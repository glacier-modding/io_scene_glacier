import bpy
import json
from . import Bone
from . import MJBA
from . import MRTR

class Animation:
	def __init__(self, object):
		self.object = object
		self.bones = {}		
		for fcurve in self.object.animation_data.action.fcurves:
			animation_type = fcurve.data_path[fcurve.data_path.rfind('.') + 1:]
			bone = fcurve.data_path.split('"')[1]
			if bone not in self.bones:
				self.bones[bone] = Bone.Bone(object, bone)
			for keyframe in fcurve.keyframe_points:
				if animation_type == "location":
					self.bones[bone].set_position_animated()
				elif animation_type == "rotation_euler":
					self.bones[bone].set_rotation_animated()
				elif animation_type == "rotation_quaternion":
					self.bones[bone].set_rotation_animated()
				elif animation_type == "scale":
					self.bones[bone].set_scale_animated()
		for frame in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
			bpy.context.scene.frame_set(frame)
			for bone in object.pose.bones:
				if bone in self.bones:
					self.bones[bone].set_matrix(frame, bone.matrix)

	def import_animation(self):
		pass

	def export_animation(self):
		pass