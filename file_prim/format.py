import enum
import sys

"""
The RenderPrimitive format:

RenderPrimitive ↴
    PrimObjectHeader
    Objects ↴
        PrimMesh ↴
            PrimObject
            PrimSubMesh ↴
                PrimObject
        ...
"""


class PrimObjectSubtype(enum.IntEnum):
    """
    Enum defining a subtype. All objects inside a prim have a subtype
    The StandarduvX types are not used within the H2016, H2 and H3 games,
    a probable cause for this is the introduction of a num_uvchannels variable.
    """

    Standard = 0
    Linked = 1
    Weighted = 2
    Standarduv2 = 3
    Standarduv3 = 4
    Standarduv4 = 5


class PrimType(enum.IntEnum):
    """
    A type property attached to all headers found within the prim format
    """

    Unknown = 0
    ObjectHeader = 1
    Mesh = 2
    Decal = 3
    Sprites = 4
    Shape = 5
    Unused = 6


class PrimMeshClothId:
    """Bitfield defining properties of the cloth data. Most bits are unknown."""

    def __init__(self, value):
        self.bitfield = value

    def isSmoll(self):  # thank PawRep for this amazing name :)
        return self.bitfield & 0x80 == 0x80

    def write(self, br):
        br.writeUInt(self.bitfield)


class PrimObjectHeaderPropertyFlags:
    """Global properties defined in the main header of a RenderPrimitive."""

    def __init__(self, val: int):
        self.bitfield = val

    def hasBones(self):
        return self.bitfield & 0b1 == 1

    def hasFrames(self):
        return self.bitfield & 0b10 == 2

    def isLinkedObject(self):
        return self.bitfield & 0b100 == 4

    def isWeightedObject(self):
        return self.bitfield & 0b1000 == 8

    def useBounds(self):
        return self.bitfield & 0b100000000 == 128

    def hasHighResolution(self):
        return self.bitfield & 0b1000000000 == 256

    def write(self, br):
        br.writeUInt(self.bitfield)

    def toString(self):
        return (
            "Object Header property flags:\n"
            + "\thas bones:\t\t"
            + str(self.hasBones())
            + "\n"
            + "\thas frames:\t\t"
            + str(self.hasFrames())
            + "\n"
            + "\tis linked object:\t"
            + str(self.isLinkedObject())
            + "\n"
            + "\tis weighted object:\t"
            + str(self.isWeightedObject())
            + "\n"
            + "\tuse bounds:\t\t"
            + str(self.useBounds())
            + "\n"
            + "\thas high resolution:\t"
            + str(self.hasHighResolution())
            + "\n"
        )


class PrimObjectPropertyFlags:
    """Mesh specific properties, used in Mesh and SubMesh."""

    def __init__(self, value: int):
        self.bitfield = value

    def isXaxisLocked(self):
        return self.bitfield & 0b1 == 1

    def isYaxisLocked(self):
        return self.bitfield & 0b10 == 2

    def isZaxisLocked(self):
        return self.bitfield & 0b100 == 4

    def isHighResolution(self):
        return self.bitfield & 0b1000 == 8

    def hasPs3Edge(self):
        return self.bitfield & 0b10000 == 16

    def useColor1(self):
        return self.bitfield & 0b100000 == 32

    def hasNoPhysicsProp(self):
        return self.bitfield & 0b1000000 == 64

    def setXaxisLocked(self):
        self.bitfield |= 0b1

    def setYaxisLocked(self):
        self.bitfield |= 0b10

    def setZaxisLocked(self):
        self.bitfield |= 0b100

    def setHighResolution(self):
        self.bitfield |= 0b1000

    def setColor1(self):
        self.bitfield |= 0b100000

    def setNoPhysics(self):
        self.bitfield |= 0b1000000

    def write(self, br):
        br.writeUByte(self.bitfield)

    def toString(self):
        return (
            "Object property flags:\n"
            + "\tX axis locked:\t\t"
            + str(self.isXaxisLocked())
            + "\n"
            + "\tY axis locked:\t\t"
            + str(self.isYaxisLocked())
            + "\n"
            + "\tZ axis locked:\t\t"
            + str(self.isZaxisLocked())
            + "\n"
            + "\tis high resolution:\t"
            + str(self.isHighResolution())
            + "\n"
            + "\thas ps3 edge:\t\t"
            + str(self.hasPs3Edge())
            + "\n"
            + "\tuses color1:\t\t"
            + str(self.useColor1())
            + "\n"
            + "\thas no physics props:\t"
            + str(self.hasNoPhysicsProp())
            + "\n"
        )


