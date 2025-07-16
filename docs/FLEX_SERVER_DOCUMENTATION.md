# Flex Server Documentation

Comprehensive documentation for the Archivist flex server infrastructure, covering content organization, storage management, and operational procedures.

## 🏗️ Flex Server Architecture

### Overview

The Archivist system utilizes a distributed storage architecture with multiple "flex servers" - network-mounted storage locations that provide scalable, organized content management. These servers are mounted at `/mnt/flex-1` through `/mnt/flex-9` and serve different purposes in the content lifecycle.

### Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLEX SERVER ECOSYSTEM                        │
├─────────────────────────────────────────────────────────────────┤
│  Network Storage Infrastructure (Proxmox Environment)           │
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │   FLEX-1    │   │   FLEX-2    │   │   FLEX-3    │          │
│  │  Birchwood  │   │  Dellwood   │   │  Lake Elmo  │          │
│  │  Storage    │   │  Grant      │   │  Storage    │          │
│  |             |   |  Willernie  |   |             |             │
│  |             |   |  Storage    |   |             |          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │

│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │   FLEX-4    │   │   FLEX-5    │   │  FLEX-6     │          │
│  │  Mahtomedi  │   │  Spare      │   │  Spare      │          │
│  │  Storage    │   │  Record     │   │  Record     │          │
│  │             │   │  Storage 1  |   │  Storage 2  │          │
│  │             │   │             │   │             │          │
│  │             │   │             │   │             │          │
│  │             │   │             │   │             │          │
│  └─────────────┘   └─────────────┘   └─────────────┘    
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │   FLEX-7    │   │   FLEX-8    │   │  FLEX-9     │          │
│  │  Oakdale    │   │  White Bear │   │  White Bear │          │
│  │  Storage    │   │  Lake       │   │  Township   │          │
│  │             │   │  Storage    |   │   Storage   │          │
│  │             │   │             │   │             │          │
│  │             │   │             │   │             │          │
│  │             │   │             │   │             │          │
│  └─────────────┘   └─────────────┘   └─────────────┘        │
│                                                                 │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           ARCHIVIST SYSTEM INTEGRATION                  │    │
│  │                                                         │    │
│  │  • Unified access via /mnt/flex-N paths                 |    │
│  │  • Automated mount point management                     │    │
│  │  • Content classification and routing                   │    │
│  │  • Storage health monitoring                            │    │
│  │  • Backup and archival policies                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Mount Point Configuration

Each flex server is mounted using NFS/CIFS protocols with specific configurations:

```bash
# /etc/fstab entries for persistent mounts
server1:/volume1/flex-1 /mnt/flex-1 nfs defaults,_netdev 0 0
server1:/volume1/flex-2 /mnt/flex-2 nfs defaults,_netdev 0 0
server2:/volume1/flex-3 /mnt/flex-3 nfs defaults,_netdev 0 0
server2:/volume1/flex-4 /mnt/flex-4 nfs defaults,_netdev 0 0
server3:/volume1/flex-5 /mnt/flex-5 nfs defaults,_netdev 0 0
```

## 📁 Flex Server Specifications

### FLEX-1: Birchwood City Council Storage

**Purpose**: Birchwood City Council and community content storage

**Capacity**: High-capacity, high-performance storage
**Performance**: Optimized for frequent read/write operations
**Backup**: Daily incremental, weekly full backups

**Content Types**:
- Current city council meeting recordings
- Active transcription projects
- Recently published VOD content
- Live streaming archives (recent 30 days)
- High-priority content requiring immediate access

**Directory Structure**:
```
/mnt/flex-1/
├── videos/
│   ├── city_council/
│   │   ├── 2024/
│   │   │   ├── 01-January/
│   │   │   ├── 02-February/
│   │   │   └── ...
│   │   └── meetings/
│   │       ├── regular/
│   │       ├── special/
│   │       └── workshops/
│   ├── live_streams/
│   │   ├── current/
│   │   ├── scheduled/
│   │   └── completed/
│   └── vod_content/
│       ├── published/
│       ├── pending/
│       └── draft/
├── transcriptions/
│   ├── scc_files/
│   │   ├── completed/
│   │   ├── processing/
│   │   └── failed/
│   ├── summaries/
│   │   ├── auto_generated/
│   │   ├── reviewed/
│   │   └── enhanced/
│   └── metadata/
│       ├── json_files/
│       ├── timestamps/
│       └── speaker_data/
├── temp/
│   ├── processing/
│   ├── uploads/
│   └── exports/
└── logs/
    ├── transcription/
    ├── vod_publishing/
    └── system/
```

**Access Patterns**:
- High-frequency access during business hours
- Transcription jobs: 24/7 access
- VOD publishing: Scheduled batch operations
- Live streaming: Real-time access

**Monitoring Metrics**:
- Storage utilization: Target < 80%
- I/O performance: < 50ms average response time
- Network throughput: > 1GB/s for large file transfers
- Availability: 99.9% uptime target

