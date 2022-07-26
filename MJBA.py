import bpy
import json
from . import Animation

class MJBA:
	def import_json(self, path):
		with open(path, "rb") as f:
			self.mjbaJSON = json.load(f)
		self.bones = {}
		for bone in self.mjbaJSON["Bones"]:
			position = bone.get("Transform")
			rotation = bone.get("Quaternion")
			used = False
			if bone["Id"] != None:
				used = True
			self.bones[bone["Name"]] = [ position, rotation, used ]

	def get_fps(self):
		return int(self.mjbaJSON["FPS"])

	def get_frame_count(self):
		return len(self.mjbaJSON["Animation"])

	def get_used_bone_list(self):
		bone_list = []
		for bone, data in self.bones.items():
			if data[2]:
				bone_list.append(bone)
		return bone_list

	def get_bone_location(self, frame, bone):
		if self.bones[bone][0] != None:
			return #(self.bones[bone][0]["x"], self.bones[bone][0]["y"], self.bones[bone][0]["z"])
		x = self.mjbaJSON["Animation"][frame][bone]["Transform"]["x"]
		y = self.mjbaJSON["Animation"][frame][bone]["Transform"]["y"]
		z = self.mjbaJSON["Animation"][frame][bone]["Transform"]["z"]
		return (x, y, z)

	def get_bone_rotation(self, frame, bone):
		if self.bones[bone][1] != None:
			return #(self.bones[bone][1]["w"], self.bones[bone][1]["x"], self.bones[bone][1]["y"], self.bones[bone][1]["z"])
		w = self.mjbaJSON["Animation"][frame][bone]["Quaternion"]["w"]
		x = self.mjbaJSON["Animation"][frame][bone]["Quaternion"]["x"]
		y = self.mjbaJSON["Animation"][frame][bone]["Quaternion"]["y"]
		z = self.mjbaJSON["Animation"][frame][bone]["Quaternion"]["z"]
		return (w, x, y, z)