class BoxColiEntry:
    """Helper class for BoxColi, defines an entry to store BoxColi"""

    def __init__(self):
        self.min = [0] * 3
        self.max = [0] * 3

    def read(self, br):
        self.min = br.readUByteVec(3)
        self.max = br.readUByteVec(3)

    def write(self, br):
        br.writeUByteVec(self.min)
        br.writeUByteVec(self.max)


class BoxColi:
    """Used to store and array of BoxColi. Used for bullet collision"""

    def __init__(self):
        self.tri_per_chunk = 0x20
        self.box_entries = []

    def read(self, br):
        num_chunks = br.readUShort()
        self.tri_per_chunk = br.readUShort()
        self.box_entries = [-1] * num_chunks
        self.box_entries = [BoxColiEntry() for _ in range(num_chunks)]
        for box_entry in self.box_entries:
            box_entry.read(br)

    def write(self, br):
        br.writeUShort(len(self.box_entries))
        br.writeUShort(self.tri_per_chunk)
        for entry in self.box_entries:
            entry.write(br)
        br.align(4)


class Vertex:
    """A vertex with all field found inside a RenderPrimitive file"""

    def __init__(self):
        self.position = [0] * 4
        self.weight = [[0] * 4 for _ in range(2)]
        self.joint = [[0] * 4 for _ in range(2)]
        self.normal = [1] * 4
        self.tangent = [1] * 4
        self.bitangent = [1] * 4
        self.uv = [[0] * 2]
        self.color = [0xFF] * 4


class PrimMesh:
    """A subMesh wrapper class, used to store information about a mesh, as well as the mesh itself (called sub_mesh)"""

    def __init__(self):
        self.prim_object = PrimObject(2)
        self.pos_scale = [
            1.0
        ] * 4  # TODO: Remove this, should be calculated when exporting
        self.pos_bias = [0.0] * 4  # TODO: No need to keep these around
        self.tex_scale_bias = [1.0, 1.0, 0.0, 0.0]  # TODO: This can also go
        self.cloth_id = PrimMeshClothId(0)
        self.sub_mesh = PrimSubMesh()

    def read(self, br, flags):
        self.prim_object.read(br)

        # this will point to a table of submeshes, this is not really usefull since this table will always contain a
        # single pointer if the table were to contain multiple pointer we'd have no way of knowing since the table
        # size is never defined. to improve readability sub_mesh_table is not an array
        sub_mesh_table_offset = br.readUInt()

        self.pos_scale = br.readFloatVec(4)
        self.pos_bias = br.readFloatVec(4)
        self.tex_scale_bias = br.readFloatVec(4)

        self.cloth_id = PrimMeshClothId(br.readUInt())

        old_offset = br.tell()
        br.seek(sub_mesh_table_offset)
        sub_mesh_offset = br.readUInt()
        br.seek(sub_mesh_offset)
        self.sub_mesh.read(br, self, flags)
        br.seek(
            old_offset
        )  # reset offset to end of header, this is required for WeightedPrimMesh

    def write(self, br, flags):
        self.update()

        sub_mesh_offset = self.sub_mesh.write(br, self, flags)

        header_offset = br.tell()

        self.prim_object.write(br)

        br.writeUInt(sub_mesh_offset)

        br.writeFloatVec(self.pos_scale)
        br.writeFloatVec(self.pos_bias)
        br.writeFloatVec(self.tex_scale_bias)

        self.cloth_id.write(br)

        br.align(16)

        return header_offset

    def update(self):
        bb = self.sub_mesh.calc_bb()
        bb_min = bb[0]
        bb_max = bb[1]

        # set bounding box
        self.prim_object.min = bb_min
        self.prim_object.max = bb_max

        # set position scale
        self.pos_scale[0] = (bb_max[0] - bb_min[0]) * 0.5
        self.pos_scale[1] = (bb_max[1] - bb_min[1]) * 0.5
        self.pos_scale[2] = (bb_max[2] - bb_min[2]) * 0.5
        self.pos_scale[3] = 0.5
        for i in range(3):
            self.pos_scale[i] = 0.5 if self.pos_scale[i] <= 0.0 else self.pos_scale[i]

        # set position bias
        self.pos_bias[0] = (bb_max[0] + bb_min[0]) * 0.5
        self.pos_bias[1] = (bb_max[1] + bb_min[1]) * 0.5
        self.pos_bias[2] = (bb_max[2] + bb_min[2]) * 0.5
        self.pos_bias[3] = 1

        bb_uv = self.sub_mesh.calc_UVbb()
        bb_uv_min = bb_uv[0]
        bb_uv_max = bb_uv[1]

        # set UV scale
        self.tex_scale_bias[0] = (bb_uv_max[0] - bb_uv_min[0]) * 0.5
        self.tex_scale_bias[1] = (bb_uv_max[1] - bb_uv_min[1]) * 0.5
        for i in range(2):
            self.tex_scale_bias[i] = (
                0.5 if self.tex_scale_bias[i] <= 0.0 else self.tex_scale_bias[i]
            )

        # set UV bias
        self.tex_scale_bias[2] = (bb_uv_max[0] + bb_uv_min[0]) * 0.5
        self.tex_scale_bias[3] = (bb_uv_max[1] + bb_uv_min[1]) * 0.5