### FLEX-2: Dellwood Grant Willernie Storage

**Purpose**: Dellwood, Grant, and Willernie combined storage

**Capacity**: Medium-capacity, good performance
**Performance**: Optimized for bulk operations and backups
**Backup**: Weekly full backups, monthly archives

**Content Types**:
- Overflow from FLEX-1 when capacity reached
- Backup copies of critical content
- Historical meeting recordings (30-90 days)
- Completed transcription archives
- VOD content mirrors

**Directory Structure**:
```
/mnt/flex-2/
├── backups/
│   ├── daily/
│   │   ├── flex-1_backup/
│   │   ├── database_backup/
│   │   └── config_backup/
│   ├── weekly/
│   │   ├── full_system/
│   │   ├── transcriptions/
│   │   └── vod_content/
│   └── monthly/
│       ├── complete_archive/
│       └── compliance_records/
├── overflow/
│   ├── videos/
│   │   ├── older_meetings/
│   │   ├── large_files/
│   │   └── bulk_uploads/
│   ├── transcriptions/
│   │   ├── archived_scc/
│   │   ├── batch_processed/
│   │   └── historical/
│   └── temp_large/
│       ├── processing_queue/
│       └── batch_operations/
├── mirrors/
│   ├── vod_published/
│   ├── critical_content/
│   └── disaster_recovery/
└── staging/
    ├── content_review/
    ├── quality_control/
    └── pre_publication/
```

**Access Patterns**:
- Moderate access during backup windows
- Burst access during disaster recovery
- Scheduled maintenance operations
- Content migration activities

**Monitoring Metrics**:
- Storage utilization: Target < 70%
- Backup completion rate: 100% success
- Recovery time objective: < 2 hours
- Network efficiency: > 500MB/s for backups

### FLEX-3: Lake Elmo City Council Storage

**Purpose**: Lake Elmo City Council and community content storage

**Capacity**: Very high capacity, cost-optimized
**Performance**: Optimized for long-term storage and retrieval
**Backup**: Quarterly full backups, compliance archives

**Content Types**:
- Historical meeting recordings (>90 days)
- Compliance and legal archive content
- Completed project archives
- Long-term transcription storage
- Cold storage for infrequently accessed content

**Directory Structure**:
```
/mnt/flex-3/
├── archives/
│   ├── yearly/
│   │   ├── 2020/
│   │   ├── 2021/
│   │   ├── 2022/
│   │   └── 2023/
│   ├── by_category/
│   │   ├── city_council/
│   │   ├── public_hearings/
│   │   ├── community_events/
│   │   └── educational/
│   └── compliance/
│       ├── legal_hold/
│       ├── retention_policy/
│       └── audit_records/
├── historical/
│   ├── transcriptions/
│   │   ├── pre_2020/
│   │   ├── legacy_formats/
│   │   └── migration_completed/
│   ├── videos/
│   │   ├── digitized_tapes/
│   │   ├── legacy_recordings/
│   │   └── format_conversions/
│   └── metadata/
│       ├── catalog_records/
│       ├── index_files/
│       └── search_data/
├── cold_storage/
│   ├── infrequent_access/
│   ├── long_term_retention/
│   └── disaster_recovery/
└── migration/
    ├── format_updates/
    ├── system_upgrades/
    └── consolidation/
```

**Access Patterns**:
- Infrequent access for historical research
- Compliance audit requests
- Migration and format conversion operations
- Emergency recovery scenarios

**Monitoring Metrics**:
- Storage utilization: Target < 90%
- Access frequency: < 10 requests/month
- Retrieval time: < 30 minutes for archived content
- Data integrity: 100% checksum verification

### FLEX-4: Special Projects Storage

**Purpose**: Dedicated storage for special projects and custom content

**Capacity**: Medium capacity, high flexibility
**Performance**: Optimized for diverse workloads
**Backup**: Project-specific backup policies

**Content Types**:
- Special event recordings
- Custom transcription projects
- Experimental content formats
- Third-party integration content
- Temporary high-priority projects

**Directory Structure**:
```
/mnt/flex-4/
├── projects/
│   ├── special_events/
│   │   ├── elections/
│   │   ├── ceremonies/
│   │   ├── festivals/
│   │   └── emergencies/
│   ├── custom_work/
│   │   ├── client_projects/
│   │   ├── research_content/
│   │   └── pilot_programs/
│   └── collaborations/
│       ├── partner_content/
│       ├── shared_resources/
│       └── joint_projects/
├── experimental/
│   ├── new_formats/
│   ├── ai_testing/
│   ├── workflow_pilots/
│   └── technology_trials/
├── temporary/
│   ├── urgent_processing/
│   ├── rush_jobs/
│   └── time_sensitive/
└── custom_workflows/
    ├── specialized_transcription/
    ├── multilingual_content/
    └── accessibility_enhanced/
```

