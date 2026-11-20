import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from geometry import port,branch_grid,nozzle_profile
geo=json.loads((ROOT/'cad/geometry_checks.json').read_text(encoding='utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
objects={};checks=[]
for part in geo['parts']:
    bpy.ops.wm.stl_import(filepath=str(ROOT/'cad/reference'/(part['name']+'.stl')));ob=bpy.context.object;ob.name=part['name'];objects[part['group']]=ob
    color=(.08,.40,.46) if part['group']=='adapter' else (.12,.22,.31)
    material=bpy.data.materials.new(ob.name);material.diffuse_color=(*color,1);material.use_nodes=True
    material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1);material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.4;ob.data.materials.append(material)
    tr=BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],all_triangles=True)
    if part['group']=='adapter':
        for hole in geo['original_holes']:assert tr.ray_cast(Vector((hole['x'],hole['y'],-1)),Vector((0,0,1)),5)[0] is None
        inlet=[sum(tr.ray_cast(Vector((0,0,1)),Vector((s if a==0 else 0,s if a==1 else 0,0)),100)[3] for s in [-1,1]) for a in [0,1]]
        assert max(abs(inlet[a]-[82,88][a]) for a in [0,1])<.03
        ids=[];ods=[]
        for k in range(3):
            E,D=port(k,geo['adapter_height_mm']);origin=Vector(E+D*12.5);direction=Vector((0,1,0));radii=[]
            for sign in [-1,1]:
                hit=tr.ray_cast(origin,sign*direction,35);assert hit[0] is not None
                outer=tr.ray_cast(hit[0]+.01*sign*direction,sign*direction,5);assert outer[0] is not None
                radii.append((hit[3],hit[3]+.01+outer[3]))
            ids.append(sum(v[0] for v in radii));ods.append(sum(v[1] for v in radii));assert abs(ids[-1]-46)<.04 and abs(ods[-1]-50)<.04
        checks.append(dict(part='adapter',original_12_holes_clear=True,inlet_XY_mm=inlet,measured_port_ID_mm=ids,measured_port_OD_mm=ods))
    elif part['group']=='nozzle':
        h=part['print_size_mm'][2];widths=[]
        for y in [-74+148*j/60 for j in range(61)]:
            origin=Vector((0,y,h-.1));hits=[tr.ray_cast(origin,Vector((s,0,0)),30) for s in [-1,1]];assert all(v[0] is not None for v in hits)
            widths.append(sum(v[3] for v in hits))
        assert max(abs(v-geo['nozzle_gap_mm']) for v in widths)<.025
        length=sum(tr.ray_cast(Vector((0,0,h-.1)),Vector((0,s,0)),100)[3] for s in [-1,1]);assert abs(length-150)<.025
        errors=[]
        for zz in [1+(h-2)*j/80 for j in range(81)]:
            expected=nozzle_profile(zz,geo['nozzle_gap_mm'],geo['nozzle_length'],geo.get('nozzle_shoulder',150),geo.get('nozzle_plenum'))
            for axis,target in [(0,expected[1]),(1,expected[0])]:
                direction=Vector((int(axis==0),int(axis==1),0));actual=sum(tr.ray_cast(Vector((0,0,zz)),s*direction,100)[3] for s in [-1,1]);errors.append(abs(actual-target))
        assert max(errors)<.03
        heights=[max(v.co.z for v in ob.data.vertices if s*v.co.y>0) for s in [-1,1]];assert abs(heights[0]-heights[1])<.001
        checks.append(dict(part='nozzle',gap_samples=61,gap_range_mm=[min(widths),max(widths)],clear_span_mm=length,profile_samples=81,max_CAD_to_CFD_profile_error_mm=max(errors),opposite_outlet_end_heights_mm=heights))
(ROOT/'cad/airpath_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
world=bpy.data.worlds.new('Studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.78,.84,.90,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
for loc,power,size in [((200,-250,500),9000000,350),((-250,-200,200),6000000,300),((100,300,400),7000000,350)]:
    bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=power;ob.data.size=size;ob.rotation_euler=(Vector((0,0,80))-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(450,-600,400));cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO'
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=2
scene.view_settings.exposure=-1;scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
for kind in ['adapter','nozzle']:
    for k,ob in objects.items():ob.hide_render=k!=kind
    ob=objects[kind];height=max(v.co.z for v in ob.data.vertices);cam.rotation_euler=(Vector((0,0,height/2))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=max(height,180)+65
    scene.render.filepath=str(ROOT/'images'/f'CAD_{kind}.png');bpy.ops.render.render(write_still=True)
objects['adapter'].location.x=-110;objects['nozzle'].location.x=110
objects['adapter'].hide_render=False;objects['nozzle'].hide_render=False;objects['fit_sample'].hide_render=True;objects['fit_sample'].hide_set(True)
cam.rotation_euler=(Vector((0,0,95))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=450
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'cad/ThreeWay150_51mm_System.blend'))
print('CAD_NATIVE_AND_AIRPATH_VERIFIED',flush=True)
