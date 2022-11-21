from enum import IntEnum
import sys
import abc


class PrimObjectSubtype(IntEnum):
    Standard = 0
    Linked = 1
    Weighted = 2
    Standarduv2 = 3
    Standarduv3 = 4
    Standarduv4 = 5


class PrimType(IntEnum):
    unknown = 0
    ObjectHeader = 1
    Mesh = 2
    Decal = 3
    Sprites = 4
    Shape = 5
    Unused = 6


class PrimMeshClothId:
    def __init__(self, value):
        self.bitfield = value

    def isSmoll(self):  # thank PawRep for this amazing name :)
        return self.bitfield & 0x80 == 0x80

    def write(self, br):
        br.writeUInt(self.bitfield)


class PrimObjectHeaderPropertyFlags:
    def __init__(self, val):
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
        return ("Object Header property flags:\n" +
                "\thas bones:\t\t" + str(self.hasBones()) + "\n" +
                "\thas frames:\t\t" + str(self.hasFrames()) + "\n" +
                "\tis linked object:\t" + str(self.isLinkedObject()) + "\n" +
                "\tis weighted object:\t" + str(self.isWeightedObject()) + "\n" +
                "\tuse bounds:\t\t" + str(self.useBounds()) + "\n" +
                "\thas high resolution:\t" + str(self.hasHighResolution()) + "\n")


class PrimObjectPropertyFlags:
    def __init__(self, value):
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

    def setHighResulution(self):
        if not self.isHighResolution():
            self.bitfield = self.bitfield + 8

    def write(self, br):
        br.writeUByte(self.bitfield)

    def toString(self):
        return ("Object property flags:\n" +
                "\tX axis locked:\t\t" + str(self.isXaxisLocked()) + "\n" +
                "\tY axis locked:\t\t" + str(self.isYaxisLocked()) + "\n" +
                "\tZ axis locked:\t\t" + str(self.isZaxisLocked()) + "\n" +
                "\tis high resolution:\t" + str(self.isHighResolution()) + "\n" +
                "\thas ps3 edge:\t\t" + str(self.hasPs3Edge()) + "\n" +
                "\tuses color1:\t\t" + str(self.useColor1()) + "\n" +
                "\thas no physics props:\t" + str(self.hasNoPhysicsProp()) + "\n")


class BoxColiEntry:
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
    def __init__(self):
        self.tri_per_chunk = 0x20
        self.box_entries = []

    def read(self, br):
        num_chunks = br.readUShort()
        self.tri_per_chunk = br.readUShort()
        self.box_entries = [-1] * num_chunks
        for entry in range(num_chunks):
            self.box_entries[entry] = BoxColiEntry()
            self.box_entries[entry].read(br)

    def write(self, br):
        br.writeUShort(len(self.box_entries))
        br.writeUShort(self.tri_per_chunk)
        for entry in self.box_entries:
            entry.write(br)
        br.align(4)


class Vertex:
    def __init__(self):
        self.position = [0] * 4
        self.weight = [[0] * 4 for i in range(2)] 
        self.joint = [[0] * 4 for i in range(2)] 
        self.normal = [1] * 4
        self.tangent = [1] * 4
        self.bitangent = [1] * 4
        self.uv = [[0] * 2]
        self.color = [0xFF] * 4