class PrimMeshWeighted(PrimMesh):
    """A different variant of PrimMesh. In addition to PrimMesh it also stores bone data"""

    def __init__(self):
        super().__init__()
        self.prim_mesh = PrimMesh()
        self.num_copy_bones = 0
        self.copy_bones = 0
        self.bone_indices = BoneIndices()
        self.bone_info = BoneInfo()

    def read(self, br, flags):
        super().read(br, flags)
        self.num_copy_bones = br.readUInt()
        copy_bones_offset = br.readUInt()

        bone_indices_offset = br.readUInt()
        bone_info_offset = br.readUInt()

        br.seek(copy_bones_offset)
        self.copy_bones = 0  # empty, because unknown

        br.seek(bone_indices_offset)
        self.bone_indices.read(br)

        br.seek(bone_info_offset)
        self.bone_info.read(br)

    def write(self, br, flags):
        sub_mesh_offset = self.sub_mesh.write(br, self.prim_mesh, flags)

        bone_info_offset = br.tell()
        self.bone_info.write(br)

        bone_indices_offset = br.tell()
        self.bone_indices.write(br)

        header_offset = br.tell()

        bb = self.sub_mesh.calc_bb()

        # set bounding box
        self.prim_object.min = bb[0]
        self.prim_object.max = bb[1]

        self.update()
        self.prim_object.write(br)

        br.writeUInt(sub_mesh_offset)

        br.writeFloatVec(self.pos_scale)
        br.writeFloatVec(self.pos_bias)
        br.writeFloatVec(self.tex_scale_bias)

        self.cloth_id.write(br)

        br.writeUInt(self.num_copy_bones)
        br.writeUInt(0)  # copy_bones offset PLACEHOLDER

        br.writeUInt(bone_indices_offset)
        br.writeUInt(bone_info_offset)

        br.align(16)
        return header_offset


