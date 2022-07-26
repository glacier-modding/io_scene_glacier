import bpy
import json
from . import Animation

class MJBA:
	def __init__(self):
		self.mjba_file = ""
		self.hash = 0
		self.mjbaJSON = {}

	def load(self, path):
		with open(path, "rb") as f:
			self.mjbaJSON = json.load(f)
		for entry in self.mjbaJSON:
			print(entry)

	def save(self, path):
		pass