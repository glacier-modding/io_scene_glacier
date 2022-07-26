import bpy
import json

class Bone:
	def __init__(self, object, name):
		self.object = object
		self.name = name
		self.position_animated = False
		self.rotation_animated = False
		self.scale_animated = False
		self.matrix = {}

	def set_position_animated(self):
		print("bone:", self.name, "has position animated")
		self.position_animated = True

	def set_rotation_animated(self):
		print("bone:", self.name, "has rotation animated")
		self.rotation_animated = True

	def set_scale_animated(self):
		print("bone:", self.name, "has scale animated")
		self.scale_animated = True
	
	def set_matrix(self, frame, matrix):
		print("bone:", self.name, "frame:", frame, "matrix:", matrix)
		self.matrix[frame] = matrix
	
	def set_position(self, frame, position, index):
		print("bone:", self.name, "frame:", frame, "position:", position, "index:", index)
		self.positions[frame] = position
	
	def get_position(self, frame, position, index):
		return self.positions[frame]
	
	def set_rotation_euler(self, frame, rotation, index):
		print("bone:", self.name, "frame:", frame, "rotation_euler:", rotation, "index:", index)
		self.rotations[frame] = rotation
	
	def get_rotation_euler(self, frame, rotation, index):
		return self.rotations[frame]
	
	def set_rotation_quaternion(self, frame, rotation, index):
		print("bone:", self.name, "frame:", frame, "rotation_quaternion:", rotation, "index:", index)
		self.rotations[frame] = rotation
	
	def get_rotation_quaternion(self, frame, rotation, index):
		return self.rotations[frame]
	
	def set_scale(self, frame, scale, index):
		print("bone:", self.name, "frame:", frame, "scale:", scale, "index:", index)
		self.scales[frame] = scale
	
	def get_scale(self, frame, scale, index):
		return self.scales[frame]