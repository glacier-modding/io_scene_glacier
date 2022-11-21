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

from . import format as prim_format
from ..file_borg import format as borg_format
from .. import io_binary


def load_prim(operator, context, collection, filepath, use_rig, rig_filepath):
    fp = os.fsencode(filepath)
    file = open(fp, "rb")
    br = io_binary.BinaryReader(file)
    prim = prim_format.RenderPrimitve()
    prim.read(br)
    br.close()

    collection.prim_collection_properties.is_weighted = prim.header.property_flags.isWeightedObject()
    collection.prim_collection_properties.is_linked = prim.header.property_flags.isLinkedObject()

    borg = None
    if use_rig:
        fp = os.fsencode(rig_filepath)
        file = open(fp, "rb")
        br = io_binary.BinaryReader(file)
        borg = borg_format.BoneRig()
        borg.read(br)

    prim_name = bpy.path.display_name_from_filepath(filepath)
    print("Start reading: " + str(prim_name) + "\n")

    meshes = []
    for meshIndex in range(prim.num_objects()):
        meshes.append(load_prim_mesh(prim, borg, prim_name, meshIndex))

        # coli testing
        # load_prim_coli(prim, prim_name, meshIndex)

    return meshes


def load_prim_coli(prim, prim_name, meshIndex):
    for boxColi in prim.header.object_table[meshIndex].sub_mesh.collision.box_entries:
        x, y, z = boxColi.min
        x1, y1, z1 = boxColi.max

        bbMin = prim.header.object_table[meshIndex].prim_object.min
        bbMax = prim.header.object_table[meshIndex].prim_object.max

        x = (x / 255) * bbMax[0]
        y = (y / 255) * bbMax[1]
        z = (z / 255) * bbMax[2]

        x1 = (x1 / 255) * bbMax[0]
        y1 = (y1 / 255) * bbMax[1]
        z1 = (z1 / 255) * bbMax[2]

        boxX = (x1 + x) / 2
        boxY = (y1 + y) / 2
        boxZ = (z1 + z) / 2

        scaleX = (x1 - x) / 2
        scaleY = (y1 - y) / 2
        scaleZ = (z1 - z) / 2

        mesh = bpy.ops.mesh.primitive_cube_add(scale=(scaleX, scaleY, scaleZ), calc_uvs=True, align='WORLD',
                                               location=(boxX, boxY, boxZ))
        ob = bpy.context.object
        me = ob.data
        ob.name = (str(prim_name) + "_" + str(meshIndex) + "_Coli")
        me.name = 'CUBEMESH'


def load_prim_mesh(prim, borg, prim_name, meshIndex):
    mesh = bpy.data.meshes.new(name=(str(prim_name) + "_" + str(meshIndex)))

    use_rig = False
    if borg is not None:
        use_rig = True

    vert_locs = []
    loop_vidxs = []
    loop_uvs = [[]]
    loop_cols = []

    num_joint_sets = 0

    if prim.header.property_flags.isWeightedObject() and use_rig:
        num_joint_sets = 2

    sub_mesh = prim.header.object_table[meshIndex].sub_mesh

    vert_joints = [[[0] * 4 for j in range(len(sub_mesh.vertexBuffer.vertices))] for i in range(num_joint_sets)]
    vert_weights = [[[0] * 4 for j in range(len(sub_mesh.vertexBuffer.vertices))] for i in range(num_joint_sets)]

    loop_vidxs.extend(sub_mesh.indices)

    i = 0
    for vert in sub_mesh.vertexBuffer.vertices:
        vert_locs.extend([vert.position[0], vert.position[1], vert.position[2]])

        for j in range(num_joint_sets):
            vert_joints[j][i] = (vert.joint[j])
            vert_weights[j][i] = (vert.weight[j])
        i = i + 1

    for index in sub_mesh.indices:
        vert = sub_mesh.vertexBuffer.vertices[index]
        loop_cols.extend([vert.color[0] / 255, vert.color[1] / 255, vert.color[2] / 255, vert.color[3] / 255])
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

    # Skinning
    ob = bpy.data.objects.new('temp_obj', mesh)
    if num_joint_sets and use_rig:

        for bone in borg.bone_definitions:
            ob.vertex_groups.new(name=bone.name.decode("utf-8"))

        vgs = list(ob.vertex_groups)

        for i in range(num_joint_sets):
            js = vert_joints[i]
            ws = vert_weights[i]
            for vi in range(len(vert_locs) // 3):
                w0, w1, w2, w3 = ws[vi]
                j0, j1, j2, j3 = js[vi]
                if w0 != 0: vgs[j0].add((vi,), w0, 'REPLACE')
                if w1 != 0: vgs[j1].add((vi,), w1, 'REPLACE')
                if w2 != 0: vgs[j2].add((vi,), w2, 'REPLACE')
                if w3 != 0: vgs[j3].add((vi,), w3, 'REPLACE')
    bpy.data.objects.remove(ob)

    layer = mesh.vertex_colors.new(name='Col')
    mesh.color_attributes[layer.name].data.foreach_set('color', loop_cols)

    mesh.validate()
    mesh.update()

    material_id = prim.header.object_table[meshIndex].prim_object.material_id
    mesh.prim_properties.material_id = material_id

    lod = prim.header.object_table[meshIndex].prim_object.lodmask
    mask = []
    for bit in range(8):
        mask.append(0 != (lod & (1 << bit)))
    mesh.prim_properties.lod = mask
    mesh.prim_properties.prim_type = str(prim.header.object_table[meshIndex].prim_object.prims.prim_header.type)
    mesh.prim_properties.prim_sub_type = str(prim.header.object_table[meshIndex].prim_object.sub_type)

    return mesh
