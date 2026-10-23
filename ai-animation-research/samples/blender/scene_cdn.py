"""Blender (bpy) sample: the same 'CDN' beat built as a real 3D scene.
Clay/vinyl materials, three-point studio light, rim light, camera push-in,
spring-like pop-in of edge nodes, packet flying along an arc. Renders a short
9:16 clip with Cycles on CPU (EEVEE needs a GPU/display in headless containers).
Run:  python3 -I scene_cdn.py <out_dir> [frames] [samples]
"""
import bpy, math, sys, os
from mathutils import Vector

out_dir = sys.argv[1] if len(sys.argv) > 1 else 'render'
FRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 72
SAMPLES = int(sys.argv[3]) if len(sys.argv) > 3 else 48
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 540, 960   # 9:16 draft size
sc.render.fps = 24
sc.frame_start, sc.frame_end = 1, FRAMES
sc.view_settings.view_transform = 'AgX'          # filmic-ish tone mapping, like ACES in three.js
sc.view_settings.look = 'AgX - Medium High Contrast'

def clay(name, rgb, emit=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = 0.45
    b.inputs['Metallic'].default_value = 0.0
    b.inputs['Coat Weight'].default_value = 0.35          # clearcoat = vinyl-toy sheen
    b.inputs['Subsurface Weight'].default_value = 0.15    # slight SSS = clay look
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m

def rounded_box(name, loc, size, mat, bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = size
    mod = o.modifiers.new('bevel', 'BEVEL'); mod.width = bevel; mod.segments = 4
    o.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return o

BG = (0.043, 0.059, 0.10)
ACCENT = (0.78, 1.0, 0.24); PINK = (1.0, 0.37, 0.66); CYAN = (0.30, 0.94, 1.0)

# world: dark studio backdrop
w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (*BG, 1)
w.node_tree.nodes['Background'].inputs[1].default_value = 0.25

# floor
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
floor = bpy.context.object
fm = clay('floor', (0.07, 0.09, 0.16)); fb = fm.node_tree.nodes['Principled BSDF']
fb.inputs['Roughness'].default_value = 0.92; fb.inputs['Coat Weight'].default_value = 0.0; fb.inputs['Subsurface Weight'].default_value = 0.0
floor.data.materials.append(fm)

# user phone + origin server + edge nodes
phone = rounded_box('phone', (0, -4.2, 0.55), (0.55, 0.08, 1.1), clay('phone', (0.12, 0.15, 0.22)), 0.03)
screen = rounded_box('screen', (0, -4.25, 0.55), (0.46, 0.01, 1.0), clay('screen', CYAN, CYAN, 1.5), 0.0)
origin = rounded_box('origin', (0, 13, 1.4), (1.6, 1.6, 2.8), clay('origin', (0.23, 0.25, 0.41)), 0.15)
for i, dz in enumerate((0.6, 0.0, -0.6)):
    rounded_box(f'led{i}', (0, 12.18, 1.4 + dz), (1.2, 0.02, 0.12), clay(f'led{i}', PINK, PINK, 6.0), 0.0)

EDGES = [(-2.6, -1.2, 0.5), (2.9, -0.6, 0.5), (-3.4, 3.2, 0.5), (3.6, 3.8, 0.5), (0.4, 6.5, 0.5)]
edge_objs = []
for i, p in enumerate(EDGES):
    e = rounded_box(f'edge{i}', p, (0.9, 0.9, 1.0), clay(f'edge{i}', (0.16, 0.19, 0.29)), 0.12)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.06, location=(p[0], p[1], p[2] + 0.53))
    led = bpy.context.object; led.data.materials.append(clay(f'eled{i}', ACCENT, ACCENT, 5.0)); led.parent = e
    led.matrix_parent_inverse = e.matrix_world.inverted()
    edge_objs.append(e)
    # pop-in with overshoot (mimics a spring): scale 0 -> 1.15 -> 1
    f0 = 10 + i * 4
    e.scale = (0, 0, 0); e.keyframe_insert('scale', frame=f0)
    e.scale = (1.15, 1.15, 1.15); e.keyframe_insert('scale', frame=f0 + 6)
    e.scale = (1, 1, 1); e.keyframe_insert('scale', frame=f0 + 10)

# glowing packet flying along an arc user -> nearest edge -> user
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(0, -4.2, 0.6))
pk = bpy.context.object; pk.data.materials.append(clay('packet', ACCENT, ACCENT, 12.0)); bpy.ops.object.shade_smooth()
A, B = Vector((0, -4.2, 0.6)), Vector(EDGES[0]) + Vector((0, 0, 0.5))
for f in range(30, FRAMES + 1):
    u = (f - 30) / max(1, (FRAMES - 30)) * 2.0       # 0..2 ping-pong
    t = u if u <= 1 else 2 - u
    p = A.lerp(B, t); p.z += math.sin(t * math.pi) * 1.2
    pk.location = p; pk.keyframe_insert('location', frame=f)

# lights: big soft key, fill, cyan rim
def light(name, kind, loc, energy, color=(1, 1, 1), size=5):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = color
    if kind == 'AREA': ld.size = size
    o = bpy.data.objects.new(name, ld); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
light('key', 'AREA', (-7, -6, 10), 700, (1, 0.97, 0.92), 6)
light('fill', 'AREA', (8, -4, 5), 120, (0.75, 0.82, 1.0), 8)
light('rim', 'AREA', (0, 14, 6), 600, CYAN, 4)

# camera: push-in on the phone, then widen to reveal the edge ring
cam_d = bpy.data.cameras.new('cam'); cam_d.lens = 50; cam_d.dof.use_dof = True; cam_d.dof.focus_object = phone; cam_d.dof.aperture_fstop = 2.8
cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
cam.location = (0, -14, 7); aim(cam, (0, -2, 0.8)); cam.keyframe_insert('location', frame=1); cam.keyframe_insert('rotation_euler', frame=1)
cam.location = (2.5, -11, 5.5); aim(cam, (0, 0, 0.8)); cam.keyframe_insert('location', frame=FRAMES); cam.keyframe_insert('rotation_euler', frame=FRAMES)
# (Blender's default Bezier keyframes already ease in/out)

sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = os.path.join(out_dir, 'frame_')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, 'scene_cdn.blend'))
bpy.ops.render.render(animation=True)
print('DONE', out_dir)