**Access Patterns**:
- Project-driven access patterns
- Burst activity during special events
- Custom workflow processing
- Collaborative access from multiple teams

**Monitoring Metrics**:
- Storage utilization: Target < 75%
- Project completion rate: Track per project
- Custom workflow performance: Variable targets
- Resource allocation: Dynamic based on projects

### FLEX-5: Development/Test Storage

**Purpose**: Development, testing, and staging environment storage

**Capacity**: Medium capacity, development-focused
**Performance**: Optimized for development workflows
**Backup**: Development backup policies (non-critical)

**Content Types**:
- Test video files for development
- Staging transcription outputs
- Development environment content
- Quality assurance test cases
- Beta feature testing content

**Directory Structure**:
```
/mnt/flex-5/
├── development/
│   ├── test_videos/
│   │   ├── sample_content/
│   │   ├── format_tests/
│   │   ├── performance_tests/
│   │   └── stress_tests/
│   ├── staging/
│   │   ├── pre_production/
│   │   ├── integration_tests/
│   │   └── user_acceptance/
│   └── debugging/
│       ├── error_reproduction/
│       ├── log_analysis/
│       └── performance_profiling/
├── testing/
│   ├── automated_tests/
│   │   ├── unit_test_data/
│   │   ├── integration_data/
│   │   └── e2e_test_data/
│   ├── manual_tests/
│   │   ├── qa_scenarios/
│   │   ├── user_stories/
│   │   └── edge_cases/
│   └── performance/
│       ├── load_testing/
│       ├── stress_testing/
│       └── benchmark_data/
├── sandbox/
│   ├── developer_workspaces/
│   ├── experimental_features/
│   └── proof_of_concepts/
└── training/
    ├── demo_content/
    ├── tutorial_materials/
    └── documentation_examples/
```

**Access Patterns**:
- Development team access during work hours
- Automated testing system access
- Staging environment deployments
- Quality assurance testing cycles

**Monitoring Metrics**:
- Storage utilization: Target < 60%
- Test execution time: < 30 minutes average
- Development workflow efficiency: Track per team
- Staging environment uptime: 95% during work hours

### FLEX-6 through FLEX-9: Reserved/Expansion Storage

**Purpose**: Reserved for future expansion and specialized use cases

**Current Status**: Configured but not actively used
**Expansion Plans**: Ready for specific use cases as they arise

**Potential Use Cases**:
- **FLEX-6**: Disaster recovery and geographic replication
- **FLEX-7**: Machine learning model storage and training data
- **FLEX-8**: Real-time streaming buffer and cache
- **FLEX-9**: External partner integration and data exchange

## 🔧 Storage Management Operations

### Mount Point Management

#### Mounting Flex Servers

```bash
# Manual mount all flex servers
sudo mount -a

# Mount specific flex server
sudo mount /mnt/flex-1

# Check mount status
mount | grep flex
df -h | grep flex
```

#### Mount Health Monitoring

```bash
# Check mount accessibility
for i in {1..9}; do
    if mountpoint -q /mnt/flex-$i; then
        echo "FLEX-$i: Mounted"
        ls -la /mnt/flex-$i/ > /dev/null 2>&1 && echo "  Access: OK" || echo "  Access: FAILED"
    else
        echo "FLEX-$i: Not mounted"
    fi
done
```

#### Automated Mount Verification

```bash
#!/bin/bash
# mount_health_check.sh

LOG_FILE="/var/log/flex_mount_health.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

check_mount() {
    local mount_point=$1
    local flex_number=$2
    
    if mountpoint -q "$mount_point"; then
        if timeout 10 ls "$mount_point" > /dev/null 2>&1; then
            echo "[$DATE] FLEX-$flex_number: OK" >> "$LOG_FILE"
            return 0
        else
            echo "[$DATE] FLEX-$flex_number: MOUNT ACCESSIBLE BUT UNRESPONSIVE" >> "$LOG_FILE"
            return 1
        fi
    else
        echo "[$DATE] FLEX-$flex_number: NOT MOUNTED" >> "$LOG_FILE"
        return 1
    fi
}

# Check all flex servers
for i in {1..9}; do
    check_mount "/mnt/flex-$i" "$i"
done
```

### Permission Management

#### Setting Up Permissions

```bash
# Create transcription users group
sudo groupadd transcription_users

# Add users to group
sudo usermod -a -G transcription_users archivist
sudo usermod -a -G transcription_users www-data

# Set directory permissions
for i in {1..9}; do
    sudo mkdir -p /mnt/flex-$i/transcriptions
    sudo chown -R :transcription_users /mnt/flex-$i/transcriptions
    sudo chmod -R g+rwx /mnt/flex-$i/transcriptions
    sudo chmod g+s /mnt/flex-$i/transcriptions  # Set group sticky bit
done
```

#### Permission Verification

