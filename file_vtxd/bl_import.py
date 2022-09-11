import os
import bpy
import math
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


def load_vtxd(operator, context, filepath):
    fp = os.fsencode(filepath)
    file = open(fp, "rb")
    br = io_binary.BinaryReader(file)
    meshes = []

    vtxd_name = bpy.path.display_name_from_filepath(filepath)
    print("Start reading: " + str(vtxd_name) + "\n")

    vtxd = format.VertexData()
    vtxd.read(br)

    for meshIndex in range(vtxd.num_submeshes()):
        meshes.append(load_vtxd_submesh(vtxd, vtxd_name, meshIndex))

    return meshes


def load_vtxd_submesh(vtxd, vtxd_name, meshIndex):
    mesh = bpy.data.meshes.new(name=(str(vtxd_name) + "_" + str(meshIndex)))

    vert_locs = []
    loop_cols = []
    loop_vidxs = []

    sub_mesh = vtxd.sub_meshes[meshIndex]

    # create a plane
    height = int(math.sqrt(int(sub_mesh.num_vertices())))
    width = int(math.sqrt(int(sub_mesh.num_vertices())))

    verts = []
    fac = []
    for indY in range(height):
        for indX in range(width):
            verts.append([indX * 0.01, indY * 0.01, 0])

    for indY in range(height - 1):
        for indX in range(width - 1):
            target_ind = (indY * width) + indX
            fac.append([target_ind, target_ind + 1, target_ind + width])
            fac.append([target_ind + 1, target_ind + width, (target_ind + width) + 1])

    mesh.from_pydata(verts, [], fac)

    # add colors to the plane
    for face in fac:
        for idx in face:
            col = sub_mesh.vertexColors[idx]
            loop_cols.extend([col[0] / 255, col[1] / 255, col[2] / 255, col[3] / 255])

    layer = mesh.vertex_colors.new(name='Col')
    mesh.color_attributes[layer.name].data.foreach_set('color', loop_cols)

    mesh.validate()
    mesh.update()

    return mesh
