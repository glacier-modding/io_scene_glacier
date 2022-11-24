from enum import IntEnum
import sys


class BoneDefinition:
    def __init__(self):
        self.center = [0] * 3
        self.prev_bone_nr = -1
        self.size = [0] * 3
        self.name = [0] * 34
        self.body_part = -1

    def read(self, br):
        self.center = br.readFloatVec(3)
        self.prev_bone_nr = br.readInt()
        self.size = br.readFloatVec(3)
        self.name = br.readString(34)
        self.body_part = br.readShort()

    def write(self, br):
        br.writeFloatVec(self.center)
        br.writeInt(self.prev_bone_nr)
        br.writeFloatVec(self.size)
        br.writeString(self.name, 34)
        br.writeShort(self.body_part)


class SVQ:
    def __init__(self):
        self.rotation = [0] * 4
        self.position = [0] * 4

    def read(self, br):
        self.rotation = br.readFloatVec(4)
        self.position = br.readFloatVec(4)

    def write(self, br):
        br.writeFloatVec(self.rotation)
        br.writeFloatVec(self.position)


class Matrix43:
    def __init__(self):
        self.m = [[0] * 3] * 4

    def read(self, br):
        for row_idx in range(len(self.m)):
            self.m[row_idx] = br.readFloatVec(3)

    def write(self, br):
        for row_idx in range(len(self.m)):
            br.writeFloatVec(self.m[row_idx])


class BoneConstrainType(IntEnum):
    LOOKAT = 1
    ROTATION = 2


class BoneConstraints:
    def __init__(self):
        self.bone_constraints = []

    def read(self, br):
        nr_constraints = br.readUInt()

        for constr in range(nr_constraints):
            self.bone_constraints.append(BoneConstraintLookat())
            self.bone_constraints[constr].read(br)

    def write(self, br):
        br.writeUInt(len(self.bone_constraints))
        for constr in self.bone_constraints:
            constr.write(br)

    def nr_constraints(self):
        return len(self.bone_constraints)


class BoneConstraint:
    def __init__(self):
        self.type  # ubyte
        self.bone_index  # ubyte


class BoneConstraintLookat(BoneConstraint):
    def __init__(self):
        super(BoneConstraint, self).__init__()
        self.look_at_axis = 0
        self.up_bone_alignment_axis = 0
        self.look_at_flip = 0
        self.up_flip = 0
        self.upnode_control = 0
        self.up_node_parent_idx = 0
        self.target_parent_idx = [0] * 2
        self.bone_targets_weights = [0] * 2
        self.target_pos = [[0] * 3] * 2
        self.up_pos = [0] * 3

    def read(self, br):
        self.type = BoneConstrainType(br.readUByte())
        self.bone_index = br.readUByte()
        nr_targets = br.readUByte()
        self.look_at_axis = br.readUByte()
        self.up_bone_alignment_axis = br.readUByte()
        self.look_at_flip = br.readUByte()
        self.up_flip = br.readUByte()
        self.upnode_control = br.readUByte()
        self.up_node_parent_idx = br.readUByte()
        self.target_parent_idx = br.readUByteVec(2)
        br.readUByte()  # alignment
        self.bone_targets_weights = br.readFloatVec(2)
        self.target_pos[0] = br.readFloatVec(3)
        self.target_pos[1] = br.readFloatVec(3)
        self.up_pos = br.readFloatVec(3)

        self.target_parent_idx = self.target_parent_idx[:nr_targets]
        self.bone_targets_weights = self.bone_targets_weights[:nr_targets]
        self.target_pos = self.target_pos[:nr_targets]
        self.target_pos = self.target_pos[:nr_targets]

    def write(self, br):
        br.writeUByte(self.type)
        br.writeUByte(self.bone_index)
        br.writeUByte(len(self.target_parent_idx))
        br.writeUByte(self.look_at_axis)
        br.writeUByte(self.up_bone_alignment_axis)
        br.writeUByte(self.look_at_flip)
        br.writeUByte(self.up_flip)
        br.writeUByte(self.upnode_control)
        br.writeUByte(self.up_node_parent_idx)

        while len(self.target_parent_idx) < 2:
            self.target_parent_idx.append(0)

        while len(self.bone_targets_weights) < 2:
            self.bone_targets_weights.append(0)

        while len(self.target_pos) < 2:
            self.target_pos.append([0, 0, 0])

        br.writeUByteVec(self.target_parent_idx)
        br.writeUByte(0)
        br.writeFloatVec(self.bone_targets_weights)
        for pos in self.target_pos:
            br.writeFloatVec(pos)
        br.writeFloatVec(self.up_pos)


