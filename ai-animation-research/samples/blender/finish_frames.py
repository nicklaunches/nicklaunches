import bpy, sys, os
blend, out, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene; sc.frame_start, sc.frame_end = a, b
sc.render.filepath = os.path.join(out, 'frame_')
bpy.ops.render.render(animation=True); print('DONE')
