<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Secure USB Image Export System for Raspberry Pi OS Bookworm

## Purpose

This document describes a secure USB export system for a Raspberry Pi running Raspberry Pi OS Bookworm / Debian systemd.

When a USB pen drive is plugged into the Raspberry Pi, either directly through a Raspberry Pi USB port or through a USB hub connected to the Pi, the system automatically exports data from:

```bash
/home/pi/Automator/data
```

to the USB drive under:

```bash
/images
```

After copying, the Raspberry Pi automatically:

```text
1. Writes EXPORT_DONE.txt or EXPORT_FAILED.txt to the USB.
2. Flushes pending writes with sync.
3. Unmounts the USB drive.
4. On successful export, beeps a 3–24 V active buzzer for 5 seconds.
5. Optionally attempts a best-effort USB power-off.
```

The 5-second buzzer beep happens **only after successful copy, sync, and unmount**. Therefore, the beep means:

```text
USB export complete + USB safely unmounted.
```

The system does **not** create a network share, file browser, SMB share, NFS share, web file manager, or any other way to browse the Raspberry Pi filesystem.

---

# 1. Export Scope

## Exported source directory

The only Raspberry Pi directory exported is:

```bash
/home/pi/Automator/data
```

Everything inside this directory is exported, including subfolders such as:

```bash
/home/pi/Automator/data/captures
/home/pi/Automator/data/other_subfolders
```

The USB destination is:

```bash
/images
```

So the export result on the USB will look like:

```text
USB:/images/captures/
USB:/images/other_subfolders/
USB:/images/other_data_files
```

## Excluded files

The following files are excluded from export:

```text
best.onnx
bestnew.onnx
calibration.json
usb_camera_index.json
```

These files will not be copied to the USB, even if they are present anywhere inside:

```bash
/home/pi/Automator/data
```

## Not exposed

No other Raspberry Pi folders are exported or exposed.

The system does **not** expose:

```bash
/home/pi
/home/pi/Automator
/
/etc
/var
```

or any other local folder.

---

# 2. Device Scope

The Raspberry Pi may also have other USB devices connected, including:

```text
USB mouse
USB keyboard
USB camera
MKS Robin Nano 3.1 board
Other non-storage USB devices
```

These must not trigger the export system.

The udev rule only reacts to devices matching all of the following:

```text
USB bus
block subsystem
partition device
filesystem present
```

This means it should only trigger for USB storage partitions such as:

```bash
/dev/sda1
/dev/sdb1
/dev/sdc1
```

It should not trigger for keyboards, mice, cameras, serial devices, or the MKS Robin Nano board because those are not USB block filesystem partitions.

---

# 3. Buzzer Hardware

## Buzzer used

The buzzer is a micro active buzzer with this rating:

```text
Voltage: 3 V to 24 V
Maximum current: 10 mA
```

Because the buzzer works from 3 V and the maximum current is 10 mA, it can be used directly from a Raspberry Pi GPIO output for this short completion indication.

## GPIO selected

Use:

```text
BCM GPIO13 = physical pin 33
GND        = physical pin 34, or another Raspberry Pi GND pin
```

## Wiring

```text
Buzzer +  → Raspberry Pi BCM GPIO13 / physical pin 33
Buzzer -  → Raspberry Pi GND, for example physical pin 34
```

Do **not** connect the buzzer positive side to a 5 V pin when using direct GPIO control. For this setup, the GPIO pin itself drives the buzzer.

## Shared buzzer access

The buzzer is controlled through one shared script:

```bash
/usr/local/sbin/automator-buzzer.sh
```

Other unrelated code should also call this script instead of directly controlling GPIO13. The script uses `flock`, so overlapping beep requests do not fight over the same GPIO pin.

---

# 4. Architecture

The system uses:

```text
udev event
   ↓
systemd template oneshot service
   ↓
root-owned shell script
   ↓
validate USB partition
   ↓
mount USB
   ↓
rsync /home/pi/Automator/data to USB:/images
   ↓
write status file
   ↓
sync
   ↓
unmount
   ↓
5-second buzzer beep after successful unmount
   ↓
optional power-off
```

udev is used only as a device-event trigger. The long-running copy operation is handed off to systemd.

This is important because udev should not run long copy jobs directly.

---

# 5. Files Created

This setup creates four files:

```bash
/usr/local/sbin/export-images-to-usb.sh
/usr/local/sbin/automator-buzzer.sh
/etc/systemd/system/export-images-to-usb@.service
/etc/udev/rules.d/99-export-images-usb.rules
```

---

