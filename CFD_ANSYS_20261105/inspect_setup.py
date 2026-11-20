from session import connect
s=connect()
r=s.settings.solution.report_definitions
r.surface.create('pin')
print('SURFACE_REPORT',r.surface['pin'].get_state(),flush=True)
print('REPORT_TYPE_OPTIONS',r.surface['pin'].report_type.allowed_values(),flush=True)
print('METHODS',s.settings.solution.methods.get_state(),flush=True)
print('CONTROLS',s.settings.solution.controls.get_state(),flush=True)
print('RESIDUAL',s.settings.solution.monitor.residual.get_state(),flush=True)
print('INITIALIZATION',s.settings.solution.initialization.get_state(),flush=True)
print('REDUCTION_METHODS',[x for x in dir(s.fields.reduction) if not x.startswith('_')],flush=True)
print('FIELD_DATA_METHODS',[x for x in dir(s.fields.field_data) if not x.startswith('_')],flush=True)
print('SURFACES_CHILDREN',s.settings.results.surfaces.get_active_child_names(),flush=True)