```bash
# Check permissions
ls -la /mnt/flex-*/transcriptions/

# Verify group access
sudo -u www-data touch /mnt/flex-1/transcriptions/test_file
sudo -u www-data ls -la /mnt/flex-1/transcriptions/test_file
sudo -u www-data rm /mnt/flex-1/transcriptions/test_file
```

### Storage Monitoring

#### Disk Usage Monitoring

```bash
# Check disk usage for all flex servers
df -h /mnt/flex-*

# Detailed usage by directory
du -sh /mnt/flex-*/*

# Find largest files
find /mnt/flex-* -type f -size +1G -exec ls -lh {} \; | sort -k5 -hr
```

#### Performance Monitoring

```bash
# I/O statistics
iostat -x 1 5

# Network I/O for NFS mounts
nfsstat -c
nfsstat -s

# Monitor specific mount point performance
iotop -p $(pgrep -f "nfs")
```

#### Automated Monitoring Script

```bash
#!/bin/bash
# flex_storage_monitor.sh

THRESHOLD_WARNING=80
THRESHOLD_CRITICAL=90
LOG_FILE="/var/log/flex_storage_monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

check_storage() {
    local mount_point=$1
    local flex_name=$2
    
    if mountpoint -q "$mount_point"; then
        local usage=$(df "$mount_point" | tail -1 | awk '{print $5}' | sed 's/%//')
        
        if [ "$usage" -gt "$THRESHOLD_CRITICAL" ]; then
            echo "[$DATE] CRITICAL: $flex_name usage at $usage%" >> "$LOG_FILE"
            # Send alert (implement your alerting mechanism)
            return 2
        elif [ "$usage" -gt "$THRESHOLD_WARNING" ]; then
            echo "[$DATE] WARNING: $flex_name usage at $usage%" >> "$LOG_FILE"
            return 1
        else
            echo "[$DATE] OK: $flex_name usage at $usage%" >> "$LOG_FILE"
            return 0
        fi
    else
        echo "[$DATE] ERROR: $flex_name not mounted" >> "$LOG_FILE"
        return 3
    fi
}

# Monitor all flex servers
for i in {1..5}; do
    check_storage "/mnt/flex-$i" "FLEX-$i"
done
```

## 🗂️ Content Organization Strategies

### File Naming Conventions

#### Video Files

```
Format: YYYY-MM-DD_EventType_Location_Additional.extension

Examples:
- 2024-01-15_CityCouncil_Regular_Meeting.mp4
- 2024-01-15_PublicHearing_Planning_Commission.mp4
- 2024-01-15_SpecialEvent_Community_Festival.mp4
```

#### Transcription Files

```
Format: YYYY-MM-DD_EventType_Location_Additional.scc

Examples:
- 2024-01-15_CityCouncil_Regular_Meeting.scc
- 2024-01-15_PublicHearing_Planning_Commission.scc
- 2024-01-15_SpecialEvent_Community_Festival.scc
```

#### Directory Structure Standards

```
/mnt/flex-N/
├── videos/
│   ├── YYYY/
│   │   ├── MM-Month/
│   │   │   ├── DD-Day/
│   │   │   └── event_type/
│   │   └── special_events/
│   └── bulk_import/
│       ├── pending/
│       ├── processing/
│       └── completed/
├── transcriptions/
│   ├── YYYY/
│   │   ├── MM-Month/
│   │   │   ├── scc_files/
│   │   │   ├── summaries/
│   │   │   └── metadata/
│   │   └── batch_processing/
│   └── failed/
│       ├── retry/
│       └── investigation/
└── metadata/
    ├── catalogs/
    ├── indexes/
    └── search_data/
```

### Content Lifecycle Management

#### Lifecycle Stages

1. **Ingestion** (FLEX-1)
   - New content uploaded
   - Initial quality checks
   - Metadata extraction

2. **Processing** (FLEX-1)
   - Transcription processing
   - Quality assurance
   - VOD preparation

3. **Active** (FLEX-1)
   - Content in active use
   - Frequent access
   - VOD publishing

4. **Aging** (FLEX-2)
   - Older content (30-90 days)
   - Reduced access frequency
   - Backup and archive preparation

5. **Archival** (FLEX-3)
   - Long-term storage
   - Compliance requirements
   - Infrequent access

6. **Cold Storage** (FLEX-3)
   - Very old content
   - Compliance-only access
   - Potential deletion candidates

#### Automated Lifecycle Management

