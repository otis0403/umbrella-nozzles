# Active 12/14/8 mm ANSYS rerun — 2026-11-17

## COMPLETE — CFD plus user-requested MODULAR release

Finalauthoritativedeliveryis `modular/DELIVERY_COMPLETE.json`, folder`case/集風罩/可換式三吹嘴_225x12_180x14_315x8_20261118`. MainZIP8STLs(6required+2reference16tips),Blender,assembly/exploded/interfacefigures,assemblyguideandcopiedCFDreport/CSV/checks. AllnativeCFDandmodulargeometry/dimension/ZIP/visualcheckscomplete;no ownedcomputejobsremain. NominalflowchannelunchangedbyexternalM4jointfeatures;physicalsealing/fit/strength/dryingunverified,all8CFDformalresidualflagsnotfullypassed. K1Csegmentationdeferredbyuser.

Finalmustanswerinitialquestion:totalQunderhyp460Pa/60cm matchedcomparison8.505→8.070(-5.11%),innermean13.80→16.97,middle16.67→18.02,outer17.49→17.17m/s. Thusmodesttotalvolumecostinexchangeforinnerreinforcement,notproofdryingtime.51mmhoseandoriginalenclosure/splitterremain. DeliverMODULARZIP,notparentfullsinglepieceZIP. Detailedcompletecheckpointinmodular/WORK_STATUS.md. No furtherapprovalortestsneeded.

## NEW USER STEERING — MUST DELIVER MODULAR NOZZLES

After CFD60cm results user explicitly said「我覺得你算完後一樣幫我設計成可換吹嘴的那種」. Task now includes fixedbody + removable43mm fronttip for ALL3 heads, not just full singlepieceSTLs. Existing CFD completed8newcases/nativeverified; parent fullreference delivery package already generated as an INTERNAL fluidshape reference, do not use it as the final model deliverable.

Current modular work is being created under `modular/`, design version20261118 (client currentdateupdated). Split at chamberdepth22mm before35mmcontraction+8mmstraight, so splitZ inner245,center205,outer345. Body/flowprofile remain; interchangeabletip length43mm. Outside-flow M4x16 bolts/nuts/washers,4/4/6 perhead(14/group), no printedthreads. Sealinggroove outsidechannel, two integrated screw-axis locator collars; exactnominalfluidpath preserved ifassembledflush/sealed. Includepreferred12/14/8tips and2comparison16mmtips(inner/center), total3bodies+5tips=8STLs. Allparts must be watertight/singlepositive, interfacecollisionfree, nativeBlenderreopened/dimensionverified. K1Csegmentation stilldeferred.

Need buildmodular, nativeassembled/explodedpreview, interface drawing, assemblynotes andMODULARZIP plus copiedCFDreport/CSV. Current fullCAD files undercad/full are referenceinputs only. Do not end until modular deliverable is checked. Existingfullreport result60cm8.505→8.070(-5.11%) remainsvalidfornominalcontinuousflow; assemblyleaks/fit notsimulated.

## 60cm matched comparison COMPLETE;50cm/native/models still running

New60cm reference16/16/8: total8.505112477,flows[2.980054855,2.880358778,2.644698843],speeds[13.796550257,16.668742930,17.491394466],Pin460.251339. Candidate12/14/8: total8.070487016,flows[2.749002746,2.725160332,2.596323938],speeds[16.969152750,18.023547169,17.171454619],Pin460.187441. Totalchangeabout-5.11%,inner speedabout+23%,middle+8%,outer-1.83%. User already told these primaryresults in commentary; final should still selfcontain.

All4 headpoints complete; new22512 curvea34.57722843,b11.43524551;18014 a36.92622110,b9.19411226. Latepressure rangesall<.18%, formalCFDheadconvergence stillnotfullypassed. Source22512 atQ2.16 coreCV8.067%,bodyreverse6.628%,Pt186.024Pa; atQ3.2 CV6.366%,reverse5.043%,Pt390.664Pa. RealANSYS confirms1Droughtradeoff direction; do not mislabelactualfanpoint or bestdesign.

## Implementation update

`build_selected_models.py`, `finish_delivery.py`, `package_delivery.py` are now implemented and pycompiled. Finisher watcher tool session50375 is running, waits forCFD terminalphase then builds2newSTL/preservesouter8SHA, creates/reopensBlender, rendersdimensions, packages3STL+Blender+MDreport+CSV+plots+checks/source+native10caseZIP+manifest.