# 6. Install Required Packages

Run:

```bash
sudo apt update
sudo apt install -y rsync exfatprogs ntfs-3g util-linux udev systemd python3-gpiozero
```

Package purpose:

| Package | Purpose |
|---|---|
| `rsync` | Copies files efficiently |
| `exfatprogs` | exFAT filesystem support |
| `ntfs-3g` | NTFS write support where needed |
| `util-linux` | Provides `mount`, `umount`, `lsblk`, `blkid`, `flock`, `blockdev` |
| `udev` | Device event handling |
| `systemd` | Runs the export service |
| `python3-gpiozero` | Controls the GPIO buzzer |

---

# 7. Create the Buzzer Script

Create:

```bash
sudo nano /usr/local/sbin/automator-buzzer.sh
```

Paste:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# Shared Automator buzzer script.
#
# GPIO mode: BCM numbering.
# BCM GPIO13 = physical pin 33.
#
# Usage:
#   /usr/local/sbin/automator-buzzer.sh 5
#
# The lock file is stored in /tmp so both callers can share it:
#   - USB export systemd service running as root
#   - maincontroller.py or other code running as the pi user
#
# /tmp is world-writable with sticky-bit permissions on normal Linux systems.
# The script also creates/repairs the lock file with mode 0666 so a lock file
# first created by root does not block later pi-user calls.

readonly BUZZER_GPIO="${BUZZER_GPIO:-13}"
readonly LOCK_FILE="/tmp/automator-buzzer.lock"
readonly DURATION="${1:-5}"

# Ensure the shared lock file exists and is writable by both root and pi.
# If root creates this file first with default permissions, pi may not be able
# to open it later. This section prevents that.
if [[ ! -e "$LOCK_FILE" ]]; then
    old_umask="$(umask)"
    umask 000
    : > "$LOCK_FILE"
    umask "$old_umask"
fi

chmod 0666 "$LOCK_FILE" 2>/dev/null || true

exec 9>"$LOCK_FILE"

if ! flock -n 9; then
    echo "automator-buzzer: buzzer already in use; skipping"
    exit 0
fi

python3 - "$BUZZER_GPIO" "$DURATION" <<'PY'
import sys
import time
from gpiozero import Buzzer

gpio = int(sys.argv[1])
duration = float(sys.argv[2])

buzzer = Buzzer(gpio)

try:
    buzzer.on()
    time.sleep(duration)
finally:
    buzzer.off()
    buzzer.close()
PY
```

Set ownership and permissions:

```bash
sudo chmod 0755 /usr/local/sbin/automator-buzzer.sh
sudo chown root:root /usr/local/sbin/automator-buzzer.sh
sudo bash -n /usr/local/sbin/automator-buzzer.sh
```

If `bash -n` gives no output, the script syntax is valid.

Confirm it uses BCM GPIO13:

```bash
grep -n "BUZZER_GPIO" /usr/local/sbin/automator-buzzer.sh
```

Expected:

```bash
readonly BUZZER_GPIO="${BUZZER_GPIO:-13}"
```

Confirm it uses the shared `/tmp` lock file:

```bash
grep LOCK_FILE /usr/local/sbin/automator-buzzer.sh
```

Expected:

```bash
readonly LOCK_FILE="/tmp/automator-buzzer.lock"
exec 9>"$LOCK_FILE"
```

Test the buzzer as root:

```bash
sudo /usr/local/sbin/automator-buzzer.sh 5
```

Then test the same buzzer script as the normal `pi` user:

```bash
/usr/local/sbin/automator-buzzer.sh 2
```

Expected result: both commands should beep without a permission error.

If a root-owned lock file already exists from an older version of the script, reset it once:

```bash
sudo rm -f /tmp/automator-buzzer.lock
sudo install -m 0666 -o root -g root /dev/null /tmp/automator-buzzer.lock
ls -l /tmp/automator-buzzer.lock
```

Expected lock-file permissions:

```text
-rw-rw-rw- 1 root root ... /tmp/automator-buzzer.lock
```


---

# 8. Create the Export Script

Create the script:

```bash
sudo rm -f /usr/local/sbin/export-images-to-usb.sh
sudo nano /usr/local/sbin/export-images-to-usb.sh
```

Paste:

```bash
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
        log "Skipping system-like USB partition: $DEVICE label=$LABEL"
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
```

Set ownership and permissions:

```bash
sudo chmod 0755 /usr/local/sbin/export-images-to-usb.sh
sudo chown root:root /usr/local/sbin/export-images-to-usb.sh
sudo bash -n /usr/local/sbin/export-images-to-usb.sh
```

If `bash -n` gives no output, the script syntax is valid.

---

# 9. Create the systemd Service

Create:

```bash
sudo nano /etc/systemd/system/export-images-to-usb@.service
```

Paste:

```ini
[Unit]
Description=Export Automator data to USB partition %I
Documentation=man:systemd.service(5)
After=systemd-udevd.service local-fs.target
Wants=systemd-udevd.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/export-images-to-usb.sh %I
TimeoutStartSec=30min

