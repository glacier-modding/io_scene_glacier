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
	
	def get_matrix(self, frame, matrix):
		print("bone:", self.name, "frame:", frame, "matrix:", matrix)
		return self.matrix[frame]