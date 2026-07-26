<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Contributing to Automator

Thank you for your interest in contributing to **Automator**.

This project supports **research automation involving physical hardware**.
As such, contributions are welcomed, but must follow clear rules to preserve
correctness, safety, and documentation integrity.

---

## Contribution scope

Contributions may include:

- Bug fixes
- Documentation improvements
- Refactoring with no behavioral change
- Performance or reliability improvements
- Additional tests or validation tooling

Contributions that affect **hardware behavior, safety logic, or system operation**
require additional review (see below).

---

## Documentation governance (important)

The following documents are considered **release-controlled**:

- [`README.md`](https://github.com/rotsl/Automator/blob/main/README.md)
- [`RunBook.md`](https://github.com/rotsl/Automator/blob/main/documentation/RunBook.md)
- [`HandOver.md`](https://github.com/rotsl/Automator/blob/main/documentation/HandOver.md)
- [`HowToUseAutomator.md`](https://github.com/rotsl/Automator/blob/main/documentation/HowToUseAutomator.md)
- [`ChangeLog.md`](https://github.com/rotsl/Automator/blob/main/ChangeLog.md)
- [`HARDWARE_BUTTONS_AND_SERVICES.md`](https://github.com/rotsl/Automator/blob/main/documentation/HARDWARE_BUTTONS_AND_SERVICES.md)
- [`OS_and_Firmware_installation.md`](https://github.com/rotsl/Automator/blob/main/documentation/OS_and_Firmware_installation.md)
- [`Security_Model_Credential_Management.md`](https://github.com/rotsl/Automator/blob/main/documentation/Security_Model_Credential_Management.md)
- [`diagnosticsserver.md`](https://github.com/rotsl/Automator/blob/main/documentation/diagnosticsserver.md)
- [`networkandprintsettings.md`](https://github.com/rotsl/Automator/blob/main/documentation/networkandprintsettings.md)
- [`model_provenance.md`](https://github.com/rotsl/Automator/blob/main/documentation/model_provenance.md)
- Any safety, security, or operational documentation

### Rules for these documents

Changes to release-controlled documents **must** correspond to at least one of:

- a verified behavior change
- a safety or risk-model change
- a change in intended use or scope

Cosmetic edits (formatting, wording) are acceptable.  
Meaningful changes **must be justified in the pull request description**.

---

## Release and version baseline

- Current released baseline is `v3.0.0`.
- If behavior, operations, or security posture changes, update `ChangeLog.md` in the same pull request.
- Use `ChangeLog.md` section structure (`Added`, `Changed`, `Fixed`, `Removed`) for release notes.

---

## Runtime boundary rules

Automator has separate runtimes:

- Controller runtime: `dev2/maincontroller.py` + imaging UI templates
- Diagnostics runtime: `dev2/maindiagnostics.py` + `dev2/main_mjpeg_server.py` + diagnostics templates

Contributors must:

1. State clearly which runtime is affected.
2. Avoid mixing unrelated controller and diagnostics changes in one pull request.
3. Update corresponding docs when runtime behavior changes.

---

## Safety-Critical changes

Any change that affects:

- physical motion
- emergency stop behavior
- pause / resume logic
- GPIO usage
- hardware timing
- power or actuator control

**must**:

1. Clearly describe the change and its motivation
2. State any new risks introduced
3. Confirm that existing safety guarantees still hold
4. Avoid overstating safety or certification claims

Software emergency stops are considered **best-effort controls** and must never
be described as safety-rated systems.

---

## Hardware assumptions

- Do not assume GPIO availability without documentation
- Do not share GPIO pins between processes
- Avoid historically reserved GPIOs unless justified
- A separate, hard-wired, latching external emergency stop is required; it is wired on the AC input and cuts power to all system supplies in an emergency. This hardware emergency stop is separate from the software/UI emergency stop control (reference: [`hardware/images/estop.jpg`](hardware/images/estop.jpg)).

Hardware-related changes should be accompanied by documentation updates in
the appropriate `documentation/` or `hardware/` subdirectory.

---

## Service and policy changes

Changes to service/policy behavior must include matching documentation updates:

- `/etc/systemd/system/automator-buttons.service`
- `/etc/polkit-1/rules.d/10-moonraker.rules`

Update at minimum:

- `documentation/HARDWARE_BUTTONS_AND_SERVICES.md`
- `documentation/RunBook.md` (operations baseline)

---

## Imaging naming and tag workflow changes

If you modify QR setup (`index_qr.html`) or capture naming logic:

- keep QR setup separate from the optional experiment-tag field on the main imaging page unless intentionally changing that workflow
- preserve `_tag-<clean_tag>` naming behavior for capture folders/files unless intentionally changed
- document the change in operator/operations docs

---

## Code style and quality

- Follow existing coding patterns
- Avoid introducing global side effects at import time
- Prefer explicit behavior over implicit assumptions
- Do not introduce breaking changes without discussion

All code must pass existing CI checks before review.

---

## Dependency changes

Development-only dependencies may be closed without merging if they do not
affect deployed systems or runtime behavior.

Security-related dependency updates are reviewed on a case-by-case basis.

---

## Pull request guidelines

Each pull request should include:

- A clear description of **what changed**
- Why the change is necessary
- Whether it affects:
  - system behavior
  - safety model
  - documentation scope

If a change affects operators or physical behavior, say so explicitly.

---

## Out of scope contributions

The following are **not accepted** without prior discussion:

- Claims of certification or safety compliance
- Medical, clinical, or diagnostic use cases
- Removal or weakening of safety disclaimers
- Bypassing systemd or lifecycle controls
- Introducing undocumented hardware dependencies

---

## Responsibility and use

By contributing, you acknowledge that:

- Automator is research tooling, not a certified instrument
- Contributors are responsible for the correctness of their changes
- Users remain responsible for validating the system in their environment

---

## Questions or proposals

For larger changes, open an issue first describing:

- the proposed change
- affected components
- potential risks
- expected benefits

This helps ensure alignment before work begins.

---

Thank you for helping improve Automator in a safe, transparent, and responsible way.