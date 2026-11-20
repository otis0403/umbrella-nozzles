# Modular replaceable tips, client date2026-11-18

## COMPLETE — reviewed modular delivery,2026-11-18 00:26 UTC+8

Finalfolder `case/集風罩/可換式三吹嘴_225x12_180x14_315x8_20261118`.
MainZIP `可換式三吹嘴_8件STL_模型與報告.zip`,29.9MB,CRCpassed andinventorychecked6requiredSTLs+2referenceSTLs+1embeddedBlender. Manual `組裝與更換說明.md`,CFDreportunder`ANSYS比較/風量影響與ANSYS報告.md`.

All8parts independentlyrereadwatertight/singlepositive/winding/nondegenerate;5body-tipcombinationsinterference~1e-12mm³ andaddedfeaturesflowprobe0. FreshBlendernative_reopenedtrue,all5tips61gaprays,width,22mmjoint,55.4socket,M4bores andlocatorfixed/floatingdimensionspassed; assemblytranslationcorrect andflowaxisparallelfloor. Mainassembled,explodedandinterfaceimagesvisuallyreviewed; copiedCFDbarfigureandfullmanualreviewed, nooverlap/labelissues. No task-ownedFluent/Blender/Pythonjobsremain.

CurrentfullCFD8newnativecase/data readbacksallpassed reportdifference0/positivevolumes;all8formalengineeringconvergenceflagsFALSE. Actualmatched460Pa:
-60cm reference Q8.505112477 speeds[13.796550257,16.668742930,17.491394466];candidateQ8.070487016 speeds[16.969152750,18.023547169,17.171454619];Qchange-5.110%,speeds+22.996%,+8.128%,-1.829%.
-50cm referenceQ8.763151478 speeds[14.243596737,17.180204390,17.974836406];candidateQ8.286829381 speeds[17.438057793,18.512432999,17.611006277].

Print6mainparts(3bodies+3tips12/14/8);2optional16mmtipsforinner/centerreference. M4x16qty14,nuts14,washers28/group. Fixedbodymustbeprintedonce;futuregapchangesonly43mmtip. Preserve51hose/R90/oldsplitter/enclosure. JointidealgeometrymatchesCFD;physicalfit,sealing,strength,durability,dryingunverified. K1Ccapacitysegmentationexplicitlydeferred.

ParentCFDfullmodelpackageisinternalreference, NOTthefinalmodeldeliverable. UsermustgetMODULARZIPabove. `DELIVERY_COMPLETE.json` here isauthoritativecurrentdeliverypointer. No moretests/permissionsneeded; remainingonlyconciseTraditionalChinesefinalanswercovering5.1%totalvolumecost,matchedspeeds,modularfilesandlimits. Appendmemorycitationblocklast once(MEMORY.md34-35,44;rollout01a19c93-233d-7623-aaab-db5419045a80). No memoryeditwasauthorized.

PackaginginitiallyfailedbecausePythoncp950defaultread_textcouldnotdecodeChineseparentDELIVERYjson;fixed3reads toexplicitutf8-sig,reranandCRCpassed. No geometry/rerenderneededafterthatfix.

User requested「我覺得你算完後一樣幫我設計成可換吹嘴的那種」while currentCFD wasfinishing. CFD/nativephase is nowcomplete, parentDELIVERY_COMPLETE.json exists. Parent fullmodelpackage isonlyinternal reference; finalmust beMODULAR.

Chosen architecture:
- inner225x12/H288 splitZ245; center180x14/H248 splitZ205; outer315x8/H388 splitZ345.
- Split atcommon22mmdeep chamber, removablelast43mm =35contraction+8straight. Futuregapchangesonlytip, allinletsID51/socket55.4 insertion25 maintained.
- 3fixedbodies +3preferredtips +2reference16mmtips(inner/center) =8STLs; alternatebodyprefixindependentofGAP beforecontraction.
- M4x16 throughbolts,nuts,2flatwashers each;4/4/6 positions perhead,14/group. HoleD4.4; Xshort±19.4, Ylong±(width/2-30), withcenterY0 extra for315. Earsradius7,zbody[split-4,split],ztip[split,split+4], externalonly, withinexistingmaxsocketwidth60.2.
- Two printablehollow locatorcollars ondiagonal screwaxes: bodyOD7.4,ID4.4,height1.5,topleadinOD7.0; tiprecessD7.9,depth1.8(radialclear.25,axialclear.3). Firstfixedround; secondpocketelongatedY1.0. TipallnonfirstboltholeselongY1.0 too, toallowprintinglengthtolerance; bodyallround.
- Bodyface sealinggroove width1.2,depth.5, outsidefluid (offsetfrominnerprofile.6..1.8). Flatcontactstops face atsplit, silicone onlygroove, avoidflowintrusion. No claimairtight/strength/durabilityphysicalvalidation.
- NeedcheckrereadSTL body^tipinterference volume~0, addedfeaturesoutsideflowprobe, eachpartclosedonepositive/no degenerates,61tipgaprays/socket/interfacewidth22 andbolt/locator dimensions viafreshBlenderBVH. Nativeassemblybroadplaneparallelfloor; tipSTLlocalZ0..43, assemblytranslation[0,0,split].
- CreateactualCADassembledandexplodedviews +interface dimensionaldiagram, assemblymanual,MODULARZIP andcopyparentCFDreport/CSVs. Verifyfigures/ZIP andnocurrentownedsolverjobs.

Current baseline sourceCAD andCFD arefullycomplete underparent. Parent60cm refspeeds[13.79655,16.66874,17.49139],candidate[16.96915,18.02355,17.17145],Q8.505112→8.070487(-5.11%),allunderhypstatic460. CFDresidualflagsstillnotallpass, reportprototypeonly. Newmodulejointnominalsameflowshape, actualseamsealingunverified.

Tool/runtime: venvPython ../.venvs/airknife_20261114 relativeproject root; exact C:/Users/otiso/umbrella/.venvs/airknife_20261114/Scripts/python.exe. Blender C:/Program Files/Blender Foundation/Blender 5.1/blender.exe. Librariesmanifold3d/trimesh/numpy available. Useparentcad_utils cylinder(diameter,length,center),box,loft,mesh; ringfromparentbuild_parts. CSGintersection is^, not&. Parentimportsys.path but localROOTmustremainmodularfolder. Exportfloat32rebuild/simplify withverytighttol; compareconsistentlyrereadmeshes toavoidprecisionfalsecollisions.

No memoryupdatesauthorized, no subagents, no goal. Userprefersaction, no repeatedconfirmation. Keepupdates<=60sec. FinalreplymustanswervolumeimpactandprovideMODULARSTLZIP/model/report, withconditionalnumbersandCFD/fitlimitations. Appendone memorycitationblocklast (MEMORY.md34-35,44;thread01a19c93-233d-7623-aaab-db5419045a80).