class VertexBuffer:
    def __init__(self):
        self.vertices = []

    def read(self, br, num_vertices, num_uvchannels, mesh, sub_mesh_color1, sub_mesh_flags, flags):
        self.vertices = [0] * num_vertices

        for vert in range(num_vertices):
            self.vertices[vert] = Vertex()

        for vert in range(num_vertices):
            if (mesh.prim_object.properties.isHighResolution()):
                self.vertices[vert].position[0] = (br.readFloat() * mesh.pos_scale[0]) + mesh.pos_bias[0]
                self.vertices[vert].position[1] = (br.readFloat() * mesh.pos_scale[1]) + mesh.pos_bias[1]
                self.vertices[vert].position[2] = (br.readFloat() * mesh.pos_scale[2]) + mesh.pos_bias[2]
                self.vertices[vert].position[3] = float(1.0)
            else:
                self.vertices[vert].position = br.readShortQuantizedVec(4, mesh.pos_scale, mesh.pos_bias)

        if (flags.isWeightedObject()):
            for vert in range(num_vertices):
                self.vertices[vert].weight[0][0] = br.readUByte() / 255
                self.vertices[vert].weight[0][1] = br.readUByte() / 255
                self.vertices[vert].weight[0][2] = br.readUByte() / 255
                self.vertices[vert].weight[0][3] = br.readUByte() / 255

                self.vertices[vert].joint[0][0] = br.readUByte()
                self.vertices[vert].joint[0][1] = br.readUByte()
                self.vertices[vert].joint[0][2] = br.readUByte()
                self.vertices[vert].joint[0][3] = br.readUByte()

                self.vertices[vert].weight[1][0] = br.readUByte() / 255
                self.vertices[vert].weight[1][1] = br.readUByte() / 255
                self.vertices[vert].weight[1][2] = 0
                self.vertices[vert].weight[1][3] = 0

                self.vertices[vert].joint[1][0] = br.readUByte()
                self.vertices[vert].joint[1][1] = br.readUByte()
                self.vertices[vert].joint[1][2] = 0
                self.vertices[vert].joint[1][3] = 0

        for vert in range(num_vertices):
            self.vertices[vert].normal = br.readUByteQuantizedVec(4)
            self.vertices[vert].tangent = br.readUByteQuantizedVec(4)
            self.vertices[vert].bitangent = br.readUByteQuantizedVec(4)
            self.vertices[vert].uv = [0] * num_uvchannels
            for uv in range(num_uvchannels):
                self.vertices[vert].uv[uv] = br.readShortQuantizedVec(2, mesh.tex_scale_bias[0:2],
                                                                      mesh.tex_scale_bias[2:4])

        if (not mesh.prim_object.properties.useColor1() or flags.isWeightedObject()):
            if (not sub_mesh_flags.useColor1()):
                for vert in range(num_vertices):
                    self.vertices[vert].color = br.readUByteVec(4)
            else:
                for vert in range(num_vertices):
                    self.vertices[vert].color[0] = sub_mesh_color1[0]
                    self.vertices[vert].color[1] = sub_mesh_color1[1]
                    self.vertices[vert].color[2] = sub_mesh_color1[2]
                    self.vertices[vert].color[3] = sub_mesh_color1[3]

    def write(self, br, mesh, sub_mesh_flags, flags):

        num_vertices = len(self.vertices)
        if num_vertices > 0:
            num_uvchannels = len(self.vertices[0].uv)
        else:
            num_uvchannels = 0
        # positions
        for vert in range(num_vertices):
            if (mesh.prim_object.properties.isHighResolution()):
                br.writeFloat((self.vertices[vert].position[0] - mesh.pos_bias[0]) / mesh.pos_scale[0])
                br.writeFloat((self.vertices[vert].position[1] - mesh.pos_bias[1]) / mesh.pos_scale[1])
                br.writeFloat((self.vertices[vert].position[2] - mesh.pos_bias[2]) / mesh.pos_scale[2])
            else:
                br.writeShortQuantizedVec(self.vertices[vert].position, mesh.pos_scale, mesh.pos_bias)

        # joints and weights
        if (flags.isWeightedObject()):
            for vert in range(num_vertices):
                br.writeUByte(br.IOI_round(self.vertices[vert].weight[0][0]))
                br.writeUByte(br.IOI_round(self.vertices[vert].weight[0][1]))
                br.writeUByte(br.IOI_round(self.vertices[vert].weight[0][2]))
                br.writeUByte(br.IOI_round(self.vertices[vert].weight[0][3]))

                br.writeUByte(self.vertices[vert].joint[0][0])
                br.writeUByte(self.vertices[vert].joint[0][1])
                br.writeUByte(self.vertices[vert].joint[0][2])
                br.writeUByte(self.vertices[vert].joint[0][3])

                br.writeUByte(br.IOI_round(self.vertices[vert].weight[1][0]))
                br.writeUByte(br.IOI_round(self.vertices[vert].weight[1][1]))
                br.writeUByte(self.vertices[vert].joint[1][0])
                br.writeUByte(self.vertices[vert].joint[1][1])

        # ntb + uv
        for vert in range(num_vertices):
            br.writeUByteQuantizedVec(self.vertices[vert].normal)
            br.writeUByteQuantizedVec(self.vertices[vert].tangent)
            br.writeUByteQuantizedVec(self.vertices[vert].bitangent)
            for uv in range(num_uvchannels):
                br.writeShortQuantizedVec(self.vertices[vert].uv[uv], mesh.tex_scale_bias[0:2],
                                          mesh.tex_scale_bias[2:4])

        # color
        if (not mesh.prim_object.properties.useColor1() or flags.isWeightedObject()):
            if (not sub_mesh_flags.useColor1() or flags.isWeightedObject()):
                for vert in range(num_vertices):
                    br.writeUByteVec(self.vertices[vert].color)


