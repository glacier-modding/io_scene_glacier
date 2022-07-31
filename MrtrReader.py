import os
import sys
		
class MrtrReader:
	def __init__(self, br):
		self.mrtr_header = MrtrHeader(br)
		self.bone_map = BoneMap(br)
		br.seek(self.mrtr_header.positions_offset)
		self.positions = BonePositions(br, self.bone_map.bone_count)
		br.seek(self.mrtr_header.quaternions_offset)
		self.quaternions = BoneQuaternions(br, self.bone_map.bone_count)
		br.seek(self.mrtr_header.names_offset)
		self.bone_names = BoneNames(br)

class MrtrHeader:
	def __init__(self, br):
		br.seek(0x20)
		self.names_offset = br.readUInt64()
		self.quaternions_offset = br.readUInt64()
		self.positions_offset = br.readUInt64()

class BoneMap:
	def __init__(self, br):
		br.seek(0x80)
		self.bone_count = br.readUInt()
		br.seekBy(0xC)
		self.bone_parents = br.readIntVec(self.bone_count)

class BonePositions:
	def __init__(self, br, bone_count):
		self.bone_positions = []
		for i in range(bone_count):
			self.bone_positions.append(br.readFloatVec(3))
			br.seekBy(4)

class BoneQuaternions:
	def __init__(self, br, bone_count):
		self.bone_quaternions = []
		for i in range(bone_count):
			self.bone_quaternions.append(br.readFloatVec(4))

class BoneNames:
	def __init__(self, br):
		names_offset = br.tell()
		names_count = br.readUInt()
		br.seekBy(0x14)
		names_index_size = br.readUInt()
		br.seekBy(4)
		strings_offset = names_offset + names_index_size
		names_indices = br.readUIntVec(names_count)
		names_string_offsets = br.readUIntVec(names_count)
		self.bones = []
		for i in range(names_count):
			self.bones.append(br.readString())