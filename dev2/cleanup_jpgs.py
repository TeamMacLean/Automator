#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

from pathlib import Path
import argparse
import time
import shutil
from datetime import datetime

DATA_DIR = Path("/home/pi/Automator/data")
CAPTURES_DIR = DATA_DIR / "captures"

PROTECTED_FILENAMES = {
    "bestnew.onnx",
    "calibration.json",
    "usb_camera_index.json",
}

SIZE_LIMIT_BYTES = 5 * 1024 * 1024 * 1024  # 5 GiB

FOURTEEN_DAYS_SECONDS = 14 * 24 * 60 * 60
TWENTY_ONE_DAYS_SECONDS = 21 * 24 * 60 * 60


def format_bytes(num_bytes: int) -> str:
    mib = num_bytes / (1024 ** 2)
    gib = num_bytes / (1024 ** 3)
    return f"{gib:.2f} GiB / {mib:.0f} MiB"


def format_time(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0
    except PermissionError:
        return 0


def get_path_size(path: Path) -> int:
    """
    Return size of a file or folder.
    """
    total = 0

    if not path.exists():
        return 0

    try:
        if path.is_file():
            return path.stat().st_size
    except FileNotFoundError:
        return 0
    except PermissionError:
        print(f"WARNING: Permission denied while checking size: {path}")
        return 0

    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except FileNotFoundError:
            continue
        except PermissionError:
            print(f"WARNING: Permission denied while checking size: {item}")

    return total


def get_total_size(path: Path) -> int:
    return get_path_size(path)


def is_jpg(path: Path) -> bool:
    """
    Match JPG format only.
    Matches .jpg and .JPG.
    Does not match .jpeg.
    """
    return path.is_file() and path.suffix.lower() == ".jpg"


def is_protected(path: Path) -> bool:
    return path.name in PROTECTED_FILENAMES


def get_dynamic_folders():
    """
    Dynamic folders are immediate folders inside DATA_DIR,
    except the special captures folder.

    These folders may be deleted recursively if they qualify.
    """
    folders = []

    if not DATA_DIR.exists():
        return folders

    for item in DATA_DIR.iterdir():
        try:
            if not item.is_dir():
                continue

            if item == CAPTURES_DIR:
                continue

            folders.append(item)

        except PermissionError:
            print(f"WARNING: Permission denied while checking folder: {item}")

    folders.sort(key=lambda p: (safe_mtime(p), str(p)))
    return folders


def collect_candidates(max_age_seconds: int):
    """
    Collect deletion candidates.

    captures:
      - Only JPG files are candidates.
      - captures itself is never deleted.
      - File age is based on each JPG file modified time.

    dynamic folders:
      - Each immediate dynamic folder is one candidate.
      - Folder age is based on the folder modified time.
      - If selected, the whole folder is deleted recursively.
    """
    now = time.time()
    cutoff_timestamp = now - max_age_seconds

    candidates = []

    # 1. JPG files inside captures.
    if CAPTURES_DIR.exists():
        captures_mtime = safe_mtime(CAPTURES_DIR)

        for file_path in CAPTURES_DIR.rglob("*"):
            try:
                if not is_jpg(file_path):
                    continue

                if is_protected(file_path):
                    continue

                file_stat = file_path.stat()
                file_mtime = file_stat.st_mtime

                if file_mtime >= cutoff_timestamp:
                    continue

                candidates.append(
                    {
                        "kind": "jpg_file",
                        "path": file_path,
                        "mtime": file_mtime,
                        "unit_path": CAPTURES_DIR,
                        "unit_mtime": captures_mtime,
                        "size": file_stat.st_size,
                    }
                )

            except FileNotFoundError:
                continue
            except PermissionError:
                print(f"WARNING: Permission denied while scanning: {file_path}")

    # 2. Dynamic folders as whole-folder units.
    for folder in get_dynamic_folders():
        folder_mtime = safe_mtime(folder)

        if folder_mtime >= cutoff_timestamp:
            continue

        folder_size = get_path_size(folder)

        candidates.append(
            {
                "kind": "dynamic_folder",
                "path": folder,
                "mtime": folder_mtime,
                "unit_path": folder,
                "unit_mtime": folder_mtime,
                "size": folder_size,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["unit_mtime"],
            item["mtime"],
            str(item["path"]),
        )
    )

    return candidates


def planned_until_under_limit(candidates, starting_size: int):
    planned = []
    simulated_size = starting_size

    for item in candidates:
        if simulated_size <= SIZE_LIMIT_BYTES:
            break

        planned.append(item)
        simulated_size -= item["size"]

    return planned, simulated_size


def delete_candidates(candidates, dry_run: bool):
    deleted_count = 0
    deleted_size = 0

    for item in candidates:
        path = item["path"]

        if item["kind"] == "jpg_file":
            label = "JPG"
        else:
            label = "DYNAMIC_FOLDER_RECURSIVE"

        print(
            f"{'DRY RUN' if dry_run else 'DELETE'} | "
            f"type={label} | "
            f"unit_date={format_time(item['unit_mtime'])} | "
            f"item_date={format_time(item['mtime'])} | "
            f"size={format_bytes(item['size'])} | "
            f"{path}"
        )

        if dry_run:
            deleted_count += 1
            deleted_size += item["size"]
            continue

        try:
            if item["kind"] == "jpg_file":
                path.unlink()
            elif item["kind"] == "dynamic_folder":
                shutil.rmtree(path)

            deleted_count += 1
            deleted_size += item["size"]

        except FileNotFoundError:
            continue
        except PermissionError:
            print(f"WARNING: Permission denied while deleting: {path}")
        except OSError as error:
            print(f"WARNING: Could not delete {path}: {error}")

    return deleted_count, deleted_size


def print_scan_units():
    print("Folder units, oldest to newest:")

    units = []

    if CAPTURES_DIR.exists():
        units.append(("captures", CAPTURES_DIR, safe_mtime(CAPTURES_DIR)))

    for folder in get_dynamic_folders():
        units.append(("dynamic", folder, safe_mtime(folder)))

    units.sort(key=lambda item: (item[2], str(item[1])))

    if not units:
        print("  No folder units found.")
        return

    for unit_type, path, mtime in units:
        print(f"  {format_time(mtime)} | {unit_type} | {path}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Delete old JPGs from captures and recursively delete old dynamic folders. "
            "Then keep /home/pi/Automator/data under 5 GiB."
        )
    )

    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete files and dynamic folders. Without this flag, dry run only.",
    )

    args = parser.parse_args()
    dry_run = not args.delete

    print("Automator images cleanup started")
    print(f"Data folder: {DATA_DIR}")
    print(f"Size limit: {format_bytes(SIZE_LIMIT_BYTES)}")
    print(f"Mode: {'DELETE' if args.delete else 'DRY RUN'}")
    print()

    starting_size = get_total_size(DATA_DIR)
    print(f"Starting data size: {format_bytes(starting_size)}")
    print()

    print_scan_units()
    print()

    # Phase 1: Always delete JPGs older than 21 days,
    # and dynamic folders whose folder date is older than 21 days.
    print("PHASE 1: Delete JPGs older than 21 days and dynamic folders older than 21 days")
    phase1_candidates = collect_candidates(TWENTY_ONE_DAYS_SECONDS)

    if not phase1_candidates:
        print("No Phase 1 candidates found.")
        phase1_deleted_count = 0
        phase1_deleted_size = 0
    else:
        phase1_deleted_count, phase1_deleted_size = delete_candidates(
            phase1_candidates,
            dry_run=dry_run,
        )

    print()
    print(f"Phase 1 matched items: {phase1_deleted_count}")
    print(f"Phase 1 matched size: {format_bytes(phase1_deleted_size)}")
    print()

    if dry_run:
        size_after_phase1 = starting_size - phase1_deleted_size
    else:
        size_after_phase1 = get_total_size(DATA_DIR)

    print(f"Size after Phase 1: {format_bytes(size_after_phase1)}")
    print()

    # Phase 2: If still above 5 GiB, delete oldest eligible items,
    # but do not delete anything newer than 14 days.
    if size_after_phase1 <= SIZE_LIMIT_BYTES:
        print("PHASE 2: Not needed. Data folder is at or below 5 GiB.")
    else:
        print(
            "PHASE 2: Still above 5 GiB. "
            "Deleting oldest eligible items older than 14 days until under limit."
        )

        phase2_all_candidates = collect_candidates(FOURTEEN_DAYS_SECONDS)

        # Avoid double-counting Phase 1 candidates during dry run.
        phase1_paths = {item["path"] for item in phase1_candidates}
        phase2_all_candidates = [
            item for item in phase2_all_candidates
            if item["path"] not in phase1_paths
        ]

        phase2_planned, simulated_final_size = planned_until_under_limit(
            phase2_all_candidates,
            size_after_phase1,
        )

        if not phase2_planned:
            print("No additional eligible items older than 14 days are available for Phase 2.")
        else:
            phase2_deleted_count, phase2_deleted_size = delete_candidates(
                phase2_planned,
                dry_run=dry_run,
            )

            print()
            print(f"Phase 2 matched items: {phase2_deleted_count}")
            print(f"Phase 2 matched size: {format_bytes(phase2_deleted_size)}")

            if dry_run:
                print(f"Estimated final data size: {format_bytes(simulated_final_size)}")

    print()

    if dry_run:
        print("Dry run complete. No files or folders were deleted.")
        print("Run again with --delete to actually delete the listed items.")
    else:
        final_size = get_total_size(DATA_DIR)
        print(f"Final data size: {format_bytes(final_size)}")

        if final_size > SIZE_LIMIT_BYTES:
            print()
            print("WARNING: Data folder is still above 5 GiB.")
            print("Reason may be: not enough eligible items older than 14 days were available to delete.")


if __name__ == "__main__":
    main()
