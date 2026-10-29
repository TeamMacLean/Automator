<!--
SPDX-License-Identifier: CC-BY-4.0
-->
<!-- markdownlint-disable MD060 -->

# Move incident and damage record — 7 August 2026

**Recorded by:** Dan MacLean
**Procedure being followed:** [Move_Procedure.md](Move_Procedure.md) (relocation from growth chamber TSL PGC07 to temporary storage)

This record documents what was found and what was damaged during the move. **The system is no longer in the state described by the build documentation** — read this before attempting the rebuild.

---

## 1. What was planned vs what happened

The move procedure assumed the umbilical (the cable loom between the controller unit and the gantry, through the chamber access) could be disconnected at the controller end and withdrawn intact, preserving the in-chamber routing for a quick reconnect.

In practice this was impossible. The as-built wiring did not match the tidy picture in the hardware documentation:

- **Extensive cable ties** throughout the loom and routing, far more than needed, binding the umbilical to the frame and to itself.
- **Numerous bodged wire-to-wire connections** — inline splices joining cables directly, rather than the connectors implied by the documentation.
- **Deliberate knots tied in wires** at multiple points, making it impossible to withdraw individual cables or the loom through the access.

The umbilical could not be removed in a timely fashion by disconnection alone.

## 2. Damage / destructive actions taken to complete the move

- **The 3D-printed cradle was destroyed** to free the wiring. It will need to be re-printed from the STLs in `mechanical/` (black PETG, 200 µm layers, 20% infill — see `mechanical/mechanical_guide.md`).
- **Many wires were cut close to their connectors** — effectively a disconnection, with near-full conductor length preserved, but these will all need re-terminating with proper connectors before reassembly.
- **Several bodged inline cable joints were cut through** where they could not be separated.

<!-- TODO (technician): complete the inventory below before the rebuild is scoped -->

| # | Wire / cable | Where cut | Re-termination needed |
| --- | --- | --- | --- |
| | | | |
| | | | |

Photos of the as-found wiring and the cut points should be added to the lab filestore and referenced here.

## 3. Consequences for the rebuild

The "reconnect and verify" rebuild in Move_Procedure.md §5 **no longer applies**. The rebuild is now a partial re-wiring job. A brief for the electronics workshop, listing the contradictions between the existing documents and the questions that must be answered from the parts, is in [document_brief.md](document_brief.md).

1. **Re-terminate every cut wire** with proper connectors (JST/XH, spade, or screw-terminal as appropriate — see the connector types on the MKS board and GPIO breakout in `hardware/Hardware_Documentation.md` §8). Replace, don't repair, any cable that had a bodged splice or knot mid-run; suitable replacement cables are itemised in `documentation/Bill_of_Materials.md` §9.
2. **Re-print the destroyed cradle** from the STLs in `mechanical/`.
3. **Treat the wiring documentation as as-designed, not as-built.** The schematic and pin maps remain the authority for *what connects to what*; they do not reflect how the previous wiring was physically routed or joined. Rewire to the schematic, cleanly.
4. **Full recalibration is mandatory** — with the wiring and mounts disturbed to this extent, assume `data/calibration.json` is invalid. Re-run `dev2/calibration.py`.
5. **Follow the from-scratch validation path**, not the quick-move path: `documentation/HandOver.md` §11 Option B (validate Klipper motion independently, verify each GPIO device, re-run workspace calibration) and the full acceptance tests — homing and end-stops on all axes, door interlock, vacuum hold ≥ 5 s, E-stop cuts all supplies, one complete imaging cycle.
6. **Safety re-check before first power-up:** with cut wires and severed splices in the loom, inspect every re-made connection for shorts and correct polarity *before* connecting the PSUs — in particular the 12 V motor wiring and anything that lands on the Pi's GPIO header.

## 4. Lessons / notes for the record

- The build was more improvised than the documentation suggests; future work on this instrument should verify physical wiring against the docs rather than trusting them.
- Any future relocation should budget for re-wiring, not just disconnection.
- When the system is rebuilt, replace splices and knots with connectorised, labelled cables so the next move is the clean procedure Move_Procedure.md describes.

---

**Sign-off:**

| Role | Name | Date |
| --- | --- | --- |
| Lab lead | | |
| Technician | | |