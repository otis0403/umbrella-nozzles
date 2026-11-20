# Numerical data status

- User-selected design: three outlets and three straight 150 x 16 mm nozzles, male OD50 / ID46 spigots for ID51 hoses.
- Physical hose cut lengths: center/sides 50/70, 60/80, 100/120 cm. The final model subtracts 25 mm insertion at each end.
- Preliminary adapter pipe comparisons used CLEAR ID51 lengths, before the insertion correction. They are not the final cutting-length results.
- Early free-jet cases `jet_g16_L120_long_pipe` and `jet_g16_*_screen` were INVALIDATED: the mesh writer accidentally exported ambient as a wall. Their results are not admissible for nozzle selection. Invalidated cases remain flagged, and two originals are preserved under `cfd/archive_closed_ambient`.
- Some invalidated-case paths contain explicitly documented warm-start aliases. They are initial guesses only, never final simulation results.
- `open_*` cases verify ambient as a pressure outlet. Selected results must pass engineering convergence, actual boundary checks and native case/data reopening.
- Earlier 4/6/8/12 mm internal curves are exploratory only; the user subsequently fixed the outlet to 16 mm.
- Only the final print package and its manifest identify released print files. CAD, CFD and readback do not establish physical printing or drying performance.
- The user selected prototype-and-report delivery instead of additional transient simulation. The fine Coupled nozzle case did not meet engineering convergence and is diagnostic only. A separate SIMPLE continuation was stopped before completion for this handoff; its copied initial native files are not final SIMPLE results.
