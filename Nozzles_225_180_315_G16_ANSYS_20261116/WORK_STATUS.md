# Current nozzle task

## Latest checkpoint after midnight 2026-11-17

- Selected ramp heads are full 225/L220/H288, 180/L180/H248, 315/L320/H388. The guided315 prototype is now selected: like-for-like Q3.024 m3/min core CV42.33 to25.97%, reverse body volume17.20 to7.75%, required Pt250.37 to258.17Pa. These are still oscillating steady prototype results.
- `use_guided315.flag` exists. `build_native_models.py` has successfully rerendered and independently reopened the correct horizontal guided315 model, labels/order now correct, measured gap/width/socket and guide_count2 in native_geometry_checks.json.
- Actual-STL cutaway and dimension drawings were viewed. `plot_internal_flow.py` plots actual Fluent cut faces; no interpolation across solid plate gaps.
- Current active guide session is serial, finishing q1.5 and q4.5. Updated waiting controller is tool session69060, launched as continue_study.py; it waits until all three guide jobs close.
- Scope focused on required prototype work: high-flow points180/225; then exactly three network conditions (60cm static460,50cm static460, fixed total11 with60cm); then fresh native readback. No external jet or fine-mesh stage is planned for this prototype. Such validation is explicitly unverified in the report, consistent with the user's earlier prototype/report preference.
- `verify_native_cfd.py` reads native case/data and recomputes reports/positive volumes. `package_delivery.py` is prepared, but MUST wait for pipeline state raw_CFD_and_independent_native_readback_complete_report_pending. It creates 3 full STL package, Blender, MD report, CSV and separate 6-case native ZIP. Review actual report values/figures and ZIP after it runs.
- After pipeline completes run package_delivery.py, inspect report and flow values and all outputs, close owned solvers, then deliver links with conditional airflow and convergence limits. No whole-enclosure modifications.

User requests three complete nozzles, inside to outside 225 x 16, 180 x 16, 315 x 16 mm, with recalculated airflow. User explicitly deferred printer-size/segmentation constraints. Do not modify the full enclosure in this task.

All work is under this ASCII folder. Existing project model revisions are inputs only. Python is `C:/Users/otiso/umbrella/.venvs/airknife_20261114/Scripts/python.exe`; Blender 5.1.2 and Fluent Student v261 are installed.

## Current modeling results

- Complete ramp-profile models built and watertight: W180/L180/H248, W225/L220/H288, W315/L320/H388. Female socket 55.4 mm, effective feed 51 mm, gap 16 mm. Full STL references are in `cad/full`.
- Raw new ramp CFD includes the R90 feed elbow. At nominal 10 m/s outlet average, 180 mm core-line CV ~5.56%, body reverse volume ~2.41%. Unguided 315 mm core-line CV ~42.33%, body reverse volume ~17.20%, edges ~3 m/s vs center ~13.4 m/s. Thus 315 is being refined with two integrated 1.6 mm plates ending 56 mm before outlet.
- `guide_geometry.py` shares plate geometry between CAD and CFD. `build_guided_parts.py` built a watertight full guided315 STL. `guided_mesh.py` preflight: 242672 cells, positive tetra volumes.
- Current steady results have residual oscillation. Report them as numerical prototypes and list convergence flags, never claim physical airflow/drying validation.

## Process state and sequencing

- Original screen session was closed after three saved native cases. Case `screen_w315_L260` has mesh only and is superseded, not a completed result.
- Ramp phase finished all three cases and closed.
- Four pressure-curve cases finished and closed (`stage_curves_finished.json`).
- `wait_and_run_guided.py` is now running `stage_guided315.json` in its own Fluent session. Three jobs: guide_w315_L320 q3.024, guide_w315_q1p5, guide_w315_q4p5.
- The old `continue_study.py` controller (launcher PID 10336) was deliberately stopped at the `fit_curves.py` review gate while no Fluent child of that controller was active. Guide solver is a separately owned job and continues.
- `refine315.hold` blocks curve fitting until the guide comparison is accepted. Updated `continue_study.py` waits for guided315 to close, compares core CV, then removes hold, selects guided315, runs two high-flow points (180 q3.5, 225 q4.0), fits pressure curves, solves six network cases, then 3 operating jets plus fine315.
- Need start/restart UPDATED `continue_study.py` now. It safely waits for `stage_guided315_finished.json`. Check `pipeline_state.json` and phase logs. If guide stage fails/incomplete, fix and rerun missing jobs. Checkpoints prevent reuse of incomplete native results.
- Do not open a second Fluent while another owned solver is active. A concurrent second launch earlier was refused. Serial launch works. Never read another native case while an outstanding iteration RPC is still running.
- Credentials are in per-process temp private JSON and removed on normal closure. Never include them in delivery.

## Still required

1. Finish guide CFD and adopt if improved. Update complete315 native model via `use_guided315.flag` and rerun `build_native_models.py`. Horizontal native preview labels/order were fixed in source and need rerender.
2. High-flow cases and fitted curves. Network uses physical current splitter central neck +10 mm (mesh center port length35 vs side25), pressure load matching at interior `load_k` surfaces.
3. `solve_network.py` calculates per-branch flow for hypothetical total inlet pressures 200/300/400 Pa, equal 50/60 cm hose cuts, and fixed total11 m3/min to compute required static/total pressure. Current CAD hose cuts ~44.59/31.83/41.57 cm include both insertions; subtract50mm for ID51 exposed length. Assumptions f=.04, lower bend K=.5, joint K=.15. Fan P-Q curve unavailable. Report pressure assumptions explicitly.
4. External jets at actual network_P400 branch rates, and fine315. `analyze_cases.py` now uses physical slot fields for external cases, not domain outlet fields.
5. Fresh independent Fluent native readback of selected cases and primary network cases, compare reports and positive volumes; close all owned sessions.
6. CSV tables/plots and clear Chinese report, 3 full STLs, native Blender, preview, ZIP. No printer segmentation deliverables in current scope. Label actual fan operating point, physical fit and drying verification pending. Document if steady convergence criteria remain unmet.
7. Deliver to a separate Chinese folder under `case/集風罩` and give direct links. Keep original case artifacts unchanged.

## Final response facts to disclose

Three sizes are net outlet widths with 16 mm gap. Full model lengths likely 288/248/388 mm inner/center/outer. 315 prototype contains two thin guides if selected. Model flow axis is horizontal in native CAD. Larger total area is +60% vs 3x150x16. Wind values must be per-blower group and conditional on the prescribed pressure/flow. The fixed11 case is a required-pressure calculation, not proof the real blower supplies11 through this assembly.

Memory used this task: MEMORY.md lines23-30 and54-55, rollout/thread ID01a19c93-233d-7623-aaab-db5419045a80. Append one memory citation block at very end of final. Do not update memory files without user request.