class VertexBuffer:
    """A helper class used to store and manage the vertices found inside a PrimSubMesh"""

    def __init__(self):
        self.vertices = []

    def read(
        self,
        br,
        num_vertices: int,
        num_uvchannels: int,
        mesh: PrimMesh,
        sub_mesh_color1: [],
        sub_mesh_flags: PrimObjectPropertyFlags,
        flags: PrimObjectHeaderPropertyFlags,
    ):
        self.vertices = [Vertex() for _ in range(num_vertices)]

        for vertex in self.vertices:
            if mesh.prim_object.properties.isHighResolution():
                vertex.position[0] = (
                    br.readFloat() * mesh.pos_scale[0]
                ) + mesh.pos_bias[0]
                vertex.position[1] = (
                    br.readFloat() * mesh.pos_scale[1]
                ) + mesh.pos_bias[1]
                vertex.position[2] = (
                    br.readFloat() * mesh.pos_scale[2]
                ) + mesh.pos_bias[2]
                vertex.position[3] = 1
            else:
                vertex.position = br.readShortQuantizedVecScaledBiased(
                    4, mesh.pos_scale, mesh.pos_bias
                )

        if flags.isWeightedObject():
            for vertex in self.vertices:
                vertex.weight[0][0] = br.readUByte() / 255
                vertex.weight[0][1] = br.readUByte() / 255
                vertex.weight[0][2] = br.readUByte() / 255
                vertex.weight[0][3] = br.readUByte() / 255

                vertex.joint[0][0] = br.readUByte()
                vertex.joint[0][1] = br.readUByte()
                vertex.joint[0][2] = br.readUByte()
                vertex.joint[0][3] = br.readUByte()

                vertex.weight[1][0] = br.readUByte() / 255
                vertex.weight[1][1] = br.readUByte() / 255
                vertex.weight[1][2] = 0
                vertex.weight[1][3] = 0

                vertex.joint[1][0] = br.readUByte()
                vertex.joint[1][1] = br.readUByte()
                vertex.joint[1][2] = 0
                vertex.joint[1][3] = 0

        for vertex in self.vertices:
            vertex.normal = br.readUByteQuantizedVec(4)
            vertex.tangent = br.readUByteQuantizedVec(4)
            vertex.bitangent = br.readUByteQuantizedVec(4)
            vertex.uv = [0] * num_uvchannels
            for uv in range(num_uvchannels):
                vertex.uv[uv] = br.readShortQuantizedVecScaledBiased(
                    2, mesh.tex_scale_bias[0:2], mesh.tex_scale_bias[2:4]
                )

        if not mesh.prim_object.properties.useColor1() or flags.isWeightedObject():
            if not sub_mesh_flags.useColor1():
                for vertex in self.vertices:
                    vertex.color = br.readUByteVec(4)
            else:
                for vertex in self.vertices:
                    vertex.color[0] = sub_mesh_color1[0]
                    vertex.color[1] = sub_mesh_color1[1]
                    vertex.color[2] = sub_mesh_color1[2]
                    vertex.color[3] = sub_mesh_color1[3]

    def write(
        self,
        br,
        mesh,
        sub_mesh_flags: PrimObjectPropertyFlags,
        flags: PrimObjectHeaderPropertyFlags,
    ):
        if len(self.vertices) > 0:
            num_uvchannels = len(self.vertices[0].uv)
        else:
            num_uvchannels = 0
        # positions
        for vertex in self.vertices:
            if mesh.prim_object.properties.isHighResolution():
                br.writeFloat(
                    (vertex.position[0] - mesh.pos_bias[0]) / mesh.pos_scale[0]
                )
                br.writeFloat(
                    (vertex.position[1] - mesh.pos_bias[1]) / mesh.pos_scale[1]
                )
                br.writeFloat(
                    (vertex.position[2] - mesh.pos_bias[2]) / mesh.pos_scale[2]
                )
            else:
                br.writeShortQuantizedVecScaledBiased(
                    vertex.position, mesh.pos_scale, mesh.pos_bias
                )

        # joints and weights
        if flags.isWeightedObject():
            for vertex in self.vertices:
                br.writeUByte(br.IOI_round(vertex.weight[0][0]))
                br.writeUByte(br.IOI_round(vertex.weight[0][1]))
                br.writeUByte(br.IOI_round(vertex.weight[0][2]))
                br.writeUByte(br.IOI_round(vertex.weight[0][3]))

                br.writeUByte(vertex.joint[0][0])
                br.writeUByte(vertex.joint[0][1])
                br.writeUByte(vertex.joint[0][2])
                br.writeUByte(vertex.joint[0][3])

                br.writeUByte(br.IOI_round(vertex.weight[1][0]))
                br.writeUByte(br.IOI_round(vertex.weight[1][1]))
                br.writeUByte(vertex.joint[1][0])
                br.writeUByte(vertex.joint[1][1])

        # ntb + uv
        for vertex in self.vertices:
            br.writeUByteQuantizedVec(vertex.normal)
            br.writeUByteQuantizedVec(vertex.tangent)
            br.writeUByteQuantizedVec(vertex.bitangent)
            for uv in range(num_uvchannels):
                br.writeShortQuantizedVecScaledBiased(
                    vertex.uv[uv], mesh.tex_scale_bias[0:2], mesh.tex_scale_bias[2:4]
                )

        # color
        if not mesh.prim_object.properties.useColor1() or flags.isWeightedObject():
            if not sub_mesh_flags.useColor1() or flags.isWeightedObject():
                for vertex in self.vertices:
                    br.writeUByteVec(vertex.color)


