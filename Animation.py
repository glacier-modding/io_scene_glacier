import bpy
import json
from . import Bone
from . import MJBA
from . import MRTR

class Animation:
	def __init__(self, object):
		#self.bones_list = [bone.name for bone in object.data.bones]
		self.bones = {}
		#data_paths = {}
		for fcurve in object.animation_data.action.fcurves:
			#if fcurve.data_path not in data_paths:
				#data_paths[fcurve.data_path] = ""
			animation_type = fcurve.data_path[fcurve.data_path.rfind('.') + 1:]
			bone = fcurve.data_path.split('"')[1]
			if bone not in self.bones:
				self.bones[bone] = Bone.Bone(bone)            
			for keyframe in fcurve.keyframe_points:
				if animation_type == "location":
					self.bones[bone].set_position(keyframe.co[0], keyframe.co[1], fcurve.array_index)
				elif animation_type == "rotation_euler":
					self.bones[bone].set_rotation_euler(keyframe.co[0], keyframe.co[1], fcurve.array_index)
				elif animation_type == "rotation_quaternion":
					self.bones[bone].set_rotation_quaternion(keyframe.co[0], keyframe.co[1], fcurve.array_index)
				elif animation_type == "scale":
					self.bones[bone].set_scale(keyframe.co[0], keyframe.co[1], fcurve.array_index)

	def import_animation(self):
		pass

	def export_animation(self):
		pass