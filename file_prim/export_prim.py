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
from . import io_binary

def __get_positions(mesh, matrix):

    #read the vertex locations
    locs = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    source = mesh.vertices
    for vert in source:
        vert.co = matrix @ vert.co

    source.foreach_get('co', locs)
    locs = locs.reshape(len(mesh.vertices), 3)

    return locs


def __get_normals(mesh):
    """Get normal for each loop."""
    normals = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.calc_normals_split()
    mesh.loops.foreach_get('normal', normals)

    normals = normals.reshape(len(mesh.loops), 3)

    for ns in normals:
        for axis in range(3):
            if int(round(ns[axis])) != 0:
                ns[axis] = round(ns[axis])
            else:
                ns[axis] = ns[axis] + (1/255)

    return normals

def __get_tangents(mesh):
    """Get an array of the tangent for each loop."""
    tangents = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.loops.foreach_get('tangent', tangents)
    tangents = tangents.reshape(len(mesh.loops), 3)

    for ts in tangents:
        for axis in range(3):
            if int(round(ts[axis])) != 0:
                ts[axis] = round(ts[axis])
            else:
                ts[axis] = ts[axis] + (1/255)

    return tangents

def __get_bitangents(mesh):
    """Get an array of the tangent for each loop."""
    bitangents = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.loops.foreach_get('bitangent', bitangents)
    bitangents = bitangents.reshape(len(mesh.loops), 3)

    for bs in bitangents:
        for axis in range(3):
            if int(round(bs[axis])) != 0:
                bs[axis] = round(bs[axis])
            else:
                bs[axis] = bs[axis] + (1/255)

    return bitangents

def __get_uvs(mesh, uv_i):
    layer = mesh.uv_layers[uv_i]
    uvs = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    layer.data.foreach_get('uv', uvs)
    uvs = uvs.reshape(len(mesh.loops), 2)

    # u,v -> u,1-v
    uvs[:, 1] *= -1
    uvs[:, 1] += 1

    return uvs

def __get_colors(mesh, color_i):
    colors = np.empty(len(mesh.loops) * 4, dtype=np.float32)
    layer = mesh.vertex_colors[color_i]
    mesh.color_attributes[layer.name].data.foreach_get('color', colors)
    colors = colors.reshape(len(mesh.loops), 4)
    # colors are already linear, no need to switch color space
    return colors

def save_prim(operator, context, filepath):
    # Export the selected mesh
    scene = context.scene
    prim = format.RenderPrimitve()
    prim.header.object_table = []

    mesh_obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for ob in mesh_obs:
        prim_obj = format.PrimMesh()
        triangulate_object(ob)
        prim_obj.sub_mesh = save_prim_sub_mesh(ob)
        if len(prim_obj.sub_mesh.vertexBuffer.vertices) > 10000:
                prim_obj.prim_object.properties.setHighResulution()

        prim.header.object_table.append(prim_obj)

    exportFile = os.fsencode(filepath)
    if os.path.exists(exportFile):
        os.remove(exportFile)
    bre = io_binary.BinaryReader(open(exportFile, 'wb'))
    prim.write(bre)
    bre.close()

    return {'FINISHED'}

