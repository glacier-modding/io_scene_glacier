import os
import sys

class MjbaReader:
	def __init__(self, br):
		self.mjba_header = MjbaHeader(br)
		self.variable_fps = VariableFps(br)
		self.unknown_float_data = UnknownFloatData(br)
		self.mrtr_bone_map = MrtrBoneMap(br)
		self.animation = Animation(br)

class MjbaHeader:
	def __init__(self, br):
		self.mrtr_index = br.readInt64()
		self.atmd_index = br.readInt64()
		self.mjba_transform_matrix = br.readFloatVec(12)

class VariableFps:
	def __init__(self, br):
		self.header_size = br.readUInt64()
		self.frame_count = br.readUInt()
		self.mjba_fps = br.readUInt()
		self.fps = br.readFloatVec(self.frame_count)
		br.seekBy(8)

class UnknownFloatData:
	def __init__(self, br):
		self.first_size = br.readUInt()
		self.second_size = br.readUInt()
		size = self.first_size * self.second_size * 12
		self.float_data = br.readFloatVec(size)

class MrtrBoneMap:
	def __init__(self, br):
		self.fps = br.readUInt()
		br.seekBy(4)
		bone_header_offset = br.tell()
		self.mrtr_bone_count = br.readUInt()
		self.used_bone_count = br.readUInt()
		self.mrtr_bone_offset = br.readUInt64()
		self.used_bone_offset = br.readUInt64()
		self.mrtr_bone_indices = br.readShortVec(self.mrtr_bone_count)
		br.seekBy(self.used_bone_offset - self.mrtr_bone_offset - self.mrtr_bone_count * 2)
		self.used_bone_indices = br.readShortVec(self.used_bone_count)
		br.seekBy(0x80 - (self.used_bone_offset + self.used_bone_count * 2) % 0x80)
		br.seekBy(0x50) # this brings you to the start of the 'essential' animation header, these bytes are the same across all MJBAs

class Animation:
	def __init__(self, br):
		self.duration = br.readFloat()
		self.used_bone_count = br.readUShort()
		br.seekBy(0xA)
		self.frame_count_1 = br.readUInt()
		self.fps = br.readFloat()
		animation_data_size_offset = br.tell()
		self.animation_data_size = br.readUInt()
		br.seekBy(4)
		self.frame_count_1 = br.readUInt()
		self.static_quaternion_bone_count = br.readUShort()
		self.static_transform_bone_count = br.readUShort()
		self.transform_scale = br.readFloatVec(3)
		self.has_bind_poses = br.readUByte()
		br.seekBy(3)
		if self.used_bone_count <= 0x40:
			self.bones_with_static_quaternions = br.readUBytesToBitBoolArray(8)
			self.bones_with_static_transforms = br.readUBytesToBitBoolArray(8)
			if self.has_bind_poses:
				self.bones_with_static_bind_poses = br.readUBytesToBitBoolArray(8)
		if self.used_bone_count > 0x40:
			self.bones_with_static_quaternions = br.readUBytesToBitBoolArray(16)
			self.bones_with_static_transforms = br.readUBytesToBitBoolArray(16)
			if self.has_bind_poses:
				self.bones_with_static_bind_poses = br.readUBytesToBitBoolArray(16)
				br.seekBy(8)
		self.static_bone_quaternions = br.readUShortToFloatVec(self.static_quaternion_bone_count * 4)
		self.dynamic_bone_quaternions = br.readUShortToFloatVec((self.used_bone_count - self.static_quaternion_bone_count) * 4 * self.frame_count_1)
		if self.has_bind_poses:
			self.bone_bind_poses_quaternions = br.readUShortToFloatVec(self.bones_with_static_bind_poses["count"] * 8)
		self.static_bone_transforms = br.readUShortToFloatVec(self.static_transform_bone_count * 4)
		self.dynamic_bone_transforms = br.readUShortToFloatVec((self.used_bone_count - self.static_transform_bone_count) * 4 * self.frame_count_1)
		if self.has_bind_poses:
			self.bone_bind_poses_transforms = br.readUShortToFloatVec(self.bones_with_static_bind_poses["count"] * 8)
		br.seekBy(self.animation_data_size - (br.tell() - animation_data_size_offset))
		if self.animation_data_size > 0:
			self.world_transforms = br.readFloatVec(self.frame_count_1 * 8)