User=root
Group=root

StandardOutput=journal
StandardError=journal

# Basic hardening.
# Avoid aggressive mount namespacing here because it caused:
#   status=226/NAMESPACE
# on Raspberry Pi OS when required paths did not exist inside the service namespace.
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Reload systemd:

```bash
sudo systemctl daemon-reload
```

---

# 10. Create the udev Rule

Create:

```bash
sudo nano /etc/udev/rules.d/99-export-images-usb.rules
```

Paste:

```udev
# Secure Automator data export to USB storage.
#
# Trigger only for USB block partitions containing a filesystem.
# This avoids USB mouse, keyboard, camera, serial devices, and MKS Robin Nano.
#
# UDISKS_IGNORE prevents Raspberry Pi desktop / udisks from auto-mounting
# the USB at /media/pi/... while our systemd service handles the export.

ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_BUS}=="usb", ENV{ID_FS_USAGE}=="filesystem", ENV{UDISKS_IGNORE}="1"

# Skip obvious Raspberry Pi boot/root partitions from bootable USB media.
ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_BUS}=="usb", ENV{ID_FS_USAGE}=="filesystem", ENV{ID_FS_LABEL}=="bootfs", GOTO="export_images_usb_end"
ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_BUS}=="usb", ENV{ID_FS_USAGE}=="filesystem", ENV{ID_FS_LABEL}=="rootfs", GOTO="export_images_usb_end"

# Start the export service only for normal USB filesystem partitions.
ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", ENV{ID_BUS}=="usb", ENV{ID_FS_USAGE}=="filesystem", TAG+="systemd", ENV{SYSTEMD_WANTS}+="export-images-to-usb@%k.service"

LABEL="export_images_usb_end"
```

Reload udev:

```bash
sudo udevadm control --reload-rules
```

Do not run `udevadm trigger` while an export USB is already mounted unless you intentionally want to re-trigger existing devices.

---

# 11. Manual Test Procedure

## 11.1 Check USB device name

Plug in the USB drive and run:

```bash
lsblk -f
```

Example:

```text
sda
├─sda1  exfat  REX     6A29-408B  /media/pi/REX
└─sda2  ext4   rootfs  ...        /media/pi/rootfs
```

In this example, the export target is:

```bash
sda1
```

The `rootfs` partition is intentionally skipped.

---

## 11.2 Unmount desktop automounts if needed

If the USB is already mounted under `/media/pi/...`, unmount it before manual testing:

```bash
sudo umount /media/pi/REX 2>/dev/null || true
sudo umount /media/pi/rootfs 2>/dev/null || true
```

Replace `REX` and `rootfs` with the actual mount names shown by:

```bash
lsblk -f
```

---

## 11.3 Test buzzer directly

```bash
sudo /usr/local/sbin/automator-buzzer.sh 5
```

Expected result:

```text
The buzzer connected to BCM GPIO13 / physical pin 33 beeps for 5 seconds.
```

---

## 11.4 Manually start the service

Run:

```bash
sudo systemctl start export-images-to-usb@sda1.service
```

Replace `sda1` with the actual USB partition name.

---

## 11.5 Check logs

Run:

```bash
journalctl -u export-images-to-usb@sda1.service --no-pager -n 100
```

Expected successful logs:

```text
Detected supported filesystem: exfat label=REX
Mounting /dev/sda1 at /mnt/image-export-usb...
Starting rsync export from /home/pi/Automator/data/ to /mnt/image-export-usb/images/
rsync completed successfully.
Export completed. USB will be synced and unmounted by cleanup.
Syncing filesystem buffers...
Unmounting /mnt/image-export-usb...
Unmounted /mnt/image-export-usb successfully.
USB export completed and unmounted. Beeping for 5 seconds.
```

The beep happens after unmount. The beep means the USB is safe to remove.

---

## 11.6 Confirm USB is unmounted

Run:

```bash
findmnt /mnt/image-export-usb
findmnt /media/pi/REX
```

After successful completion, both should ideally return no output.