# This is a different BoneConstraint type, it's likely an unused leftover from long ago.
# Since no evidence of it being used in recent BORG files has been found it will remain unused here for now
class BoneConstraintRotate(BoneConstraint):
    def __init__(self):
        super(BoneConstraint, self).__init__()
        self.reference_bone_idx
        self.twist_weight

    def read(self, br):
        print("Tried to read a BoneConstraintRotate, that's not supposed to happen")
        self.type = BoneConstrainType(br.readUByte())
        self.bone_index = br.readUByte()
        self.reference_bone_idx = br.readUByte()
        br.readUByte()
        self.twist_weight = br.readFloat()

    def write(self, br):
        print("Tried to write a BoneConstraintRotate, that's not supposed to happen")
        br.writeUByte(self.type)
        br.writeUByte(self.bone_index)
        br.writeUByte(self.reference_bone_idx)
        br.writeUByte(0)
        br.writeFloat(self.twist_weight)


class PoseBoneHeader:
    def __init__(self):
        self.pose_bone_array_offset = 0  # Size=0x4
        self.pose_bone_index_array_offset = 0  # Size=0x4
        self.pose_bone_count_total = 0  # Size=0x4
        self.pose_entry_index_array_offset = 0  # Size=0x4
        self.pose_bone_count_array_offset = 0  # Size=0x4
        self.pose_count = 0  # Size=0x4
        self.names_list_offset = 0  # Size=0x4
        self.names_entry_index_array_offset = 0  # Size=0x4
        self.face_bone_index_array_offset = 0  # Size=0x4
        self.face_bone_count = 0  # Size=0x4

    def read(self, br):
        self.pose_bone_array_offset = br.readUInt()
        self.pose_bone_index_array_offset = br.readUInt()
        self.pose_bone_count_total = br.readUInt()

        self.pose_entry_index_array_offset = br.readUInt()
        self.pose_bone_count_array_offset = br.readUInt()
        self.pose_count = br.readUInt()

        self.names_list_offset = br.readUInt()
        self.names_entry_index_array_offset = br.readUInt()

        self.face_bone_index_array_offset = br.readUInt()
        self.face_bone_count = br.readUInt()

    def write(self, br):
        header_base = br.tell()

        if self.pose_bone_array_offset == header_base:
            self.pose_bone_array_offset = 0

        if self.pose_bone_index_array_offset == header_base:
            self.pose_bone_index_array_offset = 0

        if self.pose_entry_index_array_offset == header_base:
            self.pose_entry_index_array_offset = 0

        if self.pose_bone_count_array_offset == header_base:
            self.pose_bone_count_array_offset = 0

        if self.names_list_offset == header_base:
            self.names_list_offset = 0

        if self.names_entry_index_array_offset == header_base:
            self.names_entry_index_array_offset = 0

        if self.face_bone_index_array_offset == header_base:
            self.face_bone_index_array_offset = 0

        br.writeUInt(self.pose_bone_array_offset)
        br.writeUInt(self.pose_bone_index_array_offset)
        br.writeUInt(self.pose_bone_count_total)
        br.writeUInt(self.pose_entry_index_array_offset)
        br.writeUInt(self.pose_bone_count_array_offset)
        br.writeUInt(self.pose_count)
        br.writeUInt(self.names_list_offset)
        br.writeUInt(self.names_entry_index_array_offset)
        br.writeUInt(self.face_bone_index_array_offset)
        br.writeUInt(self.face_bone_count)


class Pose:
    def __init__(self):
        self.pose_bone = PoseBone()
        self.pose_bone_index = -1


class PoseBone:
    def __init__(self):
        self.quat = [0] * 4
        self.pos = [0] * 4
        self.scale = [0] * 4

    def read(self, br):
        self.quat = br.readFloatVec(4)
        self.pos = br.readFloatVec(4)
        self.scale = br.readFloatVec(4)

    def write(self, br):
        br.writeFloatVec(self.quat)
        br.writeFloatVec(self.pos)
        br.writeFloatVec(self.scale)


