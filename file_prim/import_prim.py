import os
import bpy
import mathutils
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

def load_prim(operator, context, filepath):
    fp = os.fsencode(filepath)
    file = open(fp, "rb")
    br = io_binary.BinaryReader(file)
    meshes = []

    prim_name = bpy.path.display_name_from_filepath(filepath)
    print("Start reading: "+ str(prim_name) + "\n")

    prim = format.RenderPrimitve()
    prim.read(br)

    for meshIndex in range(prim.num_objects()):
        if(prim.header.property_flags.isWeightedObject()):
            meshes.append(load_prim_mesh_weighted(prim, prim_name, meshIndex))
        else:
            meshes.append(load_prim_mesh(prim, prim_name, meshIndex))

            #temp coli testing
            load_prim_coli(prim, prim_name, meshIndex)
    return meshes

def load_prim_coli(prim, prim_name, meshIndex):
    for boxColi in prim.header.object_table[meshIndex].sub_mesh.collision.box_entries:
        x, y, z = boxColi.min
        x1, y1, z1 = boxColi.max

        bbMin = prim.header.object_table[meshIndex].prim_object.min
        bbMax = prim.header.object_table[meshIndex].prim_object.max

        #print("BoxColi: " + str(boxColi.min))
        #print("x: " + str(x / 255))
        #print("y: " + str(y / 255))
        #print("z: " + str(z / 255))

        x = (x / 255) * bbMax[0]
        y = (y / 255) * bbMax[1]
        z = (z / 255) * bbMax[2]

        x1 = (x1 / 255) * bbMax[0]
        y1 = (y1 / 255) * bbMax[1]
        z1 = (z1 / 255) * bbMax[2]

        boxX =   (x1 + x)/2
        boxY =   (y1 + y)/2
        boxZ =   (z1 + z)/2

        scaleX = (x1 - x) /2
        scaleY = (y1 - y) /2
        scaleZ = (z1 - z) /2


        mesh = bpy.ops.mesh.primitive_cube_add(scale = (scaleX,scaleY,scaleZ), calc_uvs = True, align='WORLD', location=(boxX, boxY, boxZ))
        ob = bpy.context.object
        me = ob.data
        ob.name = (str(prim_name) + "_" + str(meshIndex) + "_Coli")
        me.name = 'CUBEMESH'

def load_prim_mesh(prim, prim_name, meshIndex):
    mesh = bpy.data.meshes.new(name=(str(prim_name) + "_" + str(meshIndex)))

    vert_locs = []
    vert_normals = []
    loop_vidxs = []
    loop_uvs = [[]]
    loop_cols = []

    sub_mesh = prim.header.object_table[meshIndex].sub_mesh

    loop_vidxs.extend(sub_mesh.indices)

    i = 0
    for vert in sub_mesh.vertexBuffer.vertices:
        vert_locs.extend([vert.position[0], vert.position[1], vert.position[2]])
        vert_normals.append([0.7, -0.5, 0.3]) #fixed value to see if normals are affected
        i = i +1

    for index in sub_mesh.indices:
        vert = sub_mesh.vertexBuffer.vertices[index]
        loop_cols.extend([vert.color[0]/255, vert.color[1]/255, vert.color[2]/255, vert.color[3]/255])
        for uv_i in range(sub_mesh.num_uvchannels):
            loop_uvs[uv_i].extend([vert.uv[uv_i][0], 1 - vert.uv[uv_i][1]])


    mesh.vertices.add(len(vert_locs) // 3)
    mesh.vertices.foreach_set('co', vert_locs)

    mesh.loops.add(len(loop_vidxs))
    mesh.loops.foreach_set('vertex_index', loop_vidxs)

    num_faces = len(sub_mesh.indices) // 3
    mesh.polygons.add(num_faces)

    loop_starts = np.arange(0, 3 * num_faces, step=3)
    loop_totals = np.full(num_faces, 3)
    mesh.polygons.foreach_set('loop_start', loop_starts)
    mesh.polygons.foreach_set('loop_total', loop_totals)

    print(sub_mesh.num_uvchannels)
    for uv_i in range(sub_mesh.num_uvchannels):
        name = 'UVMap' if uv_i == 0 else 'UVMap.%03d' % uv_i
        layer = mesh.uv_layers.new(name=name)
        layer.data.foreach_set('uv', loop_uvs[uv_i])

    layer = mesh.vertex_colors.new(name='Col')
    mesh.color_attributes[layer.name].data.foreach_set('color', loop_cols)

    mesh.validate()
    mesh.update()

#   this is not working yet :/
    mesh.create_normals_split()
    mesh.normals_split_custom_set_from_vertices(vert_normals)

    return mesh

def load_prim_mesh_weighted(prim, prim_name, meshIndex):
    mesh = bpy.data.meshes.new(name=(str(prim_name) + "_" + str(meshIndex)))

    vert_locs = []
    vert_normals = []
    loop_vidxs = []
    loop_uvs = [[]]
    loop_cols = []

    sub_mesh = prim.header.object_table[meshIndex].prim_mesh.sub_mesh

    loop_vidxs.extend(sub_mesh.indices)

    for vert in sub_mesh.vertexBuffer.vertices:
        vert_locs.extend([vert.position[0], vert.position[1], vert.position[2]])
        vert_normals.append([0.57735031, 0.57735031, 0.57735031]) #fixed value to see if normals are affected

    for index in sub_mesh.indices:
        vert = sub_mesh.vertexBuffer.vertices[index]
        loop_cols.extend([vert.color[0]/255, vert.color[1]/255, vert.color[2]/255, vert.color[3]/255])
        for uv_i in range(sub_mesh.num_uvchannels):
            loop_uvs[uv_i].extend([vert.uv[uv_i][0], 1 - vert.uv[uv_i][1]])


    mesh.vertices.add(len(vert_locs) // 3)
    mesh.vertices.foreach_set('co', vert_locs)

    mesh.loops.add(len(loop_vidxs))
    mesh.loops.foreach_set('vertex_index', loop_vidxs)

    num_faces = len(sub_mesh.indices) // 3
    mesh.polygons.add(num_faces)

    loop_starts = np.arange(0, 3 * num_faces, step=3)
    loop_totals = np.full(num_faces, 3)
    mesh.polygons.foreach_set('loop_start', loop_starts)
    mesh.polygons.foreach_set('loop_total', loop_totals)

    for uv_i in range(sub_mesh.num_uvchannels):
        name = 'UVMap' if uv_i == 0 else 'UVMap.%03d' % uv_i
        layer = mesh.uv_layers.new(name=name)
        layer.data.foreach_set('uv', loop_uvs[uv_i])

    layer = mesh.vertex_colors.new(name='Col')
    mesh.color_attributes[layer.name].data.foreach_set('color', loop_cols)

    mesh.validate()
    mesh.update()

#   this is not working yet :/
    mesh.create_normals_split()
    mesh.normals_split_custom_set_from_vertices(vert_normals)

    return mesh