class PrimSubMesh:
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

    def read(self, br, mesh, flags):
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
        self.vertexBuffer.read(br, num_vertices, num_uvchannels, mesh, self.prim_object.color1,
                               self.prim_object.properties, flags)

        # detour for indices
        br.seek(indices_offset)
        self.indices = [-1] * (num_indices + num_additional_indices)
        for index in range(num_indices + num_additional_indices):
            self.indices[index] = br.readUShort()

        # detour for collision info
        br.seek(collision_offset)
        self.collision.read(br)

        # optional detour for cloth data
        if (cloth_offset != 0 and self.cloth != -1):
            br.seek(cloth_offset)
            self.cloth.read(br, mesh, self)
        else:
            self.cloth = -1

    def write(self, br, mesh, flags):
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

        if (self.cloth != -1):
            cloth_offset = br.tell()
            self.cloth.write(br, mesh)
            br.align(16)
        else:
            cloth_offset = 0

        header_offset = br.tell()
        # IOI uses a cleared primMesh object. so let's clear it here as well
        self.prim_object.lodmask = 0x0
        self.prim_object.color1 = [0, 0, 0, 0]
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
        br.writeUInt(0)  # additional indices kept at 0, because we do not know their purpose
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
        br.writeUInt(0)  # padd
        br.writeUInt64(0)  # padd
        return obj_table_offset

    def calc_bb(self):
        bb = [0.0] * 6
        max = [sys.float_info.min] * 3
        min = [sys.float_info.max] * 3
        for vert in self.vertexBuffer.vertices:
            for axis in range(3):
                if max[axis] < vert.position[axis]:
                    max[axis] = vert.position[axis]

                if min[axis] > vert.position[axis]:
                    min[axis] = vert.position[axis]

        bb = [min, max]
        return bb

    def calc_UVbb(self):

        max = [sys.float_info.min] * 3
        min = [sys.float_info.max] * 3
        layer = 0
        for vert in self.vertexBuffer.vertices:
            for axis in range(2):
                if max[axis] < vert.uv[layer][axis]:
                    max[axis] = vert.uv[layer][axis]

                if min[axis] > vert.uv[layer][axis]:
                    min[axis] = vert.uv[layer][axis]
        uvBB = [min, max]
        return uvBB

    def num_uvchannels(self):
        if self.num_vertices() > 0:
            return len(self.vertexBuffer.vertices[0].uv)
        else:
            return 0


class PrimObject:
    def __init__(self, type):
        self.prims = Prims(type)
        self.sub_type = PrimObjectSubtype(0)
        self.properties = PrimObjectPropertyFlags(0)
        self.lodmask = 0xFF
        self.variant_id = 0
        self.zbias = 0
        self.zoffset = 0
        self.material_id = 0
        self.wire_color = 0xFFFFFFFF
        self.color1 = [
                          0xFF] * 4  # global color used when useColor1 is set. will only work when defined inside PrimSubMesh
        self.min = [0] * 3
        self.max = [0] * 3

    def read(self, br):
        self.prims.read(br)
        self.sub_type = PrimObjectSubtype(br.readUByte())
        self.properties = PrimObjectPropertyFlags(br.readUByte())
        self.lodmask = br.readUByte()
        self.variant_id = br.readUByte()
        self.zbias = br.readUByte()  # draws mesh in front of others
        self.zoffset = br.readUByte()  # will move the mesh towards the camera depending on the distance to it
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
        self.total_size = 0  # TODO: get shortest value here
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

        self.accel_entries = [0] * num_accel_entries
        for i in range(num_accel_entries):
            self.accel_entries[i] = BoneAccel()
            self.accel_entries[i].read(br)

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
        br.seek(br.tell() - 4)  # aligns the data to match the offset defined in the BonAccel entries
        for i in range(num_indices):
            self.bone_indices[i] = br.readUShort()

    def write(self, br):
        for index in self.bone_indices:
            br.writeUShort(index)

        br.align(16)


# needs additional research
class ClothData:
    def __init__(self):
        self.size = 0
        self.cloth_data = [0] * self.size

    def read(self, br, mesh, sub_mesh):

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


