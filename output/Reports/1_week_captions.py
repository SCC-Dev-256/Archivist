# Description
# PURPOSE: Generate last-7-days captioning impact report from filesystem (.scc) outputs
# DEPENDENCIES: Python 3, access to /mnt/flex-*, optional: /mnt/nas/transcriptions
# MODIFICATION NOTES: v1.0 filesystem-only report; upgrade to DB/Prometheus when credentials available

# Imports
import os, re, json, time
from datetime import datetime
from typing import Dict, Any

# Constants/config
MEMBER_CITIES = {
    'flex1': {'name': 'Birchwood', 'mount_path': '/mnt/flex-1'},
    'flex2': {'name': 'Dellwood Grant Willernie', 'mount_path': '/mnt/flex-2'},
    'flex3': {'name': 'Lake Elmo', 'mount_path': '/mnt/flex-3'},
    'flex4': {'name': 'Mahtomedi', 'mount_path': '/mnt/flex-4'},
    'flex5': {'name': 'Spare Record Storage 1', 'mount_path': '/mnt/flex-5'},
    'flex6': {'name': 'Spare Record Storage 2', 'mount_path': '/mnt/flex-6'},
    'flex7': {'name': 'Oakdale', 'mount_path': '/mnt/flex-7'},
    'flex8': {'name': 'White Bear Lake', 'mount_path': '/mnt/flex-8'},
    'flex9': {'name': 'White Bear Township', 'mount_path': '/mnt/flex-9'},
}
NAS_PATH = '/mnt/nas'
OUTPUT_DIR = os.path.join(NAS_PATH, 'transcriptions')
WINDOW_DAYS = 7
TS_RE = re.compile(r'\b(\d{2}):(\d{2}):(\d{2}):(\d{2})\b')  # HH:MM:SS:FF @30fps

# Service or DB calls
def parse_scc_duration_seconds(path: str) -> float | None:
    latest = 0.0
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                for m in TS_RE.finditer(line):
                    hh, mm, ss, ff = map(int, m.groups())
                    t = hh*3600 + mm*60 + ss + ff/30.0
                    latest = max(latest, t)
    except Exception:
        return None
    return latest if latest > 0 else None

# Main logic
def generate_report() -> Dict[str, Any]:
    cutoff = time.time() - WINDOW_DAYS*24*3600
    scc_files = []

    def scan_dir(base: str, city_id: str, city_name: str, origin: str):
        if not os.path.isdir(base):
            return
        try:
            for entry in os.scandir(base):
                if entry.is_file() and entry.name.lower().endswith('.scc'):
                    st = entry.stat()
                    if st.st_mtime >= cutoff:
                        dur = parse_scc_duration_seconds(entry.path)
                        scc_files.append({
                            'city_id': city_id, 'city_name': city_name, 'origin': origin,
                            'path': entry.path, 'size_bytes': st.st_size, 'mtime': st.st_mtime,
                            'duration_seconds': dur
                        })
        except PermissionError:
            pass

    for cid, cfg in MEMBER_CITIES.items():
        mount = cfg['mount_path']
        scan_dir(mount, cid, cfg['name'], 'flex_root')
        scan_dir(os.path.join(mount, 'vod_processed'), cid, cfg['name'], 'vod_processed')

    scan_dir(OUTPUT_DIR, 'nas', 'NAS', 'nas_output')

    by_city: Dict[str, Dict[str, Any]] = {}
    by_day: Dict[str, int] = {}
    by_origin: Dict[str, int] = {}
    total_dur = 0.0
    with_dur = 0

    for it in scc_files:
        city = it['city_id']
        by_city.setdefault(city, {'city_name': it['city_name'], 'count': 0, 'duration_seconds': 0.0})
        by_city[city]['count'] += 1
        if it['duration_seconds']:
            by_city[city]['duration_seconds'] += it['duration_seconds']
            total_dur += it['duration_seconds']
            with_dur += 1
        day = datetime.fromtimestamp(it['mtime']).strftime('%Y-%m-%d')
        by_day[day] = by_day.get(day, 0) + 1
        by_origin[f"{it['city_id']}:{it['origin']}"] = by_origin.get(f"{it['city_id']}:{it['origin']}", 0) + 1

    recent = sorted(scc_files, key=lambda x: x['mtime'], reverse=True)[:25]
    return {
        'window_days': WINDOW_DAYS,
        'now': datetime.now().isoformat(),
        'total_captions': len(scc_files),
        'files_with_duration_estimate': with_dur,
        'estimated_total_hours': round(total_dur/3600.0, 2) if with_dur else None,
        'estimated_avg_minutes_per_caption': round((total_dur/60.0)/with_dur, 1) if with_dur else None,
        'by_city': by_city,
        'by_day': dict(sorted(by_day.items())),
        'by_origin': by_origin,
        'recent_items': [
            {
                'city_id': r['city_id'], 'origin': r['origin'],
                'mtime': datetime.fromtimestamp(r['mtime']).isoformat(timespec='seconds'),
                'path': r['path'], 'duration_seconds': r['duration_seconds'],
            } for r in recent
        ],
    }

# Return value
if __name__ == '__main__':
    print(json.dumps(generate_report(), indent=2))

# NEXT STEP: Wire this into a protected Flask endpoint with Redis-cached results (5–15 min TTL) and publish Prometheus counters (caption_generation_success) for Grafana.