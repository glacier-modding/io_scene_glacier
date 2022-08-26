import os
import sys

class Mrtr:
	def __init__(self):
		self.blend_frame_orientation = [0, 0, 0, 1]
		self.trajectory_bone_index = 0
		self.character_root_bone_index = 0
		self.hierarchy = Hierarchy()
		self.bone_name_map = StringTable()
		self.positions = BonePositions()
		self.quaternions = BoneQuaternions()

	def read(self, br):
		self.blend_frame_orientation = br.readFloatVec(4)
		hierarchy_offset = br.readUInt64()
		self.trajectory_bone_index = br.readUInt()
		self.character_root_bone_index = br.readUInt()

		bone_name_map_offset = br.readUInt64()
		bone_quaternions_offset = br.readUInt64()
		bone_positions_offset = br.readUInt64()

		spu_memory_requirements = br.readUInt() #is always the same as the quats offset
		br.seekBy(0x4)

		global_id_to_rig_id_offset = br.readUInt64() #always 0
		global_id_to_rig_id_count = br.readUInt() #always 0
		br.seekBy(0x4)

		br.seek(hierarchy_offset)
		self.hierarchy.read(br)

		br.seek(bone_name_map_offset)
		self.bone_name_map.read(br)

		bone_count = len(self.hierarchy.bone_parents)

		br.seek(bone_positions_offset)
		self.positions.read(br, bone_count)

		br.seek(bone_quaternions_offset)
		self.quaternions.read(br, bone_count)

	def write(self, br):

		#write header as 0xCD, will be constructed later
		br.writeUByteVec([0xCD] * 0x40)

		br.writeUInt64(0) #global_id_to_rig_id_offset = 0
		br.writeUInt(0) #global_id_to_rig_id_count = 0
		br.align(8, 0xCD)

		br.writeUByteVec([0xCD] * 0x30)

		hierarchy_offset = br.tell()
		self.hierarchy.write(br)

		br.align(16, 0xCD)

		bone_positions_offset = br.tell()
		self.positions.write(br)

		bone_quaternions_offset = br.tell()
		self.quaternions.write(br)

		bone_name_map_offset = br.tell()
		self.bone_name_map.write(br)

		br.seek(0)
		br.writeFloatVec(self.blend_frame_orientation)
		br.writeUInt64(hierarchy_offset) #hierarchy_offset
		br.writeUInt(self.trajectory_bone_index)
		br.writeUInt(self.character_root_bone_index)

		br.writeUInt64(bone_name_map_offset) #bone_name_map_offset
		br.writeUInt64(bone_quaternions_offset) #bone_quaternions_offset
		br.writeUInt64(bone_positions_offset) #bone_positions_offset
		br.writeUInt(bone_name_map_offset) #spu_memory_requirements = bone_quaternions_offset

class Hierarchy:
	def __init__(self):
		self.bone_parents = []

	def read(self, br):
		num_entries = br.readUInt()
		br.seekBy(0x4)
		bone_parents_offset = br.readUInt64()
		br.seekBy(bone_parents_offset - 0x10) #the offset is relative to the offset of the num_entries
		self.bone_parents = br.readIntVec(num_entries)

	def write(self, br):
		br.writeUInt(len(self.bone_parents))
		br.align(8, 0xCD)
		br.writeUInt64(0x10)
		br.writeIntVec(self.bone_parents)

class BonePositions:
	def __init__(self):
		self.bone_positions = []

	def read(self, br, bone_count):
		for i in range(bone_count):
			self.bone_positions.append(br.readFloatVec(3))
			br.seekBy(0x4)

	def write(self, br):
		for val in self.bone_positions:
			br.writeFloatVec(val)
			br.align(8, 0xCD)

class BoneQuaternions:
	def __init__(self):
		self.bone_quaternions = []

	def read(self, br, bone_count):
		for i in range(bone_count):
			self.bone_quaternions.append(br.readFloatVec(4))

	def write(self, br):
		for val in self.bone_quaternions:
			br.writeFloatVec(val)

class StringTable:
	def __init__(self):
		self.data = []
		self.ids = []

	def read(self, br):
		base_offset = br.tell()
		num_entries = br.readUInt()
		data_length = br.readUInt()
		ids_offset = br.readUInt64() + base_offset
		offsets_offset = br.readUInt64() + base_offset
		data_offset = br.readUInt64() + base_offset

		br.seek(ids_offset)
		self.ids = br.readUIntVec(num_entries)

		br.seek(offsets_offset)
		offsets = br.readUIntVec(num_entries)

		br.seek(data_offset) #the intended way of reading this is with the offsets array, but this is faster
		for i in range(num_entries):
			self.data.append(br.readString())

	def write(self, br):
		base_offset = br.tell()
		br.writeUInt(len(self.data)) #num_entries

		data_length = 0
		for str in self.data:
			data_length = data_length + len(str) + 1

		ids_offset = 0x20

		br.writeUInt(data_length) #data_length
		br.writeUInt64(ids_offset) #ids_offset
		offsets_offset = len(self.data) * 0x4
		br.writeUInt64(offsets_offset + ids_offset)  #offsets_offset
		br.writeUInt64(offsets_offset * 2 + ids_offset) #data_offset

		br.writeUIntVec(self.ids)

		offsets = [0]
		data_length = 0
		for str in self.data:
			offsets.append(len(str) + data_length + 1)
			data_length = data_length + len(str) + 1

		offsets.pop()
		br.writeUIntVec(offsets)


		for str in self.data:
			br.writeString(str)

		br.align(4, 0xCD)
