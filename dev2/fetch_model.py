# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R
"""Console-script entry point: fetch the YOLO plate-detection model from Hugging Face."""

import hashlib
import os
import shutil

from huggingface_hub import hf_hub_download

HF_REPO_ID = "rotsl/petri_dish_yolo"
HF_FILENAME = "bestnew.onnx"

# SHA-256 of the known-good bestnew.onnx from rotsl/petri_dish_yolo.
EXPECTED_SHA256 = "b8eaa58a86a20b3ba6c8527a9013b69fb6674bf383426eea90cab17fa486a5d2"

# Matches the fallback path already hardcoded in dev2/mainusbcamera.py's
# YOLO_MODEL lookup, so no code changes are needed there.
DEST_PATH = os.path.expanduser("~/Automator/data/bestnew.onnx")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(os.path.dirname(DEST_PATH), exist_ok=True)
    downloaded_path = hf_hub_download(repo_id=HF_REPO_ID, filename=HF_FILENAME)

    digest = _sha256(downloaded_path)
    if digest != EXPECTED_SHA256:
        os.remove(downloaded_path)
        raise RuntimeError(
            f"SHA-256 mismatch for {HF_FILENAME}.\n"
            f"  expected: {EXPECTED_SHA256}\n"
            f"  got:      {digest}\n"
            "File removed. Do not use this model."
        )

    shutil.copyfile(downloaded_path, DEST_PATH)
    print(f"Model downloaded and verified → {DEST_PATH}")


if __name__ == "__main__":
    main()