class PrimSubMesh:
    """Stores the mesh data. as well as the BoxColi and ClothData"""

    def __init__(self):
        self.prim_object = PrimObject(0)
        self.num_vertices = 0
        self.num_indices = 0
        self.num_additional_indices = 0
        self.num_uvchannels = 1
        self.dummy1 = bytes([0, 0, 0])
        self.vertexBuffer = VertexBuffer()
        self.indices = [0] * 0
        self.collision = BoxColi()
        self.cloth = -1

    def read(self, br, mesh: PrimMesh, flags: PrimObjectHeaderPropertyFlags):
        self.prim_object.read(br)

        num_vertices = br.readUInt()
        vertices_offset = br.readUInt()
        num_indices = br.readUInt()
        num_additional_indices = br.readUInt()
        indices_offset = br.readUInt()
        collision_offset = br.readUInt()
        cloth_offset = br.readUInt()
        num_uvchannels = br.readUInt()

        # detour for vertices
        br.seek(vertices_offset)
        self.vertexBuffer.read(
            br,
            num_vertices,
            num_uvchannels,
            mesh,
            self.prim_object.color1,
            self.prim_object.properties,
            flags,
        )

        # detour for indices
        br.seek(indices_offset)
        self.indices = [-1] * (num_indices + num_additional_indices)
        for index in range(num_indices + num_additional_indices):
            self.indices[index] = br.readUShort()

        # detour for collision info
        br.seek(collision_offset)
        self.collision.read(br)

        # optional detour for cloth data,
        # !locked because the format is not known enough!
        if cloth_offset != 0 and self.cloth != -1:
            br.seek(cloth_offset)
            self.cloth.read(br, mesh, self)
        else:
            self.cloth = -1

    def write(self, br, mesh, flags: PrimObjectHeaderPropertyFlags):
        index_offset = br.tell()
        for index in self.indices:
            br.writeUShort(index)

        br.align(16)
        vert_offset = br.tell()
        self.vertexBuffer.write(br, mesh, self.prim_object.properties, flags)

        br.align(16)
        coll_offset = br.tell()
        self.collision.write(br)

        br.align(16)

        if self.cloth != -1:
            cloth_offset = br.tell()
            self.cloth.write(br, mesh)
            br.align(16)
        else:
            cloth_offset = 0

        header_offset = br.tell()
        # IOI uses a cleared primMesh object. so let's clear it here as well
        self.prim_object.lodmask = 0x0
        self.prim_object.wire_color = 0x0

        # TODO: optimze this away
        bb = self.calc_bb()
        self.prim_object.min = bb[0]
        self.prim_object.max = bb[1]
        self.prim_object.write(br)

        num_vertices = len(self.vertexBuffer.vertices)
        br.writeUInt(num_vertices)
        br.writeUInt(vert_offset)
        br.writeUInt(len(self.indices))
        br.writeUInt(
            0
        )  # additional indices kept at 0, because we do not know their purpose
        br.writeUInt(index_offset)
        br.writeUInt(coll_offset)
        br.writeUInt(cloth_offset)

        if num_vertices > 0:
            num_uvchannels = len(self.vertexBuffer.vertices[0].uv)
        else:
            num_uvchannels = 0

        br.writeUInt(num_uvchannels)

        br.align(16)

        obj_table_offset = br.tell()
        br.writeUInt(header_offset)
        br.writeUInt(0)  # padding
        br.writeUInt64(0)  # padding
        return obj_table_offset

    def calc_bb(self):
        bb_max = [-sys.float_info.max] * 3
        bb_min = [sys.float_info.max] * 3
        for vert in self.vertexBuffer.vertices:
            for axis in range(3):
                if bb_max[axis] < vert.position[axis]:
                    bb_max[axis] = vert.position[axis]

                if bb_min[axis] > vert.position[axis]:
                    bb_min[axis] = vert.position[axis]
        return [bb_min, bb_max]

    def calc_UVbb(self):
        bb_max = [-sys.float_info.max] * 3
        bb_min = [sys.float_info.max] * 3
        layer = 0
        for vert in self.vertexBuffer.vertices:
            for axis in range(2):
                if bb_max[axis] < vert.uv[layer][axis]:
                    bb_max[axis] = vert.uv[layer][axis]

                if bb_min[axis] > vert.uv[layer][axis]:
                    bb_min[axis] = vert.uv[layer][axis]
        return [bb_min, bb_max]