def save_prim_sub_mesh(blender_obj):
    mesh = blender_obj.to_mesh()
    prim_mesh = format.PrimSubMesh()

    mesh.calc_tangents(uvmap="UVMap")

    locs = __get_positions(mesh, blender_obj.matrix_world.copy())

    dot_fields = [('vertex_index', np.uint32)]
    dot_fields += [('nx', np.float32), ('ny', np.float32), ('nz', np.float32)]
    dot_fields += [('tx', np.float32), ('ty', np.float32), ('tz', np.float32), ('tw', np.float32)]
    dot_fields += [('bx', np.float32), ('by', np.float32), ('bz', np.float32), ('bw', np.float32)]
    for uv_i in range(len(mesh.uv_layers)):
        dot_fields += [('uv%dx' % uv_i, np.float32), ('uv%dy' % uv_i, np.float32)]
    dot_fields += [
        ('colorR', np.float32),
        ('colorG', np.float32),
        ('colorB', np.float32),
        ('colorA', np.float32),
    ]

    dots = np.empty(len(mesh.loops), dtype=np.dtype(dot_fields))

    vidxs = np.empty(len(mesh.loops))
    mesh.loops.foreach_get('vertex_index', vidxs)
    dots['vertex_index'] = vidxs
    del vidxs

    normals = __get_normals(mesh)
    dots['nx'] = normals[:, 0]
    dots['ny'] = normals[:, 1]
    dots['nz'] = normals[:, 2]
    del normals

    tangents = __get_tangents(mesh)
    dots['tx'] = tangents[:, 0]
    dots['ty'] = tangents[:, 1]
    dots['tz'] = tangents[:, 2]
    del tangents

    bitangents = __get_bitangents(mesh)
    dots['bx'] = bitangents[:, 0]
    dots['by'] = bitangents[:, 1]
    dots['bz'] = bitangents[:, 2]
    del bitangents

    for uv_i in range(len(mesh.uv_layers)):
        uvs = __get_uvs(mesh, uv_i)
        dots['uv%dx' % uv_i] = uvs[:, 0]
        dots['uv%dy' % uv_i] = uvs[:, 1]
        del uvs

    if len(mesh.vertex_colors) > 0:
        colors = __get_colors(mesh, 0)
        dots['colorR'] = colors[:, 0]
        dots['colorG'] = colors[:, 1]
        dots['colorB'] = colors[:, 2]
        dots['colorA'] = colors[:, 3]
        del colors
    else:
        #TODO: look into converting this to color1
        colors = np.full(len(mesh.loops) * 4, 0xFF, dtype=np.float32)
        colors = colors.reshape(len(mesh.loops), 4)
        dots['colorR'] = colors[:, 0]
        dots['colorG'] = colors[:, 1]
        dots['colorB'] = colors[:, 2]
        dots['colorA'] = colors[:, 3]

    # Calculate triangles and sort them into primitives.
    mesh.calc_loop_triangles()
    loop_indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.uint32)
    mesh.loop_triangles.foreach_get('loops', loop_indices)

    prim_mesh.indices = loop_indices.tolist()
    prim_mesh.vertexBuffer.vertices = [0] * len(np.unique(loop_indices))


    prim_dots = dots[loop_indices]

    blender_idxs = prim_dots['vertex_index']

    positions = np.empty((len(prim_dots), 4), dtype=np.float32)
    positions[:, 0] = locs[blender_idxs, 0]
    positions[:, 1] = locs[blender_idxs, 1]
    positions[:, 2] = locs[blender_idxs, 2]
    positions[:, 3] = 1.0

    normals = np.empty((len(prim_dots), 4), dtype=np.float32)
    normals[:, 0] = prim_dots['nx']
    normals[:, 1] = prim_dots['ny']
    normals[:, 2] = prim_dots['nz']
    normals[:, 3] = 1/255

    tangents = np.empty((len(prim_dots), 4), dtype=np.float32)
    tangents[:, 0] = prim_dots['tx']
    tangents[:, 1] = prim_dots['ty']
    tangents[:, 2] = prim_dots['tz']
    tangents[:, 3] = 1/255

    bitangents = np.empty((len(prim_dots), 4), dtype=np.float32)
    bitangents[:, 0] = prim_dots['bx']
    bitangents[:, 1] = prim_dots['by']
    bitangents[:, 2] = prim_dots['bz']
    bitangents[:, 3] = 1/255

    uvs = np.empty((len(mesh.uv_layers), len(prim_dots), 2), dtype=np.float32)
    for tex_coord_i in range(len(mesh.uv_layers)):
        uvs[tex_coord_i, :, 0] = prim_dots['uv%dx' % tex_coord_i]
        uvs[tex_coord_i, :, 1] = prim_dots['uv%dy' % tex_coord_i]

    colors = np.empty((len(prim_dots), 4), dtype=np.float32)
    colors[:, 0] = prim_dots['colorR']
    colors[:, 1] = prim_dots['colorG']
    colors[:, 2] = prim_dots['colorB']
    colors[:, 3] = prim_dots['colorA']

    i = 0
    for vertex in prim_mesh.vertexBuffer.vertices:
        vertex = format.Vertex()
        vertex.position = positions[i]
        vertex.normal = normals[i]
        vertex.tangent = tangents[i]
        vertex.bitangent = bitangents[i]
        for tex_coord_i in range(len(mesh.uv_layers)):
            vertex.uv[tex_coord_i] = uvs[tex_coord_i, i]
        vertex.color = (colors[i] * 255).astype("uint8").tolist()
        prim_mesh.vertexBuffer.vertices[i] = vertex
        i = i + 1

    return prim_mesh

#TODO: currently breaks original mesh. please fix
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
