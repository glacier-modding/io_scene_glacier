import os
from . import format
from .. import io_binary


def is_weighted(filepath):
    fp = os.fsencode(filepath)
    file = open(fp, "rb")
    br = io_binary.BinaryReader(file)

    prim = format.RenderPrimitve()
    return prim.readHeader(br).bone_rig_resource_index != 0xFFFFFFFF
