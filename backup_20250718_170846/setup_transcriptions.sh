#!/bin/bash

# Create transcription_users group if it doesn't exist
groupadd transcription_users

# Add schum to the group
usermod -a -G transcription_users schum

# Create directories and set permissions
for i in {1..9}; do
    mkdir -p /mnt/flex-$i/transcriptions
    chown -R :transcription_users /mnt/flex-$i/transcriptions
    chmod -R g+rwx /mnt/flex-$i/transcriptions
done

# Update fstab entries for flex mounts
sed -i 's/uid=0,gid=0,file_mode=0644,dir_mode=0755/gid=$(getent group transcription_users | cut -d: -f3),file_mode=0664,dir_mode=0775/g' /etc/fstab

# Remount all flex servers
mount -a

echo "Setup complete. Please have schum log out and log back in for group changes to take effect."
