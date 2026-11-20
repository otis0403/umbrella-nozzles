import hashlib
from adapter_mesh import build
from design import ROOT,write_json

name='adapter_network_template'
summary=build(name,height=110,neck=46,fine=False)
assert all(summary['zones'].get(f'load_{k}',0)>0 for k in range(3))
assert all(summary['zones'].get(f'outlet_{k}',0)>0 for k in range(3))
assert summary['minimum_tetra_volume_m3']>0
write_json(ROOT/'cfd'/name/'template_integrity.json',
           {'height_mm':110,'neck_mm':46,'fine':False,
            'mesh_sha256':hashlib.sha256((ROOT/'cfd'/name/'nozzle.msh').read_bytes()).hexdigest(),
            'physical_port_lengths_mm':[25,35,25]})
print('THREE_WAY_NETWORK_TEMPLATE_PREFLIGHT_PASSED',flush=True)
