import bpy
from .Animation import Animation

class GlacierEngine:
	def import_animation(self, object, mjba_path, mrtr_path):
		try:
			self.quaternion_to_try += 1
		except AttributeError:
			self.quaternion_to_try = 0
		print("Trying:", self.quaternion_to_try)
		try:
			del self.animation
			self.animation = Animation(object, mjba_path, mrtr_path)
			self.animation.import_animation(self.quaternion_to_try)
			self.animation.apply_animation()
		except AttributeError:
			self.animation = Animation(object, mjba_path, mrtr_path)
			self.animation.import_animation(self.quaternion_to_try)
			self.animation.apply_animation()
	
	def export_animation(self, object):
		#self.animation = Animation(object, mjba_path, mrtr_path)
		#self.animation.export_animation()
		pass