import bpy
import json
from . import Animation

class GlacierEngine:
	def import_mjba(self, object):
		animation = Animation.Animation(object)
		animation.import_animation()
	
	def export_mjba(self, object):
		animation = Animation.Animation(object)
		animation.export_animation()
	
	def export_mrtr(self, object):
		pass