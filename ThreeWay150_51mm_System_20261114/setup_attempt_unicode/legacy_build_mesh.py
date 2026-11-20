"""Conformal hex mesh. An external free jet includes ambient entrainment.
The CAD originals are never opened for writing. Fluent coordinates are SI.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from geometry import ROOT,section,area,config

def cosine(a,b,n):
    return a+(b-a)*(1-np.cos(np.linspace(0,np.pi,n+1)))/2

def axis(width,n,outer_limit=None):
    core=cosine(-width/2,width/2,n)
    if outer_limit is None:return core,0
    # Three cells resolve the 2.4 mm solid lip; ten graded outer cells.
    a=width/2;rim=config()['rim']
    f=np.r_[0,np.cumsum(1.55**np.arange(10))];f=f/f[-1]
    right=np.r_[np.linspace(a,a+rim,4)[:-1],a+rim+(outer_limit-a-rim)*f]
    return np.r_[-right[:0:-1],core,right[1:]],13

def build(name,height,gap,external=False,fine=False,reach=250.,span=252.,body=200.):
    out=ROOT/'cfd'/name;out.mkdir(parents=True,exist_ok=True)
    su,sv=(48,24) if not external else ((48,24) if fine else (36,18))
    dz=1.6 if not external else 2.
    z=np.r_[np.linspace(0,height,round(height/dz)+1),12,body,body+config().get('plenum',0),height-config()['land']]
    if external:
        z=np.r_[z,height+np.linspace(0,reach,round(reach/2)+1),height+30,height+50,height+80]
    if fine:z=np.r_[z,np.arange(body,height+.0001,1.)]
    z=np.array(sorted(set(round(float(v),7) for v in z)))
    coords=[]
    for zz in z:
        w,d,r=section(min(zz,height),height,gap,span,body)
        uu,offu=axis(w,su,200 if external else None)
        vv,offv=axis(d,sv,100 if external else None)
        u,v=np.meshgrid(uu,vv)
        inside=(abs(u)<=w/2+1e-8)&(abs(v)<=d/2+1e-8)
        radial=np.maximum(abs(u)/(w/2),abs(v)/(d/2));safe=np.maximum(radial,1e-30)
        bu,bv=abs(u)/safe,abs(v)/safe
        corner=inside&(bu>w/2-r)&(bv>d/2-r)&(r>1e-12)
        a=bu*bu+bv*bv;b=-2*(bu*(w/2-r)+bv*(d/2-r));c=(w/2-r)**2+(d/2-r)**2-r*r
        lam=(-b+np.sqrt(np.maximum(0,b*b-4*a*c)))/np.maximum(2*a,1e-30)
        blend=np.clip((radial-.85)/.15,0,1);blend=blend*blend*(3-2*blend)
        scale=np.where(corner,1+blend*(lam-1),1)
        coords.append(np.stack((-v*scale,u*scale,np.full_like(u,zz)),axis=-1))
    xyz=np.array(coords)/1000
    nz,nv,nu=np.array(xyz.shape[:3])-1
    fluid=np.ones((nz,nv,nu),bool)
    for k in range(nz):
        if external and (z[k]+z[k+1])/2<height:
            fluid[k]=False;fluid[k,offv:offv+sv,offu:offu+su]=True
    cid=np.zeros(fluid.shape,np.int32);ncell=int(fluid.sum());cid[fluid]=np.arange(1,ncell+1)
    ids=np.arange(np.prod(xyz.shape[:3])).reshape(xyz.shape[:3])
    k,j,i=np.nonzero(fluid)
    cell=np.stack([ids[k,j,i],ids[k,j,i+1],ids[k,j+1,i+1],ids[k,j+1,i],
                   ids[k+1,j,i],ids[k+1,j,i+1],ids[k+1,j+1,i+1],ids[k+1,j+1,i]],axis=1)
    used=np.unique(cell);remap=np.zeros(ids.size,np.int32);remap[used]=np.arange(1,len(used)+1)
    points=xyz.reshape(-1,3)[used];cell=remap[cell]-1
    assert ncell<1e6 and len(points)<1e6,(ncell,len(points))
    p=points[cell];vol=np.zeros(ncell);mintet=1.
    for a,b,c in [(1,2,6),(2,3,6),(3,7,6),(7,4,6),(4,5,6),(5,1,6)]:
        tet=np.einsum('ij,ij->i',np.cross(p[:,a]-p[:,0],p[:,b]-p[:,0]),p[:,c]-p[:,0])/6
        mintet=min(mintet,float(tet.min()));vol+=tet
    assert mintet>0,mintet
    zones={key:[] for key in [3,4,5,6,7,8]}
    def face(nodes,lo,hi,boundary):
        if not lo and not hi:return
        ns=remap[np.array(nodes)]
        if lo:ns=ns[::-1];c0,c1=lo,hi
        else:c0,c1=hi,0
        key=3 if lo and hi else boundary
        zones[key].append((*ns,int(c0),int(c1)))
    for k in range(nz):
        for j in range(nv):
            for i in range(nu+1):
                face((ids[k,j,i],ids[k,j+1,i],ids[k+1,j+1,i],ids[k+1,j,i]),
                     cid[k,j,i-1] if i else 0,cid[k,j,i] if i<nu else 0,
                     8 if external and i in [0,nu] else 6)
    for k in range(nz):
        for j in range(nv+1):
            for i in range(nu):
                face((ids[k,j,i],ids[k+1,j,i],ids[k+1,j,i+1],ids[k,j,i+1]),
                     cid[k,j-1,i] if j else 0,cid[k,j,i] if j<nv else 0,
                     8 if external and j in [0,nv] else 6)
    for k in range(nz+1):
        for j in range(nv):
            for i in range(nu):
                boundary=4 if k==0 else 5 if k==nz else 6
                if external and abs(z[k]-height)<1e-6:
                    near_u=offu-3<=i<offu+su+3;near_v=offv-3<=j<offv+sv+3
                    boundary=7 if near_u and near_v else 8
                face((ids[k,j,i],ids[k,j,i+1],ids[k,j+1,i+1],ids[k,j+1,i]),
                     cid[k-1,j,i] if k else 0,cid[k,j,i] if k<nz else 0,boundary)
    zones={key:np.array(val,np.int32) for key,val in zones.items() if val}
    names={3:('interior',2),4:('inlet',10),5:('outlet',5),6:('housing',3),7:('lip_rim',3),8:('ambient',5)}
    nface=sum(len(x) for x in zones.values())
    with (out/'nozzle.msh').open('w',encoding='ascii') as f:
        f.write('(0 "Modular air knife fluid mesh in metres")\n(2 3)\n')
        f.write(f'(10 (0 1 {len(points):x} 0))\n(12 (0 1 {ncell:x} 0))\n(13 (0 1 {nface:x} 0))\n')
        f.write(f'(10 (1 1 {len(points):x} 1 3)(\n');np.savetxt(f,points,fmt='%.12g');f.write('))\n')
        f.write(f'(12 (2 1 {ncell:x} 1 4))\n');first=1
        for key,rows in zones.items():
            f.write(f'(13 ({key:x} {first:x} {first+len(rows)-1:x} {names[key][1]:x} 4)(\n')
            for row in rows:f.write(' '.join(format(int(x),'x') for x in row)+'\n')
            f.write('))\n');first+=len(rows)
        f.write('(39 (2 fluid fluid)())\n')
        for key in zones:
            name,bc=names[key];typ={2:'interior',10:'velocity-inlet',5:'pressure-outlet',3:'wall'}[bc]
            f.write(f'(39 ({key:x} {typ} {name})())\n')
    summary={'name':out.name,'height_mm':height,'gap_mm':gap,'profile_config':dict(config()),'span_mm':span,'body_height_mm':body,'lip_length_mm':height-body,'external':external,'cells':ncell,'nodes':len(points),
        'inlet_area_m2':area(0,height,gap,span,body)*1e-6,'outlet_slot_area_m2':span*gap*1e-6,
        'volume_m3':float(vol.sum()),'min_tetra_volume_m3':mintet,'vane_count':0,
        'external_bounds_mm':[-100,100,-200,200,height,height+reach] if external else None,
        'zones':{names[key][0]:len(val) for key,val in zones.items()}}
    (out/'mesh_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('MESH_READY',str(out),ncell,len(points),flush=True)
    return summary

if __name__=='__main__':
    pa=argparse.ArgumentParser();pa.add_argument('name');pa.add_argument('--height',type=float,default=320)
    pa.add_argument('--gap',type=float,default=16);pa.add_argument('--span',type=float,default=252);pa.add_argument('--body',type=float,default=200)
    pa.add_argument('--external',action='store_true');pa.add_argument('--fine',action='store_true')
    a=pa.parse_args();build(a.name,a.height,a.gap,a.external,a.fine,span=a.span,body=a.body)
