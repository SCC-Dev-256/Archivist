#!/usr/bin/env python3
"""
Simple System Status Check
Quick overview of VOD processing system components
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


def check_flex_mounts():
    """Check flex mount status"""
    print("🔍 Checking Flex Mounts...")
    mounts = [
        "/mnt/flex-1",
        "/mnt/flex-2",
        "/mnt/flex-3",
        "/mnt/flex-4",
        "/mnt/flex-5",
        "/mnt/flex-6",
        "/mnt/flex-7",
        "/mnt/flex-8",
        "/mnt/flex-9",
    ]

    working = 0
    for mount in mounts:
        try:
            if os.path.ismount(mount):
                test_file = f"{mount}/status_test_{int(time.time())}.txt"
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                print(f"✅ {mount}: Working")
                working += 1
            else:
                print(f"❌ {mount}: Not mounted")
        except Exception as e:
            print(f"❌ {mount}: Error - {e}")

    return working, len(mounts)


def check_celery():
    """Check Celery status"""
    print("\n🔍 Checking Celery...")
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, db=0)

        # Check Redis connection
        r.ping()
        print("✅ Redis: Connected")

        # Check Celery workers
        workers = r.smembers("celery:workers")
        print(f"✅ Celery Workers: {len(workers)} active")

        # Check recent tasks
        task_keys = r.keys("celery:task-meta-*")
        print(f"✅ Recent Tasks: {len(task_keys)} found")

        return True
    except Exception as e:
        print(f"❌ Celery/Redis Error: {e}")
        return False


def check_cablecast():
    """Check Cablecast API"""
    print("\n🔍 Checking Cablecast API...")
    try:
        from core.cablecast_client import CablecastAPIClient

        client = CablecastAPIClient()

        if client.test_connection():
            print("✅ Cablecast API: Connected")
            return True
        else:
            print("❌ Cablecast API: Connection failed")
            return False
    except Exception as e:
        print(f"❌ Cablecast API Error: {e}")
        return False


def check_system_resources():
    """Check system resources"""
    print("\n🔍 Checking System Resources...")
    try:
        import psutil

        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        print(f"✅ CPU Usage: {cpu}%")
        print(
            f"✅ Memory Usage: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)"
        )
        print(
            f"✅ Disk Usage: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"
        )

        return True
    except Exception as e:
        print(f"❌ System Resources Error: {e}")
        return False


def main():
    """Run all checks"""
    print("🚀 VOD Processing System Status Check")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check flex mounts
    working_mounts, total_mounts = check_flex_mounts()

    # Check Celery
    celery_ok = check_celery()

    # Check Cablecast
    cablecast_ok = check_cablecast()

    # Check system resources
    system_ok = check_system_resources()

    # Summary
    print("\n" + "=" * 50)
    print("📊 STATUS SUMMARY")
    print("=" * 50)
    print(f"Flex Mounts: {working_mounts}/{total_mounts} working")
    print(f"Celery/Redis: {'✅ OK' if celery_ok else '❌ FAILED'}")
    print(f"Cablecast API: {'✅ OK' if cablecast_ok else '❌ FAILED'}")
    print(f"System Resources: {'✅ OK' if system_ok else '❌ FAILED'}")

    # Overall status
    if working_mounts >= 5 and celery_ok and cablecast_ok and system_ok:
        print("\n🎉 SYSTEM STATUS: OPERATIONAL")
        print("   VOD processing system is ready for production use.")
    elif working_mounts >= 3 and celery_ok:
        print("\n⚠️  SYSTEM STATUS: PARTIALLY OPERATIONAL")
        print("   System can process VODs but some components need attention.")
    else:
        print("\n❌ SYSTEM STATUS: DEGRADED")
        print("   System needs immediate attention before production use.")

    print(f"\n📊 Dashboard: http://localhost:5051")
    print(f"📋 Logs: /opt/Archivist/logs/archivist.log")


if __name__ == "__main__":
    main()
