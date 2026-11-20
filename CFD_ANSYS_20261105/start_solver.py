import json
import os
import tempfile
from pathlib import Path
import ansys.fluent.core as pf

root=Path(__file__).resolve().parent
solver=pf.launch_fluent(
    fluent_path=r'C:\Program Files\ANSYS Inc\ANSYS Student\v261\fluent\ntbin\win64\fluent.exe',
    dimension=3,precision='double',processor_count=4,mode='solver',
    ui_mode='no_gui',cwd=str(root),
    cleanup_on_exit=False,start_watchdog=False,start_timeout=120,
    start_transcript=True)
props=solver.connection_properties
private=Path(tempfile.gettempdir())/'umbrella_fluent_connection_20261105.json'
private.write_text(json.dumps({'ip':props.ip,'port':props.port,'password':props.password}),encoding='utf-8')
print('CONNECTION_SAVED_IN_OS_TEMP',flush=True)
solver.settings.file.read_mesh(file_name=str(root/'coarse'/'nozzle.msh'))
solver.tui.mesh.check()
solver.tui.mesh.quality()
solver.settings.setup.models.viscous.model='k-omega'
print('VISCOUS_STATE',solver.settings.setup.models.viscous.get_state(),flush=True)
print('INLET_STATE',solver.settings.setup.boundary_conditions.velocity_inlet['inlet'].get_state(),flush=True)
print('OUTLET_STATE',solver.settings.setup.boundary_conditions.pressure_outlet['outlet'].get_state(),flush=True)
print('MATERIAL_STATE',solver.settings.setup.materials.fluid['air'].get_state(),flush=True)
print('REPORT_TYPES',solver.settings.solution.report_definitions.get_active_child_names(),flush=True)
print('SETUP_READY',flush=True)
