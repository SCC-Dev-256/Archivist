#!/usr/bin/env python3

import os
import subprocess
import grp
import pwd

def run_command(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def main():
    # Create transcription_users group if it doesn't exist
    try:
        grp.getgrnam('transcription_users')
    except KeyError:
        run_command('groupadd transcription_users')
        print("Created transcription_users group")

    # Add schum to the group
    run_command('usermod -a -G transcription_users schum')
    print("Added schum to transcription_users group")

    # Get the GID of transcription_users
    gid = grp.getgrnam('transcription_users').gr_gid
    print(f"transcription_users GID: {gid}")

    # Update fstab entries for flex mounts
    print("\nUpdating fstab entries...")
    for i in range(1, 10):
        mount_point = f'/mnt/flex-{i}'
        if os.path.ismount(mount_point):
            print(f"\nUnmounting {mount_point}...")
            run_command(f'umount {mount_point}')

    # Create directories and set permissions
    for i in range(1, 10):
        dir_path = f'/mnt/flex-{i}/transcriptions'
        print(f"\nProcessing {dir_path}")

        # Create directory
        run_command(f'mkdir -p {dir_path}')

        # Set group ownership
        run_command(f'chown -R :transcription_users {dir_path}')

        # Set permissions
        run_command(f'chmod -R g+rwx {dir_path}')

    # Remount all flex servers
    print("\nRemounting all flex servers...")
    run_command('mount -a')

    print("\nSetup complete. Please have schum log out and log back in for group changes to take effect.")

if __name__ == "__main__":
    main() 