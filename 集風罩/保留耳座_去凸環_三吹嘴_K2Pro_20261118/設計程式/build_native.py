"""Verify flat ear faces from STLs and render the actual geometry before/after."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'flat_ear_checks.json').read_text(encoding='utf-8-sig'))
parts={r['id']:r for r in data['parts']}
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001;scene.unit_settings.length_unit='MILLIMETERS'
def mat(name,color):
    obj=bpy.data.materials.new(name);obj.use_nodes=True
    obj.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    obj.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.4
    return obj
bodymat=mat('Original housing',(.045,.30,.37));tipmat=mat('Original removable tip',(.9,.31,.07));lowmat=mat('Original inlet',(.03,.16,.24))
def import_part(path,name,mesh_matrix,world_matrix,material):
    bpy.ops.wm.stl_import(filepath=str(path),use_scene_unit=False)
    ob=bpy.context.object;ob.name=name;ob.data.transform(mesh_matrix);ob.matrix_world=world_matrix
    ob.data.materials.append(material);return ob
def tree(ob):return BVHTree.FromPolygons([v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],all_triangles=True)
def span(t,p,axis):
    hits=[t.ray_cast(Vector(p),s*Vector(axis),1000) for s in [-1,1]]
    assert all(h[0] is not None for h in hits),(p,axis)
    return sum(h[3] for h in hits)
objects={};trees={};matrices={};flat_checks=[];flow_checks=[]
for group,xpos in zip(data['groups'],[-340,0,360]):
    key=group['position'];h=group['total_length_mm'];w=group['width_mm'];gap=group['preferred_gap_mm']
    matrix=Matrix(((0,1,0,xpos),(0,0,1,-h),(1,0,0,30.1),(0,0,0,1)));matrices[key]=matrix
    for name in group['parts']:
        row=parts[name];material=tipmat if '_tip_' in name else lowmat if name=='outer_inlet' else bodymat
        ob=import_part(row['STL'],name,Matrix(row['assembly_from_print']),matrix,material)
        ob['printable_part']=True;ob['group']=key;objects[name]=ob;trees[name]=tree(ob)
        if row['changed']:
            old_ob=import_part(row['source'],'Verification_source',Matrix(row['source_to_assembly']),Matrix.Identity(4),bodymat)
            old_tree=tree(old_ob);face=row['flat_assembly_Z_mm'];heights=[];old_heights=[];thicknesses=[];bores=[]
            for x,y in row['ring_centers_assembly_XY_mm']:
                for i in range(16):
                    a=2*math.pi*i/16;xx=x+3*math.cos(a);yy=y+3*math.sin(a)
                    hit=trees[name].ray_cast(Vector((xx,yy,face+3)),Vector((0,0,-1)),10)
                    old_hit=old_tree.ray_cast(Vector((xx,yy,face+3)),Vector((0,0,-1)),10)
                    bottom=trees[name].ray_cast(Vector((xx,yy,face-6)),Vector((0,0,1)),10)
                    assert hit[0] is not None and old_hit[0] is not None and bottom[0] is not None
                    heights.append(hit[0].z-face);old_heights.append(old_hit[0].z-face)
                    thicknesses.append(hit[0].z-bottom[0].z)
                bores.append(span(trees[name],(x,y,face-2),(1,0,0)))
            assert max(abs(v) for v in heights)<.002,(name,heights)
            assert min(old_heights)>1.49 and max(old_heights)<1.51
            assert max(abs(v-4) for v in thicknesses)<.02 and max(abs(v-4.4) for v in bores)<.03
            flat_checks.append({'id':name,'ring_count':2,'old_height_range_mm':[min(old_heights),max(old_heights)],
                                'new_height_range_mm':[min(heights),max(heights)],'ear_thickness_range_mm':[min(thicknesses),max(thicknesses)],
                                'M4_holes_mm':bores,'annular_surface_samples':len(heights)})
            bpy.data.objects.remove(old_ob,do_unlink=True)
    inlet=trees[group['parts'][0]];tip=trees[group['preferred_tip']]
    socket=span(inlet,(0,0,12),(0,1,0));bore=span(inlet,(0,0,25.1),(0,1,0))
    gaps=[span(tip,(0,-w/2+1+(w-2)*i/60,h-.1),(1,0,0)) for i in range(61)]
    width=span(tip,(0,0,h-.1),(0,1,0))
    assert abs(socket-55.4)<.03 and abs(bore-51)<.03
    assert max(abs(v-gap) for v in gaps)<.03 and abs(width-w)<.03
    result={'position':key,'socket_ID_mm':socket,'main_bore_mm':bore,'gap61_range_mm':[min(gaps),max(gaps)],'width_mm':width}
    if key=='outer':
        starts=[]
        for y in [-8.030094,8.030094]:
            hit=trees['outer_guided_body'].ray_cast(Vector((0,y,54)),Vector((0,0,1)),5)
            assert hit[0] is not None and abs(hit[0].z-55)<.01;starts.append(hit[0].z-55)
        result['guide_leading_faces_print_Z_mm']=starts
    flow_checks.append(result)

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.87,.91,.95,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.6;scene.world=world
lights=[]
for loc,power,size in [((200,-450,900),10000000,650),((-650,250,650),9000000,600),((700,500,700),11000000,600)]:
    bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=power;ob.data.size=size;aim(ob,(50,-150,30));lights.append(ob)
bpy.ops.object.camera_add(location=(450,1300,1250));camera=bpy.context.object;scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=1120;camera.data.clip_end=10000;aim(camera,(0,-150,30))
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1500;scene.render.resolution_y=950;scene.render.resolution_percentage=100
native=ROOT/'cad/original_ears_flat_faces_assembled_mm.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
scene.render.filepath=str(ROOT/'images/all_three_assembled.png');bpy.ops.render.render(write_still=True)
for ob in objects.values():ob.hide_render=ob['group']!='outer'
matrix=matrices['outer']
objects['outer_inlet'].matrix_world=matrix@Matrix.Translation((0,0,-40))
objects['outer_tip_g8'].matrix_world=matrix@Matrix.Translation((0,0,45))
camera.location=(930,520,680);camera.data.ortho_scale=690;aim(camera,(360,-190,30))
scene.render.resolution_x=1400;scene.render.resolution_y=1050
scene.render.filepath=str(ROOT/'images/outer_exploded.png');bpy.ops.render.render(write_still=True)

# Close-up is actual mesh geometry, with the two views using an identical camera.
for ob in objects.values():ob.hide_render=True
for ob in lights:ob.hide_render=True
for loc,power,size in [((25,-35,60),30000,40),((-30,-10,35),16000,35),((10,35,45),22000,35)]:
    bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=power;ob.data.size=size;aim(ob,(0,0,-2))
detail_row=parts['inner_body'];center=Vector((19.4,82.5,245))
old=import_part(detail_row['source'],'Detail_before',Matrix(detail_row['source_to_assembly']),Matrix.Translation(-center),bodymat)
after=objects['inner_body'].copy();after.data=objects['inner_body'].data.copy();scene.collection.objects.link(after)
after.name='Detail_after';after.matrix_world=Matrix.Translation(-center);after.hide_render=True
camera.location=(27,-30,28);camera.data.ortho_scale=31;aim(camera,(-1,0,-2))
scene.render.resolution_x=850;scene.render.resolution_y=700
scene.render.filepath=str(ROOT/'images/ear_before.png');bpy.ops.render.render(write_still=True)
old.hide_render=True;after.hide_render=False
scene.render.filepath=str(ROOT/'images/ear_after.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(native))
assert abs(bpy.context.scene.unit_settings.scale_length-.001)<1e-9
assert len([o for o in bpy.context.scene.objects if o.get('printable_part')])==7
for group in data['groups']:
    for name in group['parts']:
        ob=bpy.data.objects[name];expected=matrices[group['position']]
        assert max(abs(ob.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))<1e-5
result={'native_reopened':True,'assembled_poses_verified':True,'printable_parts':7,'flat_faces':flat_checks,
        'flow_dimensions':flow_checks,'verified_STL_sha256':{r['id']:hashlib.sha256(Path(r['STL']).read_bytes()).hexdigest() for r in data['parts']}}
(ROOT/'native_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ORIGINAL_EARS_RETAINED_ALL_8_RING_FACES_FLAT_NATIVE_PASSED',json.dumps(flat_checks),flush=True)
