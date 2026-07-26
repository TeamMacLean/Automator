#!/usr/bin/env bash
set -Eeuo pipefail

readonly SOURCE_DIR="/home/pi/Automator/data"
readonly MOUNT_POINT="/mnt/image-export-usb"
readonly LOCK_FILE="/run/export-images-to-usb.lock"
readonly EXPORT_SUBDIR="images"
readonly BUZZER_SCRIPT="/usr/local/sbin/automator-buzzer.sh"

log() {
    echo "export-images-to-usb[$$]: $*"
}

fail() {
    log "ERROR: $*"
    exit 1
}

DEVICE_NAME="${1:-}"

if [[ -z "$DEVICE_NAME" ]]; then
    fail "No device name supplied. Expected something like sda1."
fi

# Prevent path injection.
# Accept normal kernel block names such as sda1, sdb2, mmcblk0p1, nvme0n1p1.
if [[ ! "$DEVICE_NAME" =~ ^[A-Za-z0-9._+-]+$ ]]; then
    fail "Invalid device name: $DEVICE_NAME"
fi

readonly DEVICE="/dev/$DEVICE_NAME"

exec 9>"$LOCK_FILE"

if ! flock -n 9; then
    log "Another export is already running. Exiting."
    exit 0
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
    fail "Source directory does not exist: $SOURCE_DIR"
fi

if [[ ! -b "$DEVICE" ]]; then
    fail "Device is not a block device: $DEVICE"
fi

DEVTYPE="$(lsblk -no TYPE "$DEVICE" 2>/dev/null | head -n1 | tr -d '[:space:]' || true)"
if [[ "$DEVTYPE" != "part" ]]; then
    fail "Device is not a partition: $DEVICE type=$DEVTYPE"
fi

PKNAME="$(lsblk -no PKNAME "$DEVICE" 2>/dev/null | head -n1 | tr -d '[:space:]' || true)"
if [[ -z "$PKNAME" ]]; then
    fail "Could not determine parent block device for $DEVICE"
fi

PARENT_DEVICE="/dev/$PKNAME"

TRAN="$(lsblk -dn -o TRAN "$PARENT_DEVICE" 2>/dev/null | head -n1 | tr -d '[:space:]' || true)"

if [[ "$TRAN" != "usb" ]]; then
    fail "Parent device is not USB transport: $PARENT_DEVICE transport=$TRAN"
fi

FSTYPE="$(blkid -o value -s TYPE "$DEVICE" 2>/dev/null || true)"
LABEL="$(blkid -o value -s LABEL "$DEVICE" 2>/dev/null || true)"

if [[ -z "$FSTYPE" ]]; then
    fail "Could not detect filesystem type on $DEVICE"
fi

# Avoid accidentally exporting to boot/root partitions on bootable USB media.
case "$LABEL" in
    bootfs|rootfs)
        log "Skipping system-like USB partition: <REDACTED>
        exit 0
        ;;
esac

case "$FSTYPE" in
    vfat|exfat|ext4|ntfs)
        log "Detected supported filesystem: $FSTYPE label=${LABEL:-none}"
        ;;
    *)
        fail "Unsupported filesystem: $FSTYPE"
        ;;
esac

mkdir -p "$MOUNT_POINT"

MOUNTED_BY_SCRIPT=0
EXPORT_OK=0

write_status_file() {
    local status_file="$1"
    local status_text="$2"

    if mountpoint -q "$MOUNT_POINT"; then
        {
            echo "$status_text"
            echo "Device: $DEVICE"
            echo "Filesystem: $FSTYPE"
            echo "Label: ${LABEL:-none}"
            echo "Source: $SOURCE_DIR"
            echo "Destination: /$EXPORT_SUBDIR"
            echo "Excluded files:"
            echo "  best.onnx"
            echo "  bestnew.onnx"
            echo "  calibration.json"
            echo "  usb_camera_index.json"
            echo "Timestamp UTC: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
            echo "Hostname: $(hostname)"
        } > "$MOUNT_POINT/$status_file" || true
    fi
}

