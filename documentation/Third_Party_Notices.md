<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Third-Party Notices

This document identifies third-party software components used by this project
and references their respective licenses.

The Automator project is released under the [MIT License](https://github.com/rotsl/Automator/blob/main/LICENSE). Third-party components
retain their original licenses and are used in accordance with those terms.

---

## Raspberry Pi OS

Project: Raspberry Pi OS  
Website: [https://www.raspberrypi.com/software/](https://www.raspberrypi.com/software/)

Raspberry Pi OS is a Debian-based operating system. It consists of many
independent software packages, each distributed under its own open-source
license in accordance with the Debian Free Software Guidelines (DFSG).

License information for individual packages is provided within the operating
system and by the Debian project.

---

## Klipper

Project: Klipper 3D Printer Firmware  
Repository: [https://github.com/Klipper3d/klipper](https://github.com/Klipper3d/klipper)
License file:[https://github.com/Klipper3d/klipper/blob/master/COPYING](https://github.com/Klipper3d/klipper/blob/master/COPYING)

License:  
`GNU General Public License version 3`

---

## Moonraker

Project: Moonraker (Klipper API Server)  
Repository: [https://github.com/Arksine/moonraker](https://github.com/Arksine/moonraker)  
License file:[https://github.com/Arksine/moonraker/blob/master/LICENSE](https://github.com/Arksine/moonraker/blob/master/LICENSE)

License:  
`GNU General Public License version 3`

---

## Mainsail

Project: Mainsail (Klipper Web Interface)  
Repository: [https://github.com/mainsail-crew/mainsail](https://github.com/mainsail-crew/mainsail)  
License file:[https://github.com/mainsail-crew/mainsail/blob/master/LICENSE](https://github.com/mainsail-crew/mainsail)

License:  
`GNU General Public License version 3`

---

## Python runtime dependencies (`requirements.txt`)

The following packages are installed at runtime and listed in `requirements.txt` / `pyproject.toml`.

| Package | Version | License |
| --- | --- | --- |
| numpy | 1.26.4 | BSD-3-Clause |
| opencv-python | 4.10.0.84 | Apache-2.0 |
| opencv-contrib-python | 4.10.0.84 | Apache-2.0 |
| Pillow | 11.3.0 | HPND (MIT-compatible) |
| picamera2 | 0.3.31 | BSD-2-Clause |
| Flask | 3.0.3 | BSD-3-Clause |
| werkzeug | 3.0.3 | BSD-3-Clause |
| Flask-SocketIO | 5.5.1 | MIT |
| python-socketio | 5.14.2 | MIT |
| eventlet | 0.40.3 | MIT |
| requests | 2.32.4 | Apache-2.0 |
| python-dotenv | 1.0.1 | BSD-3-Clause |
| qrcode | 8.0 | MIT |
| segno | 1.6.6 | BSD-3-Clause |
| zxing-cpp | 2.2.0 | Apache-2.0 |
| onnxruntime | 1.18.0 | MIT |
| RPi.GPIO | 0.7.1 | MIT |
| gpiozero | 2.0.1 | BSD-3-Clause |
| pyserial | 3.5 | BSD-3-Clause |
| reportlab | 4.2.0 | BSD-style (ReportLab License) |
| huggingface_hub | 0.23.4 | Apache-2.0 |

Each package retains its original license. License texts are available via
`pip show <package>` or on the respective project page at
[https://pypi.org](https://pypi.org).

---

## Python development-only dependencies (`requirements-dev.txt`)

The following packages are used only during development and are not installed
in the deployed system.

| Package | Version | License |
| --- | --- | --- |
| ipython | 8.26.0 | BSD-3-Clause |
| rich | 13.7.1 | MIT |
| pytest | 8.3.2 | MIT |
| pytest-timeout | 2.3.1 | MIT |
| black | 24.8.0 | MIT |
| ruff | 0.6.3 | MIT |
| mypy | 1.11.2 | MIT |
| types-requests | 2.32.0.20240712 | Apache-2.0 |
| line-profiler | 4.1.3 | BSD-2-Clause |
| watchdog | 4.0.2 | Apache-2.0 |
| jupyterlab | 4.2.5 | BSD-3-Clause |
| matplotlib | 3.9.2 | PSF (BSD-compatible) |

---

## ONNX Machine Learning Models

The ONNX model files used by this project are documented in full detail — including
authorship, licensing, SHA-256 checksums, and Hugging Face Hub provenance — in:

`documentation/model_provenance.md`

Model files are located in the `data/` directory. Each model retains its original
license as documented in `documentation/model_provenance.md`.

---

## General Notice

All third-party software is used in accordance with its respective license.

This document is provided for reference only and does not replace or modify the
original license texts of the listed components.
