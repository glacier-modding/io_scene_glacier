import bpy
import json

class Bone:
	def __init__(self, name):
		self.name = ""
		self.positions = {}
		self.rotations = {}
		self.scales = {}
	
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