```bash
#!/bin/bash
# content_lifecycle_manager.sh

LOG_FILE="/var/log/content_lifecycle.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Move content from FLEX-1 to FLEX-2 (30 days old)
move_to_secondary() {
    find /mnt/flex-1/videos -type f -mtime +30 -name "*.mp4" -print0 | \
    while IFS= read -r -d '' file; do
        relative_path=${file#/mnt/flex-1/}
        target_dir="/mnt/flex-2/$(dirname "$relative_path")"
        
        mkdir -p "$target_dir"
        if mv "$file" "$target_dir/"; then
            echo "[$DATE] Moved to secondary: $file" >> "$LOG_FILE"
        else
            echo "[$DATE] Failed to move: $file" >> "$LOG_FILE"
        fi
    done
}

# Move content from FLEX-2 to FLEX-3 (90 days old)
move_to_archive() {
    find /mnt/flex-2/videos -type f -mtime +90 -name "*.mp4" -print0 | \
    while IFS= read -r -d '' file; do
        relative_path=${file#/mnt/flex-2/}
        target_dir="/mnt/flex-3/$(dirname "$relative_path")"
        
        mkdir -p "$target_dir"
        if mv "$file" "$target_dir/"; then
            echo "[$DATE] Moved to archive: $file" >> "$LOG_FILE"
        else
            echo "[$DATE] Failed to archive: $file" >> "$LOG_FILE"
        fi
    done
}

# Execute lifecycle management
move_to_secondary
move_to_archive
```

## 🔄 Backup and Recovery Procedures

### Backup Strategies

#### Daily Backup (FLEX-1 → FLEX-2)

```bash
#!/bin/bash
# daily_backup.sh

SOURCE_DIR="/mnt/flex-1"
BACKUP_DIR="/mnt/flex-2/backups/daily"
DATE=$(date '+%Y-%m-%d')
LOG_FILE="/var/log/daily_backup.log"

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup critical content
rsync -av --progress \
    --exclude='temp/' \
    --exclude='*.tmp' \
    --exclude='processing/' \
    "$SOURCE_DIR/" "$BACKUP_DIR/$DATE/" \
    >> "$LOG_FILE" 2>&1

# Verify backup integrity
cd "$BACKUP_DIR/$DATE"
find . -type f -name "*.mp4" -o -name "*.scc" | \
while read file; do
    if [ -f "$SOURCE_DIR/$file" ]; then
        if ! cmp -s "$file" "$SOURCE_DIR/$file"; then
            echo "[$DATE] Backup verification failed: $file" >> "$LOG_FILE"
        fi
    fi
done
```

#### Weekly Full Backup (FLEX-1 → FLEX-2)

```bash
#!/bin/bash
# weekly_backup.sh

SOURCE_DIR="/mnt/flex-1"
BACKUP_DIR="/mnt/flex-2/backups/weekly"
DATE=$(date '+%Y-W%U')
LOG_FILE="/var/log/weekly_backup.log"

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Full system backup
rsync -av --progress \
    --delete \
    --exclude='temp/' \
    --exclude='*.tmp' \
    "$SOURCE_DIR/" "$BACKUP_DIR/$DATE/" \
    >> "$LOG_FILE" 2>&1

# Create backup manifest
find "$BACKUP_DIR/$DATE" -type f -exec md5sum {} \; > "$BACKUP_DIR/$DATE/backup_manifest.md5"

# Compress old backups
find "$BACKUP_DIR" -type d -name "20*" -mtime +7 -exec tar -czf {}.tar.gz {} \; -exec rm -rf {} \;
```

#### Monthly Archive Backup (FLEX-2 → FLEX-3)

```bash
#!/bin/bash
# monthly_archive.sh

SOURCE_DIR="/mnt/flex-2"
ARCHIVE_DIR="/mnt/flex-3/archives/monthly"
DATE=$(date '+%Y-%m')
LOG_FILE="/var/log/monthly_archive.log"

# Create archive directory
mkdir -p "$ARCHIVE_DIR/$DATE"

# Archive monthly backup
tar -czf "$ARCHIVE_DIR/$DATE/flex-2-backup-$DATE.tar.gz" \
    -C "$SOURCE_DIR" \
    --exclude='temp/' \
    --exclude='*.tmp' \
    . >> "$LOG_FILE" 2>&1

# Create archive index
tar -tzf "$ARCHIVE_DIR/$DATE/flex-2-backup-$DATE.tar.gz" > "$ARCHIVE_DIR/$DATE/archive_index.txt"

# Verify archive integrity
if tar -tzf "$ARCHIVE_DIR/$DATE/flex-2-backup-$DATE.tar.gz" > /dev/null 2>&1; then
    echo "[$DATE] Archive created successfully" >> "$LOG_FILE"
else
    echo "[$DATE] Archive creation failed" >> "$LOG_FILE"
fi
```

### Recovery Procedures

#### Emergency Recovery

```bash
#!/bin/bash
# emergency_recovery.sh

BACKUP_DATE=$1
RECOVERY_TARGET=$2
LOG_FILE="/var/log/emergency_recovery.log"

if [ -z "$BACKUP_DATE" ] || [ -z "$RECOVERY_TARGET" ]; then
    echo "Usage: $0 <backup_date> <recovery_target>"
    exit 1
fi

# Locate backup
BACKUP_DIR="/mnt/flex-2/backups/daily/$BACKUP_DATE"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Perform recovery
rsync -av --progress \
    "$BACKUP_DIR/" "$RECOVERY_TARGET/" \
    >> "$LOG_FILE" 2>&1

# Verify recovery
if [ $? -eq 0 ]; then
    echo "[$BACKUP_DATE] Recovery completed successfully to $RECOVERY_TARGET" >> "$LOG_FILE"
else
    echo "[$BACKUP_DATE] Recovery failed" >> "$LOG_FILE"
fi
```