class BoneRig:
    def __init__(self):
        self.bone_definitions = []
        self.bind_poses = []
        self.inv_global_mats = []
        self.pose_bones = []
        self.pose_bone_indices = []
        self.pose_entry_index = []
        self.pose_bone_count_array = []
        self.names_list = []
        self.face_bone_indices = []
        self.bone_constraints = []

    def read(self, br):
        br.seek(br.readUInt64())

        number_of_bones = br.readUInt()
        number_of_animated_bones = br.readUInt()
        bone_definitions_offset = br.readUInt()
        bind_pose_offset = br.readUInt()
        bind_pose_inv_global_mats_offset = br.readUInt()
        bone_constraints_header_offset = br.readUInt()
        pose_bone_header_offset = br.readUInt()

        # invert_global_bones and bone_map are both unused (0) pointers likely leftover from an old version of the BoneRig
        invert_global_bones_offset = br.readUInt()
        bone_map_offset = br.readUInt64()

        # reading data from the offsets
        br.seek(bone_definitions_offset)
        for bone_idx in range(number_of_bones):
            self.bone_definitions.append(BoneDefinition())
            self.bone_definitions[bone_idx].read(br)

        br.seek(bind_pose_offset)
        for bind_pose_idx in range(number_of_bones):
            self.bind_poses.append(SVQ())
            self.bind_poses[bind_pose_idx].read(br)

        br.seek(bind_pose_inv_global_mats_offset)
        for mat_idx in range(number_of_bones):
            self.inv_global_mats.append(Matrix43())
            self.inv_global_mats[mat_idx].read(br)

        br.seek(bone_constraints_header_offset)
        self.bone_constraints = BoneConstraints()
        self.bone_constraints.read(br)

        # read the pose_bone
        br.seek(pose_bone_header_offset)
        pose_bone_header = PoseBoneHeader()
        pose_bone_header.read(br)

        br.seek(pose_bone_header.pose_bone_array_offset)
        for pose_bone in range(pose_bone_header.pose_bone_count_total):
            self.pose_bones.append(PoseBone())
            self.pose_bones[pose_bone].read(br)

        br.seek(pose_bone_header.pose_bone_index_array_offset)
        self.pose_bone_indices = br.readUIntVec(pose_bone_header.pose_bone_count_total)

        br.seek(pose_bone_header.pose_entry_index_array_offset)
        self.pose_entry_index = br.readUIntVec(pose_bone_header.pose_count)

        br.seek(pose_bone_header.pose_bone_count_array_offset)
        self.pose_bone_count_array = br.readUIntVec(pose_bone_header.pose_count)

        # read names
        names_entry_index_array = []
        br.seek(pose_bone_header.names_entry_index_array_offset)
        for entry_idx in range(pose_bone_header.pose_count):
            names_entry_index_array.append(br.readUInt())

        for name_idx in range(pose_bone_header.pose_count):
            br.seek(pose_bone_header.names_list_offset + names_entry_index_array[name_idx])
            self.names_list.append(br.readCString())

        # read face bone indices
        br.seek(pose_bone_header.face_bone_index_array_offset)
        self.face_bone_indices = br.readUIntVec(pose_bone_header.face_bone_count)

    def write(self, br):
        br.writeUInt64(420)  # PLACEHOLDER
        br.writeUInt64(0)  # padding

        pose_bone_header = PoseBoneHeader()
        pose_bone_header.pose_bone_array_offset = br.tell()
        for pose_bone in self.pose_bones:
            pose_bone.write(br)

        pose_bone_header.pose_bone_index_array_offset = br.tell()
        br.writeUIntVec(self.pose_bone_indices)
        br.align(16)

        pose_bone_header.pose_entry_index_array_offset = br.tell()
        br.writeUIntVec(self.pose_entry_index)
        br.align(16)

        pose_bone_header.pose_bone_count_array_offset = br.tell()
        br.writeUIntVec(self.pose_bone_count_array)
        br.align(16)

        pose_bone_header.names_list_offset = br.tell()
        for name in self.names_list:
            br.writeCString(name)
        br.align(16)

        pose_bone_header.names_entry_index_array_offset = br.tell()
        name_offset = 0
        for name in self.names_list:
            br.writeUInt(name_offset)
            name_offset = name_offset + len(name) + 1
        br.align(16)

        pose_bone_header.face_bone_index_array_offset = br.tell()
        br.writeUIntVec(self.face_bone_indices)
        br.align(16)

        pose_bone_header.pose_bone_count_total = len(self.pose_bones)
        pose_bone_header.pose_count = len(self.pose_entry_index)
        pose_bone_header.face_bone_count = len(self.face_bone_indices)

        pose_bone_header_offset = br.tell()
        pose_bone_header.write(br)
        br.align(16)

        bone_definitions_offset = br.tell()
        for bone in self.bone_definitions:
            bone.write(br)
        br.align(16)

        bind_pose_offset = br.tell()
        for pose in self.bind_poses:
            pose.write(br)
        br.align(16)

        bind_pose_inv_global_mats_offset = br.tell()
        for mat in self.inv_global_mats:
            mat.write(br)
        br.align(16)

        bone_constraints_header_offset = br.tell()
        self.bone_constraints.write(br)
        br.align(16)

        header_offset = br.tell()
        br.writeUInt(len(self.bone_definitions))  # number_of_bones
        br.writeUInt(len(self.bone_definitions) - self.bone_constraints.nr_constraints())  # number_of_animated_bones
        br.writeUInt(bone_definitions_offset)
        br.writeUInt(bind_pose_offset)
        br.writeUInt(bind_pose_inv_global_mats_offset)
        br.writeUInt(bone_constraints_header_offset)
        br.writeUInt(pose_bone_header_offset)
        br.writeUInt(0)  # invert_global_bones_offset
        br.writeUInt64(0)  # bone_map_offset
        br.align(16)

        br.seek(0)
        br.writeUInt64(header_offset)
