import os
import sys

class VertexDataSubMesh:
	def __init__(self):
		self.id = 0
		self.vertexColors = []

	def read(self, br):
		self.id = br.readUInt()
		num_vertices = br.readUInt()
		for vert in range(num_vertices):
			self.vertexColors.append(br.readUByteVec(4))

	def write(self, br):
		br.writeUInt(self.id)
		br.writeUInt(self.num_vertices())
		for vert in self.vertexColors:
			br.writeUByteVec(vert)

	def num_vertices(self):
		return len(self.vertexColors)

class VertexData:
	def __init__(self):
		self.sub_meshes = []

	def read(self, br):
		num_submeshes = br.readUInt()
		for sub_mesh in range(num_submeshes):
			self.sub_meshes.append(VertexDataSubMesh())
			self.sub_meshes[sub_mesh].read(br)

	def write(self, br):
		br.writeUInt(self.num_submeshes())
		for sub_mesh in self.sub_meshes:
			sub_mesh.write(br)

	def num_submeshes(self):
		return len(self.sub_meshes)