#### Selective File Recovery

```bash
#!/bin/bash
# selective_recovery.sh

FILE_PATH=$1
BACKUP_DATE=$2
LOG_FILE="/var/log/selective_recovery.log"

if [ -z "$FILE_PATH" ] || [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 <file_path> <backup_date>"
    exit 1
fi

# Locate backup file
BACKUP_FILE="/mnt/flex-2/backups/daily/$BACKUP_DATE/$FILE_PATH"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Recover specific file
cp "$BACKUP_FILE" "/mnt/flex-1/$FILE_PATH"

if [ $? -eq 0 ]; then
    echo "[$BACKUP_DATE] File recovery completed: $FILE_PATH" >> "$LOG_FILE"
else
    echo "[$BACKUP_DATE] File recovery failed: $FILE_PATH" >> "$LOG_FILE"
fi
```

## 🔍 Monitoring and Alerting

### Storage Health Monitoring

#### Real-time Monitoring Dashboard

```bash
#!/bin/bash
# storage_dashboard.sh

watch -n 30 '
echo "=== FLEX SERVER DASHBOARD ==="
echo "$(date)"
echo ""

for i in {1..5}; do
    echo "FLEX-$i Status:"
    if mountpoint -q "/mnt/flex-$i"; then
        df -h "/mnt/flex-$i" | tail -1
        echo "  Files: $(find /mnt/flex-$i -type f | wc -l)"
        echo "  Dirs:  $(find /mnt/flex-$i -type d | wc -l)"
        echo "  Last Activity: $(stat -c %y /mnt/flex-$i 2>/dev/null || echo "N/A")"
    else
        echo "  STATUS: NOT MOUNTED"
    fi
    echo ""
done
'
```

#### Alert System

```bash
#!/bin/bash
# flex_alert_system.sh

ALERT_EMAIL="admin@example.com"
ALERT_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
LOG_FILE="/var/log/flex_alerts.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

send_alert() {
    local level=$1
    local message=$2
    
    echo "[$DATE] $level: $message" >> "$LOG_FILE"
    
    # Email alert
    echo "$message" | mail -s "FLEX Server Alert: $level" "$ALERT_EMAIL"
    
    # Webhook alert (Slack example)
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"FLEX Server Alert: $level\\n$message\"}" \
        "$ALERT_WEBHOOK"
}

# Check disk usage
for i in {1..5}; do
    if mountpoint -q "/mnt/flex-$i"; then
        usage=$(df "/mnt/flex-$i" | tail -1 | awk '{print $5}' | sed 's/%//')
        
        if [ "$usage" -gt 90 ]; then
            send_alert "CRITICAL" "FLEX-$i disk usage at $usage%"
        elif [ "$usage" -gt 80 ]; then
            send_alert "WARNING" "FLEX-$i disk usage at $usage%"
        fi
    else
        send_alert "ERROR" "FLEX-$i is not mounted"
    fi
done

# Check mount accessibility
for i in {1..5}; do
    if mountpoint -q "/mnt/flex-$i"; then
        if ! timeout 10 ls "/mnt/flex-$i" > /dev/null 2>&1; then
            send_alert "ERROR" "FLEX-$i mounted but not accessible"
        fi
    fi
done
```

### Performance Monitoring

#### I/O Performance Monitoring

```bash
#!/bin/bash
# io_performance_monitor.sh

LOG_FILE="/var/log/flex_io_performance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Monitor I/O statistics
iostat -x 1 1 | grep -E "(flex|Device)" | while read line; do
    if [[ $line == *"flex"* ]]; then
        echo "[$DATE] $line" >> "$LOG_FILE"
    fi
done

# Monitor network I/O for NFS
nfsstat -c | grep -E "(read|write)" >> "$LOG_FILE"
```

#### Access Pattern Analysis

```bash
#!/bin/bash
# access_pattern_analysis.sh

LOG_FILE="/var/log/flex_access_patterns.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Analyze file access patterns
for i in {1..5}; do
    if mountpoint -q "/mnt/flex-$i"; then
        echo "[$DATE] FLEX-$i Access Analysis:" >> "$LOG_FILE"
        
        # Most accessed files (by modification time)
        find "/mnt/flex-$i" -type f -mtime -1 -exec ls -la {} \; | \
        sort -k6,7 | tail -10 >> "$LOG_FILE"
        
        # Directory access statistics
        find "/mnt/flex-$i" -type d -mtime -1 | wc -l >> "$LOG_FILE"
        
        echo "---" >> "$LOG_FILE"
    fi
done
```

## 🛠️ Maintenance Procedures

### Routine Maintenance