If `/media/pi/REX` still appears, the desktop automounter has remounted the USB. The export may still have completed, but the USB is not safe to unplug until it is unmounted.

Unmount manually if required:

```bash
sudo umount /media/pi/REX
```

---

## 11.7 Confirm exported files

Mount the USB manually for inspection:

```bash
sudo mkdir -p /mnt/check-usb
sudo mount /dev/sda1 /mnt/check-usb
ls -la /mnt/check-usb
ls -la /mnt/check-usb/images
cat /mnt/check-usb/EXPORT_DONE.txt
```

Expected:

```text
/images
EXPORT_DONE.txt
```

You should see subfolders from:

```bash
/home/pi/Automator/data
```

inside:

```bash
/mnt/check-usb/images
```

For example:

```text
/mnt/check-usb/images/captures
/mnt/check-usb/images/other_subfolders
```

The following files should not be present:

```bash
/mnt/check-usb/images/best.onnx
/mnt/check-usb/images/bestnew.onnx
/mnt/check-usb/images/calibration.json
/mnt/check-usb/images/usb_camera_index.json
```

You can check with:

```bash
find /mnt/check-usb/images \( -name 'best.onnx' -o -name 'bestnew.onnx' -o -name 'calibration.json' -o -name 'usb_camera_index.json' \)
```

This should return no output.

Then unmount:

```bash
sudo umount /mnt/check-usb
```

---

# 12. Automatic Test Procedure

After the manual test succeeds:

1. Unmount any current USB mounts:

```bash
sudo umount /media/pi/REX 2>/dev/null || true
sudo umount /media/pi/rootfs 2>/dev/null || true
sudo umount /mnt/image-export-usb 2>/dev/null || true
```

2. Physically unplug the USB drive.

3. Start live logs:

```bash
journalctl -f | grep --line-buffered export-images-to-usb
```

4. Plug the USB drive back in.

5. Wait for the export to complete.

6. Listen for the 5-second completion beep.

7. Check:

```bash
lsblk -f
findmnt /mnt/image-export-usb
```

The USB should not remain mounted at:

```bash
/mnt/image-export-usb
```

---

# 13. Using the Same Buzzer from Other Code

For other unrelated code, call the shared buzzer script:

```bash
/usr/local/sbin/automator-buzzer.sh 1
```

From Python:

```python
import subprocess

subprocess.run(["/usr/local/sbin/automator-buzzer.sh", "1"], check=False)
```

The `flock` lock prevents overlapping beeps only if all your code uses this shared script. The shared lock file is `/tmp/automator-buzzer.lock`, which allows both root-run services and `pi`-user programs to coordinate access. If another program directly opens GPIO13 and controls it separately, it can still conflict.

---

# 14. Common Issues and Fixes

## 14.1 `journalctl -u 'export-images-to-usb@*'` shows `No data available`

This is normal before any USB has triggered the service.

The service is a template:

```bash
export-images-to-usb@.service
```

A real instance only exists after something like this starts:

```bash
export-images-to-usb@sda1.service
```

Check the template with:

```bash
systemctl cat export-images-to-usb@.service
```

After a USB has triggered the service, check the specific instance:

```bash
journalctl -u export-images-to-usb@sda1.service --no-pager
```

---

## 14.2 `status=226/NAMESPACE`

Example log:

```text
Failed to set up mount namespacing
status=226/NAMESPACE
```

Cause:

Aggressive systemd sandboxing such as `ProtectSystem=strict`, `ProtectHome`, `ReadWritePaths`, or `ReadOnlyPaths` failed because required paths were unavailable inside the service namespace.

Fix:

Use the simpler service file in this document.

---

## 14.3 exFAT `chown` error from rsync

Example log:

```text
rsync: chown failed: Operation not permitted
rsync error: some files/attrs were not transferred (code 23)
```

Cause:

`rsync -a` tries to preserve Unix ownership and permissions. exFAT and FAT32 do not support normal Linux ownership metadata.

Fix:

Use:

```bash
rsync -rt --ignore-existing --no-owner --no-group --no-perms --omit-dir-times
```

Do not use:

```bash
rsync -a
```

for FAT32/exFAT/NTFS USB export.

---

## 14.4 USB appears mounted at `/media/pi/REX`

Cause:

The Raspberry Pi desktop automounter mounted the USB before or after the export script.

Fix:

The udev rule includes:

```udev
ENV{UDISKS_IGNORE}="1"
```

If it is still mounted, unmount manually:

```bash
sudo umount /media/pi/REX
```

---

## 14.5 USB has multiple partitions

Example:

```text
sda1  exfat  REX
sda2  ext4   rootfs
```

