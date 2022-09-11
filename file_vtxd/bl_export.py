import os
import bpy
import bmesh
import mathutils as mu
import numpy as np

from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       )
from bpy_extras.io_utils import (ImportHelper,
                                 ExportHelper,
                                 unpack_list,
                                 unpack_face_list,
                                 axis_conversion,
                                 )

from . import format
from .. import io_binary


def __get_colors(mesh, color_i):
    colors = np.empty(len(mesh.loops) * 4, dtype=np.float32)
    layer = mesh.vertex_colors[color_i]
    mesh.color_attributes[layer.name].data.foreach_get('color', colors)
    colors = colors.reshape(len(mesh.loops), 4)
    # colors are already linear, no need to switch color space
    return colors


def save_vtxd(operator, context, filepath):
    # Export the selected mesh
    scene = context.scene
    vtxd = format.VertexData()

    mesh_obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for ob in mesh_obs:
        triangulate_object(ob)
        sub_mesh = save_vtxd_sub_mesh(ob)

        vtxd.sub_meshes.append(sub_mesh)

    exportFile = os.fsencode(filepath)
    if os.path.exists(exportFile):
        os.remove(exportFile)
    bre = io_binary.BinaryReader(open(exportFile, 'wb'))
    vtxd.write(bre)
    bre.close()

    return {'FINISHED'}


def save_vtxd_sub_mesh(blender_obj):
    mesh = blender_obj.to_mesh()
    sub_mesh = format.VertexDataSubMesh()

    dot_fields += [
        ('colorR', np.float32),
        ('colorG', np.float32),
        ('colorB', np.float32),
        ('colorA', np.float32),
    ]

    dots = np.empty(len(mesh.loops), dtype=np.dtype(dot_fields))

    if len(mesh.vertex_colors) > 0:
        colors = __get_colors(mesh, 0)
        dots['colorR'] = colors[:, 0]
        dots['colorG'] = colors[:, 1]
        dots['colorB'] = colors[:, 2]
        dots['colorA'] = colors[:, 3]
        del colors

    # Calculate triangles and sort them into primitives.
    mesh.calc_loop_triangles()
    loop_indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.uint32)
    mesh.loop_triangles.foreach_get('loops', loop_indices)

    prim_dots = dots[loop_indices]

    colors = np.empty((len(prim_dots), 4), dtype=np.float32)
    colors[:, 0] = prim_dots['colorR']
    colors[:, 1] = prim_dots['colorG']
    colors[:, 2] = prim_dots['colorB']
    colors[:, 3] = prim_dots['colorA']

    for i in range(len(colors)):
        color = (colors[i] * 255).astype("uint8").tolist()
        sub_mesh.vertexColors.append(color)

    return sub_mesh


# TODO: currently breaks original mesh. please fix
def triangulate_object(obj):
    me = obj.data
    # Get a BMesh representation
    bm = bmesh.new()
    bm.from_mesh(me)

    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    # V2.79 : bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method=0, ngon_method=0)

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(me)
    bm.free()
