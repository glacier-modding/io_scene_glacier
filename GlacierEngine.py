import bpy
from .Animation import Animation

class GlacierEngine:
	def import_animation(self, object, mjba_path, mrtr_path):
		self.animation = Animation(object, mjba_path, mrtr_path)
		self.animation.import_animation()
		self.animation.apply_animation()
	
	def export_animation(self, object):
		#self.animation = Animation(object, mjba_path, mrtr_path)
		#self.animation.export_animation()
		pass