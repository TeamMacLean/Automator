<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

[![Repository](https://img.shields.io/badge/GitHub-Repository-black?logo=github)](https://github.com/rotsl/Automator)
[![Documentation](https://img.shields.io/badge/docs-Read%20the%20Docs-blue)](https://rotsl.github.io/Automator/)
[![PyPI Package](https://img.shields.io/pypi/v/automator-tsl.svg)](https://pypi.org/project/automator-tsl/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/automator-tsl?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLUE&right_color=RED&left_text=package-downloads)](https://pepy.tech/projects/automator-tsl)

# Automator: automated imaging of round Petri dishes/plates for magnaporthe analysis.

Automator is an open-source system for real-time automated imaging, tracking, and analysis of round Petri dishes/plates (90–100 mm) containing magnaporthe Orzae, integrating motion control, camera acquisition, and scheduling on Raspberry Pi hardware using Klipper, Moonraker, and a custom Python-based controller and web interface.

This package is the **installable distribution** of the Automator controller and its reference assets — for the full source repository, contributor guidelines, and changelog, see <https://github.com/rotsl/Automator>.

## Install on a new Raspberry Pi

### 1. System prerequisites (Raspberry Pi OS lite 64-bit)

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-dev \
  libcamera-dev libcamera-apps v4l-utils \
  libjpeg-dev libpng-dev libatlas-base-dev
```

### 2. Create a virtual environment and install the package

```bash
python3 -m venv venv_clean
source venv_clean/bin/activate
pip install --upgrade pip
pip install automator-tsl[pi]
```

The `[pi]` extra pulls in the Raspberry-Pi-only hardware dependencies (`picamera2`, `RPi.GPIO`, `gpiozero`). Omit it if you're only inspecting the bundled documentation/templates on a non-Pi machine.

### 3. Fetch the plate-detection model

The YOLO ONNX model used for plate detection is not bundled in this package (to keep it small) — fetch it from Hugging Face after install:

```bash
automator-fetch-model
```

This downloads `bestnew.onnx` from [`rotsl/petri_dish_yolo`](https://huggingface.co/rotsl/petri_dish_yolo) and places it at `~/Automator/data/bestnew.onnx`.

> **Integrity check:** the download is verified against a pinned SHA-256 digest before being copied into place. If the file has been tampered with or the upstream model has changed unexpectedly, the command will exit with an error and remove the file automatically.

### 4. Generate security keys, configure Klipper/Moonraker, and start the controller

Follow the full installation steps in [HandOver.md](https://github.com/rotsl/Automator/blob/main/documentation/HandOver.md), then start the controller:

```bash
python -m dev2.maincontroller
```

## Full documentation

The complete documentation site, including the step-by-step user guide, admin/maintainer handover, and run book, is published at:

<https://rotsl.github.io/Automator/>

## In this package

Alongside the Python code, this package installs a copy of the project's reference assets under `share/automator/` in your environment's install prefix:

- `share/automator/data/` — `calibration.json` (camera calibration reference)
- `share/automator/raw/` — runtime state directory (created empty on install)

## License

This package bundles software (MIT License), hardware design references (CERN Open Hardware Licence v2 - Strongly Reciprocal), and documentation (CC BY 4.0). See [LICENSE](https://github.com/rotsl/Automator/blob/main/LICENSE) for the full breakdown by component, and `LICENSE-MIT`, `LICENSE-CERN-OHL-S`, `LICENSE-CC-BY-4.0` for the individual license texts (all included with this package).

### Recommended citation

```bibtex
@software{R_Automator_Automated_Imaging_20252026,
author = {R, Rohan},
title = {{Automator: Automated Imaging of Microbial Plates}},
url = {https://github.com/rotsl/Automator},
year = {2025–2026}
}
```

## Institutional note

This package as part of the main repository represents research automation tooling developed at [The Sainsbury Laboratory, Norwich.](https://www.tsl.ac.uk)  
It is provided as-is for research and engineering use and is not a certified laboratory instrument unless approved by the institute.

Users are responsible for:

- validating the system for their experimental context  
- complying with local safety, electrical, and biological regulations  
- ensuring appropriate risk assessments are in place  

<div align="center">

<hr>

<p>
  <strong style="color:#1f6feb; font-size:1.05em;">
    🦠 Built for reproducible research automation.👨‍🔬
  </strong>
</p>

<p>
  <strong style="color:#238636;">
    <em>“Make the instrument part of the method.”</em>
  </strong>
</p>

</div>