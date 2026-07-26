<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Changelog

All notable changes to this project will be documented in this file.

---

## [v3.0.0] - 2026-07-26

### Added

- Select All button in per-plate configuration panel
- Auto-dismissing Klipper/Moonraker offline popup (40 s, with dismiss button)

### Changed

- Workspace capacity increased from 5 to 6 round Petri dishes/plates (90–100 mm)
- Default imaging interval changed from 1 min to 30 min
- Default run duration changed from 1 h to 2 h
- Unresolved plate rows show light green background in config panel
- Unresolved plate X/Y coordinates displayed in red, larger font in workspace overlay
- Renamed from "microbial plates" to "round Petri dishes/plates (90–100 mm)" throughout

### Fixed

- Per-plate first-grip extended vacuum dwell (Fix B)
- Door sensor 3 s debounce to filter servo EMI false triggers (Fix C)
- Post-capture re-grip prevention (Fix D)

### Removed

- `dev2/templates/index2.html` (unused)
- `dev2/mainusbcamera1.py` (unused)
- `data/best.onnx` (superseded by `bestnew.onnx`)

---

Note: A separate repo is maintained with previous git history of this repo — [Automator-backup](https://github.com/rotsl/Automator-backup) [updated on 16/06/2026 17:00 Hrs]. This Repo was reinitialized on 26 July 2026 to remove any secrets/tokens that might have been previously committed.

---

## Versioning policy

- Release tags follow `vMAJOR.MINOR.PATCH` format.
- `Unreleased` tracks pending changes until the next tagged release.