class PrimObject:
    """A header class used to store information about PrimMesh and PrimSubMesh"""

    def __init__(self, type_preset: int):
        self.prims = Prims(type_preset)
        self.sub_type = PrimObjectSubtype(0)
        self.properties = PrimObjectPropertyFlags(0)
        self.lodmask = 0xFF
        self.variant_id = 0
        self.zbias = 0
        self.zoffset = 0
        self.material_id = 0
        self.wire_color = 0xFFFFFFFF
        self.color1 = [
            0xFF
        ] * 4  # global color used when useColor1 is set. only works inside PrimSubMesh
        self.min = [0] * 3
        self.max = [0] * 3

    def read(self, br):
        self.prims.read(br)
        self.sub_type = PrimObjectSubtype(br.readUByte())
        self.properties = PrimObjectPropertyFlags(br.readUByte())
        self.lodmask = br.readUByte()
        self.variant_id = br.readUByte()
        self.zbias = br.readUByte()  # draws mesh in front of others
        self.zoffset = (
            br.readUByte()
        )  # will move the mesh towards the camera depending on the distance to it
        self.material_id = br.readUShort()
        self.wire_color = br.readUInt()

        # global color used when useColor1 is set. will only work when defined inside PrimSubMesh
        self.color1 = br.readUByteVec(4)

        self.min = br.readFloatVec(3)
        self.max = br.readFloatVec(3)

    def write(self, br):
        self.prims.write(br)
        br.writeUByte(self.sub_type)
        self.properties.write(br)
        br.writeUByte(self.lodmask)
        br.writeUByte(self.variant_id)
        br.writeUByte(self.zbias)
        br.writeUByte(self.zoffset)
        br.writeUShort(self.material_id)
        br.writeUInt(self.wire_color)
        br.writeUByteVec(self.color1)

        br.writeFloatVec(self.min)
        br.writeFloatVec(self.max)


class BoneAccel:
    def __init__(self):
        self.offset = 0
        self.num_indices = 0

    def read(self, br):
        self.offset = br.readUInt()
        self.num_indices = br.readUInt()

    def write(self, br):
        br.writeUInt(self.offset)
        br.writeUInt(self.num_indices)


class BoneInfo:
    def __init__(self):
        self.total_size = 0
        self.bone_remap = [0xFF] * 255
        self.pad = 0
        self.accel_entries = []

    def read(self, br):
        self.total_size = br.readUShort()
        num_accel_entries = br.readUShort()
        self.bone_remap = [0] * 255
        for i in range(255):
            self.bone_remap[i] = br.readUByte()
        self.pad = br.readUByte()

        self.accel_entries = [BoneAccel() for _ in range(num_accel_entries)]
        for accel_entry in self.accel_entries:
            accel_entry.read(br)

    def write(self, br):
        br.writeUShort(self.total_size)
        br.writeUShort(len(self.accel_entries))
        for i in range(255):
            br.writeUByte(self.bone_remap[i])
        br.writeUByte(self.pad)

        for entry in self.accel_entries:
            entry.write(br)

        br.align(16)


class BoneIndices:
    def __init__(self):
        self.bone_indices = []

    def read(self, br):
        num_indices = br.readUInt()
        self.bone_indices = [0] * num_indices
        br.seek(
            br.tell() - 4
        )  # aligns the data to match the offset defined in the BonAccel entries
        for i in range(num_indices):
            self.bone_indices[i] = br.readUShort()

    def write(self, br):
        for index in self.bone_indices:
            br.writeUShort(index)

        br.align(16)


# needs additional research
class ClothData:
    """Class to store data about cloth"""

    def __init__(self):
        self.size = 0
        self.cloth_data = [0] * self.size

    def read(self, br, mesh: PrimMesh, sub_mesh: PrimSubMesh):
        if mesh.cloth_id.isSmoll():
            self.size = br.readUInt()
        else:
            self.size = 0x14 * sub_mesh.num_vertices
        self.cloth_data = [0] * self.size
        for i in range(self.size):
            self.cloth_data[i] = br.readUByte()

    def write(self, br, mesh):
        if mesh.cloth_id.isSmoll():
            br.writeUInt(len(self.cloth_data))
        for b in self.cloth_data:
            br.writeUByte(b)


class PrimHeader:
    """Small header class used by other header classes"""

    def __init__(self, type_preset):
        self.draw_destination = 0
        self.pack_type = 0
        self.type = PrimType(type_preset)

    def read(self, br):
        self.draw_destination = br.readUByte()
        self.pack_type = br.readUByte()
        self.type = PrimType(br.readUShort())

    def write(self, br):
        br.writeUByte(self.draw_destination)
        br.writeUByte(self.pack_type)
        br.writeUShort(self.type)