#### Daily Maintenance Tasks

```bash
#!/bin/bash
# daily_maintenance.sh

LOG_FILE="/var/log/flex_daily_maintenance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting daily maintenance" >> "$LOG_FILE"

# Clean temporary files
for i in {1..5}; do
    if mountpoint -q "/mnt/flex-$i"; then
        find "/mnt/flex-$i/temp" -type f -mtime +1 -delete 2>/dev/null
        find "/mnt/flex-$i/temp" -type d -empty -delete 2>/dev/null
    fi
done

# Update access time for frequently used directories
for i in {1..5}; do
    if mountpoint -q "/mnt/flex-$i"; then
        touch "/mnt/flex-$i/.health_check"
    fi
done

# Verify mount points
for i in {1..5}; do
    if ! mountpoint -q "/mnt/flex-$i"; then
        echo "[$DATE] WARNING: FLEX-$i not mounted, attempting remount" >> "$LOG_FILE"
        mount "/mnt/flex-$i" >> "$LOG_FILE" 2>&1
    fi
done

echo "[$DATE] Daily maintenance completed" >> "$LOG_FILE"
```

#### Weekly Maintenance Tasks

```bash
#!/bin/bash
# weekly_maintenance.sh

LOG_FILE="/var/log/flex_weekly_maintenance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting weekly maintenance" >> "$LOG_FILE"

# Deep clean temporary files
for i in {1..5}; do
    if mountpoint -q "/mnt/flex-$i"; then
        # Remove old log files
        find "/mnt/flex-$i/logs" -type f -mtime +7 -delete 2>/dev/null
        
        # Remove failed transcription attempts
        find "/mnt/flex-$i/transcriptions/failed" -type f -mtime +7 -delete 2>/dev/null
        
        # Compress old completed transcriptions
        find "/mnt/flex-$i/transcriptions/completed" -type f -mtime +30 -name "*.scc" \
            -exec gzip {} \; 2>/dev/null
    fi
done

# Verify backup integrity
for i in {1..5}; do
    if [ -d "/mnt/flex-2/backups/daily" ]; then
        find "/mnt/flex-2/backups/daily" -type f -name "backup_manifest.md5" -mtime -7 \
            -exec md5sum -c {} \; >> "$LOG_FILE" 2>&1
    fi
done

# Update storage statistics
for i in {1..5}; do
    if mountpoint -q "/mnt/flex-$i"; then
        echo "[$DATE] FLEX-$i Statistics:" >> "$LOG_FILE"
        df -h "/mnt/flex-$i" >> "$LOG_FILE"
        du -sh "/mnt/flex-$i"/* >> "$LOG_FILE"
    fi
done

echo "[$DATE] Weekly maintenance completed" >> "$LOG_FILE"
```

### Troubleshooting Procedures

#### Mount Point Issues

```bash
#!/bin/bash
# mount_troubleshooting.sh

troubleshoot_mount() {
    local mount_point=$1
    local flex_num=$2
    
    echo "Troubleshooting FLEX-$flex_num ($mount_point)"
    
    # Check if mount point exists
    if [ ! -d "$mount_point" ]; then
        echo "Creating mount point: $mount_point"
        sudo mkdir -p "$mount_point"
    fi
    
    # Check if mounted
    if mountpoint -q "$mount_point"; then
        echo "Mount point is mounted"
        
        # Check accessibility
        if timeout 10 ls "$mount_point" > /dev/null 2>&1; then
            echo "Mount point is accessible"
        else
            echo "Mount point is not accessible, attempting remount"
            sudo umount "$mount_point" 2>/dev/null
            sudo mount "$mount_point"
        fi
    else
        echo "Mount point is not mounted, attempting mount"
        sudo mount "$mount_point"
    fi
    
    # Verify final status
    if mountpoint -q "$mount_point" && timeout 10 ls "$mount_point" > /dev/null 2>&1; then
        echo "FLEX-$flex_num is now operational"
    else
        echo "FLEX-$flex_num troubleshooting failed"
    fi
}

# Troubleshoot all flex servers
for i in {1..5}; do
    troubleshoot_mount "/mnt/flex-$i" "$i"
    echo ""
done
```

#### Performance Issues

```bash
#!/bin/bash
# performance_troubleshooting.sh

LOG_FILE="/var/log/flex_performance_troubleshooting.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting performance troubleshooting" >> "$LOG_FILE"

# Check network connectivity
for i in {1..5}; do
    if mountpoint -q "/mnt/flex-$i"; then
        echo "[$DATE] Testing FLEX-$i network performance" >> "$LOG_FILE"
        
        # Test write performance
        dd if=/dev/zero of="/mnt/flex-$i/performance_test" bs=1M count=100 2>> "$LOG_FILE"
        
        # Test read performance
        dd if="/mnt/flex-$i/performance_test" of=/dev/null bs=1M 2>> "$LOG_FILE"
        
        # Clean up test file
        rm -f "/mnt/flex-$i/performance_test"
    fi
done

# Check system resources
echo "[$DATE] System resource usage:" >> "$LOG_FILE"
free -h >> "$LOG_FILE"
iostat -x 1 1 >> "$LOG_FILE"
```