cleanup() {
    local exit_code=$?

    set +e

    if [[ "$MOUNTED_BY_SCRIPT" -eq 1 ]] && mountpoint -q "$MOUNT_POINT"; then
        if [[ "$EXPORT_OK" -eq 1 ]]; then
            write_status_file "EXPORT_DONE.txt" "Export completed successfully."
        else
            write_status_file "EXPORT_FAILED.txt" "Export failed or was interrupted."
        fi

        log "Syncing filesystem buffers..."
        sync

        log "Unmounting $MOUNT_POINT..."
        umount "$MOUNT_POINT"
        local umount_code=$?

        if [[ "$umount_code" -ne 0 ]]; then
            log "ERROR: Failed to unmount $MOUNT_POINT. Exit code: $umount_code"
            exit "$umount_code"
        fi

        log "Unmounted $MOUNT_POINT successfully."

        # Beep only after successful copy, sync, and unmount.
        # Meaning of beep:
        #   USB export complete + USB safely unmounted.
        if [[ "$EXPORT_OK" -eq 1 ]]; then
            if [[ -x "$BUZZER_SCRIPT" ]]; then
                log "USB export completed and unmounted. Beeping for 5 seconds."
                "$BUZZER_SCRIPT" 5 >/dev/null 2>&1 || true
            else
                log "Buzzer script not found or not executable: $BUZZER_SCRIPT"
            fi
        fi
    fi

    # Optional best-effort safe power-off.
    # This happens after successful sync + unmount, and after the completion beep.
    # sync + umount are the main safety steps.
    if command -v udisksctl >/dev/null 2>&1; then
        if lsblk -nr -o MOUNTPOINT "$PARENT_DEVICE" | grep -q '/'; then
            log "Not powering off $PARENT_DEVICE because one or more partitions are still mounted."
        else
            log "Attempting USB power-off with udisksctl for $PARENT_DEVICE..."
            udisksctl power-off -b "$PARENT_DEVICE" >/dev/null 2>&1 || true
        fi
    elif command -v blockdev >/dev/null 2>&1; then
        blockdev --flushbufs "$PARENT_DEVICE" >/dev/null 2>&1 || true
    fi

    exit "$exit_code"
}

trap cleanup EXIT INT TERM

# If Raspberry Pi desktop has already auto-mounted this exact partition,
# unmount it first so the export uses only the controlled mount point.
EXISTING_MOUNTS="$(findmnt -rn -S "$DEVICE" -o TARGET 2>/dev/null || true)"

if [[ -n "$EXISTING_MOUNTS" ]]; then
    while IFS= read -r existing_mount; do
        [[ -z "$existing_mount" ]] && continue
        log "Device $DEVICE is already mounted at $existing_mount. Attempting to unmount it first."
        umount "$existing_mount" || fail "Could not unmount existing mount: $existing_mount"
    done <<< "$EXISTING_MOUNTS"
fi

if mountpoint -q "$MOUNT_POINT"; then
    fail "Mount point is already in use: $MOUNT_POINT"
fi

log "Mounting $DEVICE at $MOUNT_POINT..."

case "$FSTYPE" in
    ext4)
        mount -t ext4 -o rw,noexec,nodev,nosuid "$DEVICE" "$MOUNT_POINT"
        ;;
    vfat)
        mount -t vfat -o rw,noexec,nodev,nosuid,uid=0,gid=0,umask=022,flush "$DEVICE" "$MOUNT_POINT"
        ;;
    exfat)
        mount -t exfat -o rw,noexec,nodev,nosuid,uid=0,gid=0,umask=022 "$DEVICE" "$MOUNT_POINT"
        ;;
    ntfs)
        if mount -t ntfs3 -o rw,noexec,nodev,nosuid,uid=0,gid=0,umask=022 "$DEVICE" "$MOUNT_POINT" 2>/dev/null; then
            :
        elif command -v ntfs-3g >/dev/null 2>&1; then
            ntfs-3g -o rw,noexec,nodev,nosuid,uid=0,gid=0,umask=022 "$DEVICE" "$MOUNT_POINT"
        else
            fail "NTFS filesystem detected but neither ntfs3 nor ntfs-3g is available."
        fi
        ;;
esac

MOUNTED_BY_SCRIPT=1

mkdir -p "$MOUNT_POINT/$EXPORT_SUBDIR"

log "Starting rsync export from $SOURCE_DIR/ to $MOUNT_POINT/$EXPORT_SUBDIR/"

# Do not use rsync -a here.
# FAT32, exFAT, and many NTFS mounts do not support normal Unix chown/chgrp/chmod.
#
# Export scope:
#   Source: /home/pi/Automator/data/
#   Destination on USB: /images/
#
# Excluded files:
#   best.onnx
#   bestnew.onnx
#   calibration.json
#   usb_camera_index.json
#
# The exclude patterns below match those filenames anywhere under SOURCE_DIR.
if rsync -rt \
    --ignore-existing \
    --no-owner \
    --no-group \
    --no-perms \
    --omit-dir-times \
    --exclude='best.onnx' \
    --exclude='bestnew.onnx' \
    --exclude='calibration.json' \
    --exclude='usb_camera_index.json' \
    -- "$SOURCE_DIR"/ "$MOUNT_POINT/$EXPORT_SUBDIR"/; then
    EXPORT_OK=1
    log "rsync completed successfully."
else
    EXPORT_OK=0
    log "ERROR: rsync failed."
    exit 1
fi

log "Export completed. USB will be synced and unmounted by cleanup."
exit 0