class Prims:
    """
    Wrapper class for PrimHeader.
    I'm not quite sure why it exists, but here it is :)
    """

    def __init__(self, type_preset: int):
        self.prim_header = PrimHeader(type_preset)

    def read(self, br):
        self.prim_header.read(br)

    def write(self, br):
        self.prim_header.write(br)


class PrimObjectHeader:
    """Global RenderPrimitive header. used by all objects defined"""

    def __init__(self):
        self.prims = Prims(1)
        self.property_flags = PrimObjectHeaderPropertyFlags(0)
        self.bone_rig_resource_index = 0xFFFFFFFF
        self.min = [sys.float_info.max] * 3
        self.max = [-sys.float_info.max] * 3
        self.object_table = []

    def read(self, br):
        self.prims.read(br)
        self.property_flags = PrimObjectHeaderPropertyFlags(br.readUInt())
        self.bone_rig_resource_index = br.readUInt()
        num_objects = br.readUInt()
        object_table_offset = br.readUInt()

        self.min = br.readFloatVec(3)
        self.max = br.readFloatVec(3)

        br.seek(object_table_offset)
        object_table_offsets = [-1] * num_objects
        for obj in range(num_objects):
            object_table_offsets[obj] = br.readInt()

        self.object_table = [-1] * num_objects
        for obj in range(num_objects):
            br.seek(object_table_offsets[obj])
            if self.property_flags.isWeightedObject():
                self.object_table[obj] = PrimMeshWeighted()
                self.object_table[obj].read(br, self.property_flags)
            else:
                self.object_table[obj] = PrimMesh()
                self.object_table[obj].read(br, self.property_flags)

    def write(self, br):
        obj_offsets = []
        for obj in self.object_table:
            if obj is not None:
                obj_offsets.append(obj.write(br, self.property_flags))

                if self.property_flags.isWeightedObject():
                    self.append_bb(
                        obj.prim_mesh.prim_object.min, obj.prim_mesh.prim_object.max
                    )
                else:
                    self.append_bb(obj.prim_object.min, obj.prim_object.max)

        obj_table_offset = br.tell()
        for offset in obj_offsets:
            br.writeUInt(offset)

        br.align(16)

        header_offset = br.tell()
        self.prims.write(br)
        self.property_flags.write(br)

        if self.bone_rig_resource_index < 0:
            br.writeUInt(0xFFFFFFFF)
        else:
            br.writeUInt(self.bone_rig_resource_index)

        br.writeUInt(len(obj_offsets))
        br.writeUInt(obj_table_offset)

        br.writeFloatVec(self.min)
        br.writeFloatVec(self.max)

        if br.tell() % 8 != 0:
            br.writeUInt(0)
        return header_offset

    def append_bb(self, bb_min: [], bb_max: []):
        for axis in range(3):
            if bb_min[axis] < self.min[axis]:
                self.min[axis] = bb_min[axis]
            if bb_max[axis] > self.max[axis]:
                self.max[axis] = bb_max[axis]


def readHeader(br):
    """ "Global function to read only the header of a RenderPrimitive, used to fast file identification"""
    offset = br.readUInt()
    br.seek(offset)
    header_values = PrimObjectHeader()
    header_values.prims.read(br)
    header_values.property_flags = PrimObjectHeaderPropertyFlags(br.readUInt())
    header_values.bone_rig_resource_index = br.readUInt()
    br.readUInt()
    br.readUInt()
    header_values.min = br.readFloatVec(3)
    header_values.max = br.readFloatVec(3)
    return header_values


class RenderPrimitive:
    """
    RenderPrimitive class, represents the .prim file format.
    It contains a multitude of meshes and properties.
    The RenderPrimitive format has built-in support for: armatures, bounding boxes, collision and cloth physics.
    """

    def __init__(self):
        self.header = PrimObjectHeader()

    def read(self, br):
        offset = br.readUInt()
        br.seek(offset)
        self.header.read(br)

    def write(self, br):
        br.writeUInt64(420)  # PLACEHOLDER
        br.writeUInt64(0)  # padding
        header_offset = self.header.write(br)
        br.seek(0)
        br.writeUInt64(header_offset)

    def num_objects(self):
        num = 0
        for obj in self.header.object_table:
            if obj is not None:
                num = num + 1

        return num