## 📊 Usage Analytics and Reporting

### Storage Usage Reports

```bash
#!/bin/bash
# storage_usage_report.sh

REPORT_FILE="/var/log/flex_storage_report_$(date +%Y%m%d).txt"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

generate_report() {
    echo "=== FLEX SERVER STORAGE REPORT ===" > "$REPORT_FILE"
    echo "Generated: $DATE" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    for i in {1..5}; do
        if mountpoint -q "/mnt/flex-$i"; then
            echo "FLEX-$i Storage Analysis:" >> "$REPORT_FILE"
            echo "------------------------" >> "$REPORT_FILE"
            
            # Disk usage summary
            df -h "/mnt/flex-$i" >> "$REPORT_FILE"
            
            # Directory sizes
            du -sh "/mnt/flex-$i"/* 2>/dev/null | sort -hr >> "$REPORT_FILE"
            
            # File counts by type
            echo "File counts:" >> "$REPORT_FILE"
            echo "  Videos: $(find /mnt/flex-$i -name "*.mp4" | wc -l)" >> "$REPORT_FILE"
            echo "  SCC files: $(find /mnt/flex-$i -name "*.scc" | wc -l)" >> "$REPORT_FILE"
            echo "  Summaries: $(find /mnt/flex-$i -name "*.txt" | wc -l)" >> "$REPORT_FILE"
            
            echo "" >> "$REPORT_FILE"
        fi
    done
}

generate_report
echo "Report generated: $REPORT_FILE"
```

### Access Pattern Reports

```bash
#!/bin/bash
# access_pattern_report.sh

REPORT_FILE="/var/log/flex_access_report_$(date +%Y%m%d).txt"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

generate_access_report() {
    echo "=== FLEX SERVER ACCESS PATTERN REPORT ===" > "$REPORT_FILE"
    echo "Generated: $DATE" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    for i in {1..5}; do
        if mountpoint -q "/mnt/flex-$i"; then
            echo "FLEX-$i Access Patterns:" >> "$REPORT_FILE"
            echo "------------------------" >> "$REPORT_FILE"
            
            # Most recently accessed files
            echo "Recently accessed files (last 24 hours):" >> "$REPORT_FILE"
            find "/mnt/flex-$i" -type f -atime -1 -exec ls -ltu {} \; | \
            head -10 >> "$REPORT_FILE"
            
            # Most recently modified files
            echo "Recently modified files (last 24 hours):" >> "$REPORT_FILE"
            find "/mnt/flex-$i" -type f -mtime -1 -exec ls -lt {} \; | \
            head -10 >> "$REPORT_FILE"
            
            echo "" >> "$REPORT_FILE"
        fi
    done
}

generate_access_report
echo "Access report generated: $REPORT_FILE"
```

## 🔧 Configuration Management

### Flex Server Configuration File

```bash
# /etc/archivist/flex_config.conf

# Flex Server Configuration
FLEX_SERVERS=(
    "flex-1:/mnt/flex-1:primary:active"
    "flex-2:/mnt/flex-2:secondary:active"
    "flex-3:/mnt/flex-3:archive:active"
    "flex-4:/mnt/flex-4:projects:active"
    "flex-5:/mnt/flex-5:development:active"
    "flex-6:/mnt/flex-6:reserved:inactive"
    "flex-7:/mnt/flex-7:reserved:inactive"
    "flex-8:/mnt/flex-8:reserved:inactive"
    "flex-9:/mnt/flex-9:reserved:inactive"
)

# Storage thresholds
DISK_WARNING_THRESHOLD=80
DISK_CRITICAL_THRESHOLD=90

# Backup settings
BACKUP_RETENTION_DAYS=30
ARCHIVE_RETENTION_MONTHS=12

# Monitoring settings
MONITOR_INTERVAL=300
ALERT_EMAIL="admin@example.com"
ALERT_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Environment-Specific Configuration

```bash
# /etc/archivist/flex_env.conf

# Environment: Production
ENVIRONMENT="production"

# Performance settings
NFS_MOUNT_OPTIONS="defaults,_netdev,rsize=32768,wsize=32768"
BACKUP_COMPRESSION="gzip"
MAINTENANCE_WINDOW="02:00-04:00"

# Security settings
TRANSCRIPTION_USER_GROUP="transcription_users"
DEFAULT_PERMISSIONS="755"
SECURE_PERMISSIONS="750"

# Logging settings
LOG_LEVEL="INFO"
LOG_RETENTION_DAYS=30
AUDIT_LOG_ENABLED=true
```

---

**This documentation provides comprehensive guidance for managing the Archivist flex server infrastructure. For technical support, consult your system administrator or refer to the main system documentation.** 