The script skips partitions labelled:

```text
bootfs
rootfs
```

This avoids accidentally exporting to Raspberry Pi boot/root partitions on bootable USB media.

---

## 14.6 No buzzer sound

Check wiring:

```text
Buzzer +  → BCM GPIO13 / physical pin 33
Buzzer -  → GND / physical pin 34 or another GND pin
```

Check the buzzer script exists and is executable:

```bash
ls -l /usr/local/sbin/automator-buzzer.sh
```

Check GPIO setting:

```bash
grep -n "BUZZER_GPIO" /usr/local/sbin/automator-buzzer.sh
```

Run direct buzzer test:

```bash
sudo /usr/local/sbin/automator-buzzer.sh 5
```

---

## 14.7 `Permission denied` on `/tmp/automator-buzzer.lock`

Example error:

```text
/usr/local/sbin/automator-buzzer.sh: line 16: /tmp/automator-buzzer.lock: Permission denied
```

Cause:

An older or manually tested version of the buzzer script may have created the lock file as root with permissions that the `pi` user cannot write to. The shared buzzer script needs the same lock file to be writable by both root-run services and normal `pi` user programs.

Fix the existing lock file once:

```bash
sudo rm -f /tmp/automator-buzzer.lock
sudo install -m 0666 -o root -g root /dev/null /tmp/automator-buzzer.lock
ls -l /tmp/automator-buzzer.lock
```

Expected:

```text
-rw-rw-rw- 1 root root ... /tmp/automator-buzzer.lock
```

Then verify both root and the `pi` user can call the buzzer script:

```bash
sudo /usr/local/sbin/automator-buzzer.sh 2
/usr/local/sbin/automator-buzzer.sh 2
```

The current version of `automator-buzzer.sh` creates or repairs the lock file with mode `0666`, so this should not recur after the updated script is installed.

---

# 15. Safe Eject Behaviour

The script performs:

```text
1. rsync copy
2. write EXPORT_DONE.txt or EXPORT_FAILED.txt
3. sync
4. umount
5. 5-second beep only if export succeeded and USB was unmounted
6. optional udisksctl power-off
```

After the Pi has successfully run:

```bash
sync
```

and:

```bash
umount
```

and the buzzer beeps, the USB drive can be unplugged safely.

Important limitation:

If the USB drive is physically unplugged while files are still being copied, the USB filesystem can still be corrupted. No script can fully prevent corruption from mid-write removal.

The system is designed to fail gracefully if the USB is removed early. It should log the error, attempt cleanup, and should not crash the Raspberry Pi.

---

# 16. Rollback / Uninstall

Remove the udev rule:

```bash
sudo rm -f /etc/udev/rules.d/99-export-images-usb.rules
```

Remove the systemd service:

```bash
sudo rm -f /etc/systemd/system/export-images-to-usb@.service
```

Remove the export script:

```bash
sudo rm -f /usr/local/sbin/export-images-to-usb.sh
```

Remove the buzzer script if it is only used for this USB export system:

```bash
sudo rm -f /usr/local/sbin/automator-buzzer.sh
```

Reload systemd and udev:

```bash
sudo systemctl daemon-reload
sudo udevadm control --reload-rules
```

Remove the mount directory if unused:

```bash
sudo rmdir /mnt/image-export-usb 2>/dev/null || true
```

Optional package removal:

```bash
sudo apt remove -y ntfs-3g exfatprogs python3-gpiozero
```

---

# 17. Final Behaviour Summary

When a suitable USB pen drive is plugged in:

```text
1. udev detects the USB filesystem partition.
2. udev asks systemd to start export-images-to-usb@sda1.service.
3. systemd runs /usr/local/sbin/export-images-to-usb.sh sda1.
4. The script validates that /dev/sda1 is a USB block partition.
5. The script skips bootfs/rootfs partitions.
6. The script mounts the USB at /mnt/image-export-usb.
7. The script creates /images on the USB.
8. The script copies /home/pi/Automator/data/ to /images/.
9. The script excludes best.onnx, bestnew.onnx, calibration.json, and usb_camera_index.json.
10. The script writes EXPORT_DONE.txt or EXPORT_FAILED.txt.
11. The script runs sync.
12. The script unmounts the USB.
13. If export succeeded and unmount succeeded, the buzzer on BCM GPIO13 / physical pin 33 beeps for 5 seconds.
14. The USB can be safely removed after the beep.
```

The Raspberry Pi filesystem is not exposed. Only `/home/pi/Automator/data` is exported, and the excluded files are not copied.
