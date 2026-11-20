import argparse,hashlib,json,math
import numpy as np
import trimesh
from geometry import ROOT,HOLES,boundary,root_grid,branch_grid,port_grid,cross_grid,nozzle_profile,nozzle_height
from cad_utils import loft,rect_loft,cylinder,mesh,save3mf

def split_solid(height=120,neck=46):
    n=64
    outer=rect_loft([0,30],lambda z:boundary(cross_grid(92.8,86.8,5.4,n,n)))
    flange=rect_loft([0,3],lambda z:[(x+2,y) for x,y in boundary(cross_grid(120,118,4,n,n))])
    outer=outer+flange
    lower=rect_loft([-1,10.001],lambda z:boundary(cross_grid(88,82,3,n,n)))
    air=lower
    for k in range(3):
        root=[np.c_[boundary(root_grid(k,z,n,n)),np.full(4*n,z)] for z in np.r_[9.999,np.linspace(10,30,41)]]
        air=air+loft(root)
        outer=outer+loft([boundary(branch_grid(k,float(t),height,n,n,2.4,neck)) for t in np.linspace(0,1,101)])
        air=air+loft([boundary(branch_grid(k,float(t),height,n,n,0,neck)) for t in np.r_[-.000001,np.linspace(0,1,101)]])
        outer=outer+loft([boundary(port_grid(k,s,height,n,n,25)) for s in [-.1,25]])
        air=air+loft([boundary(port_grid(k,s,height,n,n,23)) for s in [-.1,25.1]])
    solid=outer-air
    for h in HOLES:solid=solid-cylinder(h['d'],6,[h['x'],h['y'],1.5],segments=96)
    return solid

def nozzle_solid(gap=6,length=120):
    h=nozzle_height(length);zs=np.unique(np.r_[np.linspace(0,h,int(h*2)+1),25,30,25+length,h-8])
    def profile(z,wall):
        w,d,r=nozzle_profile(z,gap,length);return boundary(cross_grid(w+2*wall,d+2*wall,r+wall,64,64))
    outside=[]
    for z in zs:
        wall=2+ .4*float(np.clip((z-25)/5,0,1))*float(np.clip((h-z-8)/5,0,1))
        outside.append(np.c_[profile(z,wall),np.full(256,z)])
    air=rect_loft(np.r_[-.1,zs,h+.1],lambda z:profile(max(0,min(h,z)),0))
    return loft(outside)-air

def export(obj,name,group,records):
    assert len(obj.decompose())==1,(name,'components')
    tm=mesh(obj.simplify(.00001));assert tm.is_watertight and tm.volume>0
    ref=ROOT/'cad/reference'/(name+'.stl');tm.export(ref)
    sizes=tm.extents;assert (sizes[:2]+10<=220).all() and sizes[2]<=250
    out=tm.copy();out.vertices-=np.r_[tm.bounds.mean(0)[:2],tm.bounds[0,2]]
    stl=ROOT/'print/STL'/(name+'_mm.stl');out.export(stl)
    reread=trimesh.load_mesh(stl,process=True)
    assert reread.is_watertight and reread.is_winding_consistent and len(reread.split(only_watertight=False))==1
    assert reread.area_faces.min()>1e-10
    save3mf(ROOT/'print/3MF'/(name+'.3mf'),out.vertices,out.faces,name,(110,110,0))
    record=dict(name=name,group=group,assembly_bounds_mm=tm.bounds.tolist(),print_size_mm=sizes.tolist(),volume_mm3=float(tm.volume),triangles=len(tm.faces),
        sha256=hashlib.sha256(stl.read_bytes()).hexdigest(),closed_single_solid=True,independent_STL_readback=True,minimum_triangle_area_mm2=float(reread.area_faces.min()))
    records.append(record);print('CAD_READY',name,sizes.tolist(),flush=True)

def main(height,neck,gap,length):
    for p in ['cad/reference','print/STL','print/3MF','images']:(ROOT/p).mkdir(parents=True,exist_ok=True)
    records=[]
    export(split_solid(height,neck),f'splitter_H{height:g}_neck{neck:g}','adapter',records)
    export(nozzle_solid(gap,length),f'nozzle_150x{gap:g}_H{nozzle_height(length):g}','nozzle',records)
    export(cylinder(50,25,[0,0,12.5],segments=192)-cylinder(46,27,[0,0,12.5],segments=192),'fit_sample_OD50_ID46','fit_sample',records)
    (ROOT/'cad/geometry_checks.json').write_text(json.dumps(dict(parts=records,adapter_height_mm=height,adapter_neck_mm=neck,nozzle_gap_mm=gap,nozzle_length=length,
        original_holes=HOLES,spigot_OD_mm=50,spigot_ID_mm=46,insertion_mm=25,actual_slicing_verified=False,physical_print_verified=False),indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--height',type=float,default=120);p.add_argument('--neck',type=float,default=46);p.add_argument('--gap',type=float,default=6);p.add_argument('--length',type=float,default=120);a=p.parse_args();main(a.height,a.neck,a.gap,a.length)
