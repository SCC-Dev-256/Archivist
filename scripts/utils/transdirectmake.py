#!/usr/bin/env python3
"""Setup script for transcription directory permissions and group management."""

import grp
import os
import pwd
import subprocess

from loguru import logger


def run_command(cmd):
    """Run a shell command and log the execution."""
    logger.info(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def main():
    """Main setup function for transcription directories."""
    # Create transcription_users group if it doesn't exist
    try:
        grp.getgrnam('transcription_users')
    except KeyError:
        run_command('groupadd transcription_users')
        logger.success("Created transcription_users group")

    # Add schum to the group
    run_command('usermod -a -G transcription_users schum')
    logger.success("Added schum to transcription_users group")

    # Get the GID of transcription_users
    gid = grp.getgrnam('transcription_users').gr_gid
    logger.info(f"transcription_users GID: {gid}")

    # Update fstab entries for flex mounts
    logger.info("Updating fstab entries...")
    for i in range(1, 10):
        mount_point = f'/mnt/flex-{i}'
        if os.path.ismount(mount_point):
            logger.info(f"Unmounting {mount_point}...")
            run_command(f'umount {mount_point}')

    # Create directories and set permissions
    for i in range(1, 10):
        dir_path = f'/mnt/flex-{i}/transcriptions'
        logger.info(f"Processing {dir_path}")

        # Create directory
        run_command(f'mkdir -p {dir_path}')

        # Set group ownership
        run_command(f'chown -R :transcription_users {dir_path}')

        # Set permissions
        run_command(f'chmod -R g+rwx {dir_path}')

    # Remount all flex servers
    logger.info("Remounting all flex servers...")
    run_command('mount -a')

    logger.success("Setup complete. Please have schum log out and log back in for group changes to take effect.")


if __name__ == "__main__":
    main() 