Important final QA: comparevolumeimpactwith matched reference, not old8.53 at463Pa; new references and candidates target460within.1%. Review actual figures/MD values andbothZIPs before final. Mainbarlegend already has35%headroom so labels shouldnot overlap. NativecaseZIP should contain8newcases +2unchangedouterpoints (10cases,20files). Allnew formalconvergenceflags mustbe read, not assumedpass. Update deliveredstatus onlyafter visual review/solverclosure. Package outputs `case/集風罩/三尺寸吹嘴_225x12_180x14_315x8_ANSYS_20261117`.

## Latest user request

User: 「重新跑ansys，但先告訴我『整組風量約由8.53降至8.11m³/min』影響很多嗎」.

Already answered in commentary: decrease is~4.9%,~7L/s per blower group, modest in total volume; potentially worth testing in exchange for inner speed~23% and middle~8% increase from preliminary math. It is NOT a prediction of drying-time change. User explicitly authorized rerun; do not ask permission again. Preserve51mm hose and separate versions; no whole enclosure edits. Ignore K1C fit/segmentation for now.

Actual task: run new inner225x12,center180x14,outer315x8 with matched reference225x16,180x16,315x8, evaluate real CFD flow/speed tradeoff under nominal static460Pa and50/60cm cuts, deliver updated separate full models/report if worthwhile. New comparison is still prototype unless formal convergence passes. Prior user chose prototype/report over long transient work.

## Current process

`continue_study.py` launched with tool exec session66756; inspect current process inventory rather than assuming alive. `pipeline_state.json` and `head_curves_fluent.log` show phase. No other Fluent was running before launch. Only ONE Fluent session at a time.

Stage1 `stage_head_curves.json`, SIMPLE,4cores, 30x40 max iterations each:
1 inner225_g12_q2p16 L220/H288, gap12, Q2.16, warmseed_inner
2 inner225_g12_q3p2 Q3.2, warmcase1
3 center180_g14_q1p728 L180/H248, gap14,Q1.728,warmseed_center
4 center180_g14_q3p2 Q3.2,warmcase3

Warm fields are copied from independently verified original16mm head cases. `cfd_solver.py` in THIS folder only now scales interpolated velocity/omega byQratio, pressure/k byQratio² as an initial guess; all real Fluent iterations follow, no final fields are scaled. Newrun_stage assigns design.GAP perjob. Mesh metadata and area are gap-aware.

Stage2 controller fits separate nonnegative P=aQ²+bQ curves for22512 and18014 from2 CFDpoints each. Outer3158 curve reuses `Outer315_NarrowGap_ANSYS_20261117` unchanged. Selection.json written with gaps12/14/8; old files never edited.

Stage3 `stage_network.json`: matched 4 CFD networks:
- reference_16_16_8_hose60 using baseline_pressure_curves.json
- candidate_12_14_8_hose60 using selected_pressure_curves.json
- reference_16_16_8_hose50 baselinecurves
- candidate_12_14_8_hose50 selectedcurves

`solve_network.py` switches active curves for each job.baseline_curves. Tighter current matching: static target460Pa within.1%, load<.5%,Qchange<.15%,mass<.05%,3stable batches,max45x50. These are network matching gates, NOT full residual convergence. Results include network_three_stable_batches_pass. Both matching flags asserted before checkpoints.

Stage4 analyze all cases, verify all8 new native case/data through a fresh owned Fluent session; positive cell volumes and recomputed report agreement <2e-7. Final phase `CFD_and_native_readback_complete_models_report_pending`.

## Remaining implementation