class PrimMesh:
    def __init__(self):
        self.prim_object = PrimObject(2)
        self.pos_scale = [1] * 4
        self.pos_bias = [0] * 4
        self.tex_scale_bias = [1, 1, 0, 0]
        self.cloth_id = PrimMeshClothId(0)
        self.sub_mesh = PrimSubMesh()

    def read(self, br, flags):
        self.prim_object.read(br)

        # this will point to a table of submeshes, this is not really usefull since this table will always contain a single pointer
        # if the table were to contain multiple pointer we'd have no way of knowing since the table size is never defined.
        # to improve readability sub_mesh_table is not an array
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
        br.seek(old_offset)  # reset offset to end of header, this is required for WeightedPrimMesh

    def write(self, br, flags):
        self.update(flags)
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

    def update(self, flags):
        bb = self.sub_mesh.calc_bb()
        min = bb[0]
        max = bb[1]

        # set bounding box
        self.prim_object.min = min
        self.prim_object.max = max

        # set position scale
        self.pos_scale[0] = (max[0] - min[0]) * 0.5
        self.pos_scale[1] = (max[1] - min[1]) * 0.5
        self.pos_scale[2] = (max[2] - min[2]) * 0.5
        self.pos_scale[3] = 0.5

        # set position bias
        self.pos_bias[0] = (max[0] + min[0]) * 0.5
        self.pos_bias[1] = (max[1] + min[1]) * 0.5
        self.pos_bias[2] = (max[2] + min[2]) * 0.5
        self.pos_bias[3] = 1

        UVbb = self.sub_mesh.calc_UVbb()
        minUV = UVbb[0]
        maxUV = UVbb[1]

        # set UV scale
        self.tex_scale_bias[0] = (maxUV[0] - minUV[0]) * 0.5
        self.tex_scale_bias[1] = (maxUV[1] - minUV[1]) * 0.5

        # set UV bias
        self.tex_scale_bias[2] = (maxUV[0] + minUV[0]) * 0.5
        self.tex_scale_bias[3] = (maxUV[1] + minUV[1]) * 0.5

        if flags.isLinkedObject():
            self.pos_bias[3] = 0
            self.pos_scale[3] = 0x7FFF


class PrimMeshWeighted(PrimMesh):
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


# TODO: make pos scale and bias local only
class PrimHeader:
    def __init__(self, type):
        self.draw_destination = 0
        self.pack_type = 0
        self.type = PrimType(type)

    def read(self, br):
        self.draw_destination = br.readUByte()
        self.pack_type = br.readUByte()
        self.type = PrimType(br.readUShort())

    def write(self, br):
        br.writeUByte(self.draw_destination)
        br.writeUByte(self.pack_type)
        br.writeUShort(self.type)


class Prims:
    def __init__(self, type):
        self.prim_header = PrimHeader(type)

    def read(self, br):
        self.prim_header.read(br)

    def write(self, br):
        self.prim_header.write(br)


class PrimObjectHeader:
    def __init__(self):
        self.prims = Prims(1)
        self.property_flags = PrimObjectHeaderPropertyFlags(0)
        self.bone_rig_resource_index = 0xFFFFFFFF
        self.min = [sys.float_info.max] * 3
        self.max = [sys.float_info.min] * 3
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
            if (self.property_flags.isWeightedObject()):
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
                    self.append_bb(obj.prim_mesh.prim_object.min, obj.prim_mesh.prim_object.max)
                else:
                    self.append_bb(obj.prim_object.min, obj.prim_object.max)

        obj_table_offset = br.tell()
        for offset in obj_offsets:
            br.writeUInt(offset)

        br.align(16)

        header_offset = br.tell()
        self.prims.write(br)
        self.property_flags.write(br)
        br.writeUInt(self.bone_rig_resource_index)
        br.writeUInt(len(obj_offsets))
        br.writeUInt(obj_table_offset)

        br.writeFloatVec(self.min)
        br.writeFloatVec(self.max)

        if br.tell() % 8 != 0:
            br.writeUInt(0)
        return header_offset

    def append_bb(self, min, max):
        for axis in range(3):
            if min[axis] < self.min[axis]:
                self.min[axis] = min[axis]
            if max[axis] > self.max[axis]:
                self.max[axis] = max[axis]


class RenderPrimitve:
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

    def readHeader(self, br):
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
    def num_objects(self):
        num = 0
        for obj in self.header.object_table:
            if obj is not None:
                num = num + 1

        return num
