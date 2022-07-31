import struct
import binascii

class BinaryReader:
	def __init__(self, stream):
		self.file = stream

	def seek(self, position):
		self.file.seek(position)

	def seekBy(self, value):
		self.file.seek(self.file.tell() + value)

	def tell(self):
		return self.file.tell()

	def readHex(self, length):
		hexdata = self.file.read(length)
		hexstr = ''
		for h in hexdata:
			hexstr = hex(h)[2:].zfill(2) + hexstr
		return hexstr

	def readInt64(self):
		return struct.unpack('q', self.file.read(8))[0]

	def readUInt64(self):
		return struct.unpack('Q', self.file.read(8))[0]

	def readInt(self):
		return struct.unpack('i', self.file.read(4))[0]

	def readUInt(self):
		return struct.unpack('I', self.file.read(4))[0]

	def readUShort(self):
		return struct.unpack('H', self.file.read(2))[0]

	def readShort(self):
		return struct.unpack('h', self.file.read(2))[0]

	def readByte(self):
		return struct.unpack('b', self.file.read(1))[0]

	def readUByte(self):
		return struct.unpack('B', self.file.read(1))[0]

	def readFloat(self):
		return struct.unpack('!f', bytes.fromhex(self.readHex(4)))[0]

	def readShortVec(self, size):
		vec = [0] * size
		for i in range(size):
			vec[i] = self.readShort()
		return vec

	def readShortQuantizedVec(self, size, scale, bias):
		vec = [0] * size
		for i in range(size):
			vec[i] = ((self.readShort() * scale[i]) / 0x7FFF) + bias[i]
		return vec

	def readUByteQuantizedVec(self, size):
		vec = [0] * size
		for i in range(size):
			vec[i] = ((self.readUByte() * float(2.0)) / float(255.0)) + float(1.0)
		return vec

	def readUByteVec(self, size):
		vec = [0] * size
		for i in range(size):
			vec[i] = self.readUByte()
		return vec

	def peekHex(self, length):
		hexdata = self.file.read(length)
		hexstr = ''
		for h in hexdata:
			hexstr = hex(h)[2:].zfill(2) + hexstr
		file.seek(file.tell() - length)
		return hexstr

	def readUShortToFloatVec(self, size):
		vec = [0] * size
		for i in range(size):
			vec[i] = ((self.readUShort() * float(2.0)) / float(65535.0)) - float(1.0)
		return vec

	def readFloatVec(self, size):
		vec = [0] * size
		for i in range(size):
			vec[i] = self.readFloat()
		return vec

	def readUBytesToBitBoolArray(self, size):
		bit_array = ""
		bool_array = []
		bytes = self.readUByteVec(size)
		for i in range(size):
			bit_array = bin(bytes[i])[2:].zfill(8) + bit_array
		for i in bit_array[::-1]:
			bool_array.append(True if i == '1' else False)
		return { "count" : sum(bool_array), "bones" : bool_array }

	def readUIntVec(self, size):
		vec = [0] * size
		for i in range(size):
			vec[i] = self.readUInt()
		return vec

	def readIntVec(self, size):
		vec = [0] * size
		for i in range(size):
			vec[i] = self.readInt()
		return vec

	def readString(self):
		string = []
		while True:
			c = self.file.read(1)
			if c == b'\x00':
				return b"".join(string)
			string.append(c)