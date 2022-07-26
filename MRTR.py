import bpy
import json
from . import Animation

class MRTR:
	def __init__(self):
		self.mtrt_file = ""
		self.hash = 0
		self.mrtrJSON = {}

	def load(self, path):
		with open(path, "rb") as f:
			self.mrtrJSON = json.load(f)
		for entry in self.mrtrJSON:
			print(entry)

	def save(self, path):
		pass