1 Monitor stage work, correct actual recoverable errors. Check candidate network Q for ALL3 branches lies inside each fitted CFD range. No unbounded transient/fine-grid expansion without new reason.
2 Need write build_selected_models.py: create complete225G12,L220 and180G14,L180 with shared full_nozzle/ramp and design.GAP, manifold float32 rebuild/simplify like prior; preserve exact315G8 copied STL. All H288,248,388; wall2.4/tip2,socket55.4 insertion25,flowID51. Outer2guides retained, inner/middle none. Watertight,oneconnectedpositive solid, nondegenerate triangles, SHA. No split pieces.
3 build_native_models.py and draw_dimensions.py were copied from prior and already gap-aware. Read selection, namesgapsdynamic,61gap checks/width/socket/central clearance, reopenedBlender horizontal broadplane parallelfloor. Both ready to run onceSTLs built.
4 Outer actual-STL cutaway copied unchanged from prior; exact outerSTL SHA check must confirm unchanged. No need rerender same geometry.
5 Need write new report/package and finisher watcher. Deliver dated separate Chinese folder undercase/集風罩, full3STL,Blender,dimensions/main/cutaway,updated CSV+plots, MDreport,mainZIP,nativeZIP,checks/source and SHAmanifest. Do not use prior package_narrow_delivery.py unchanged; it assumes inner/middle16 and candidate16/10/8.
6 Need final report first address actual totalQ cost versus initial4.9% estimate; mean slot speed ALL3 before/after and CV/reverse where comparable, pressure assumptions, actual matching errors/residualflags. Real fanP–Q, drying, physicalfit/externaljet,grid independence/transient remain unverified.
7 Need inspect fresh nativecase results, geometry and images; only rerun visual packaging if actual issue. Close owned solvers/caches. Finish user reply selfcontained with firstquestion answer, actual new result and directSTL/ZIP/reportlinks; no confirmation.

## Existing complete baselines and assumptions

PRIOR=`../Outer315_NarrowGap_ANSYS_20261117` complete native-verified12? NO: its gaps are16/16/8! Outer8 solemodifiedthere.
- nominal static460/60cm old: total8.531184, flows[2.990164,2.889432,2.651588],speeds[13.84335,16.72125,17.53696],actualPin462.979Pa.
- nominal460/50cm old: total8.782257, speeds[14.27646,17.21919,18.00970],actualPin461.629Pa.
- old outer curvePt=44.20110959Q²+13.6647354Q,pointsQ2/3.024; outer fullSTL sha0f76ae2e12f1f269beaad7fceb69eda281e676a1572df9bd89fe97240e360dd8.
- outer2thin1.6mmguideplates Z55..332 ending56mm beforeoutlet. No centralplug. All current nozzles femaleID55.4/25 insertion accept originalR90OD55 plug; flowID51. Physical fit not yet tested.
- prior full new formal convergence flags werefalse; all native/filechecks passed. Keep separate.

HEADS original225/180 G16 root=`../Nozzles_225_180_315_G16_ANSYS_20261116`, pressurecurves usedonlybaseline comparison. Its selected heads H288/H248 andcoreCV15.306% atQ2.16 for225,5.556% atQ1.728 for180. Their .cas/.dat already verified.

1D SCREEN root=`../InnerMiddle_Narrowing_Screen_20261117`:
- calibrated model current16/16/8 total8.53267
- proposed12/14/8 total8.11322 speeds[17.05965,18.12594,17.25475]; baseline reproduction.0667% DOES NOT validate newlosses. NewANSYS will supersede.

All flow values perONEblowergroup. Fan330W,11m³/min,460Pa label is not a P–Q curve or known simultaneous operating point. Pressure boundary hypothetical, not actual measured fanrate. Original splitter82x88 inlet,ID46 branches, physicalport[25,35,25], center+10. Template68064cells/77425nodes already copied with meshhash. HoseID51,f=.04,lowerbendK=.5,jointK=.15 atID46; hosecuts50/60cm minus50mm insertions; R90 feedelbow included in eachheadCFD.

## Runtime/rules

Python C:/Users/otiso/umbrella/.venvs/airknife_20261114/Scripts/python.exe; Blender C:/Program Files/Blender Foundation/Blender5.1/blender.exe(actual path with space betweenBlender and5.1); FluentStudentv2614cores.
No subagents authorized, no goal tool created. Approvalnever do not supply sandbox_permissions. Fileaccessunrestricted. PreferRG -g patterns onWindows, notpath/*.json globs. Python -c quoting awkward; save scripts.
PowerShellredirectUTF16 but parent stage logsUTF8; convergence_control/analyze detectBOM. Blender exits0 even if Python error; check successmarkers/JSONfiles.
Commentary updates <=60sec. During solver wait, usefunctions.exec monitor notifyevery45sec pluswait<=60sec. Do not leave background solver active after claiming stopped.
Memory used registryMEMORY.md34-35,42-44, roll/thread01a19c93-233d-7623-aaab-db5419045a80. Current memory registry paused-status entry is stale; current workspace evidence takes precedence. Append exactlyone memorycitationblock at finalend. Do NOT editmemory unless userexplicitlyasks.
