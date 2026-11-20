"""Run explicit stage jobs and close the owned Fluent session on completion."""
import argparse
import json
import os
import time
from pathlib import Path
import hashlib
import numpy as np

from design import ROOT, write_json
from nozzle_mesh import build
from cfd_solver import connect, solve, PRIVATE


def postprocess(name):
    folder = ROOT/'cfd'/name
    result = json.loads((folder/'results.json').read_text())
    cells = np.load(folder/'cell_fields.npz')
    xyz = cells['SV_CENTROID'].reshape(-1, 3)
    volume = cells['SV_VOLUME']
    body = (xyz[:, 2] > .025) & (xyz[:, 2] < result['conditions']['height_mm']/1000)
    reverse = body & (cells['SV_W'] < -.01)
    result['nozzle_body_reverse_axial_volume_pct'] = 100*float(volume[reverse].sum()/volume[body].sum())
    write_json(folder/'results.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('plan')
    args = parser.parse_args()
    plan = json.loads((ROOT/args.plan).read_text())
    os.environ['CFD_ACTIVE_LOG'] = str(ROOT/plan['log'])
    session = connect(launch=True, cleanup=True)
    completed = []
    try:
        for job in plan['jobs']:
            folder = ROOT/'cfd'/job['name']
            checkpoint = folder/'completed_checkpoint.json'
            signature = {k:v for k,v in job.items() if k not in ['warm','batches','reuse']}
            intact = False
            if checkpoint.exists() and (folder/'results.json').exists():
                saved = json.loads(checkpoint.read_text())
                intact = saved.get('signature') == signature
                intact = intact and hashlib.sha256((folder/'results.json').read_bytes()).hexdigest() == saved.get('result_sha256')
                intact = intact and all((folder/name).exists() and (folder/name).stat().st_size == size for name,size in saved.get('native_sizes',{}).items())
            if intact and job.get('reuse', True):
                print('REUSED_CASE', job['name'], flush=True)
                completed.append(job['name'])
                continue
            builder=build
            if job.get('guided'):
                from guided_mesh import build as builder
            builder(job['name'], job['width'], job['length'], job.get('external', False), job.get('fine', False), job.get('reach', 250), job.get('profile_kind','quintic'))
            solve(session, job['name'], q=job['q'], batches=job.get('batches', 25), warm=job.get('warm'))
            result = postprocess(job['name'])
            write_json(checkpoint, {'signature':signature,'result_sha256':hashlib.sha256((folder/'results.json').read_bytes()).hexdigest(),
                                   'native_sizes':{name:(folder/name).stat().st_size for name in ['solution.cas.h5','solution.dat.h5']}})
            completed.append(job['name'])
            write_json(ROOT/(Path(args.plan).stem+'_progress.json'), {'completed': completed, 'last_result': result, 'time': time.time()})
    finally:
        session.exit(timeout=20, wait=30)
        PRIVATE.unlink(missing_ok=True)
        write_json(ROOT/(Path(args.plan).stem+'_finished.json'), {'completed': completed, 'plan': args.plan, 'owned_solver_closed': True})
        print('OWNED_SOLVER_CLOSED', flush=True)


if __name__ == '__main__':
    main()
