import struct
import binascii


class BinaryReader:
    def __init__(self, stream):
        self.file = stream

    def close(self):
        self.file.close()

    def seek(self, position):
        self.file.seek(position)

    def seekBy(self, value):
        self.file.seek(self.file.tell() + value)

    def tell(self):
        return self.file.tell()

    # reading
    def readHex(self, length):
        hexdata = self.file.read(length)
        hexstr = ""
        for h in hexdata:
            hexstr = hex(h)[2:].zfill(2) + hexstr
        return hexstr

    def readInt64(self):
        return struct.unpack("q", self.file.read(8))[0]

    def readUInt64(self):
        return struct.unpack("Q", self.file.read(8))[0]

    def readInt(self):
        return struct.unpack("i", self.file.read(4))[0]

    def readIntBigEndian(self):
        return struct.unpack(">i", self.file.read(4))[0]

    def readUInt(self):
        return struct.unpack("I", self.file.read(4))[0]

    def readUShort(self):
        return struct.unpack("H", self.file.read(2))[0]

    def readShort(self):
        return struct.unpack("h", self.file.read(2))[0]

    def readByte(self):
        return struct.unpack("b", self.file.read(1))[0]

    def readUByte(self):
        return struct.unpack("B", self.file.read(1))[0]

    def readFloat(self):
        return struct.unpack("!f", bytes.fromhex(self.readHex(4)))[0]

    def readShortVec(self, size):
        vec = [0] * size
        for i in range(size):
            vec[i] = self.readShort()
        return vec

    def readShortQuantizedVec(self, size):
        vec = [0] * size
        for i in range(size):
            vec[i] = self.readShort() / 0x7FFF
        return vec

    def readShortQuantizedVecScaledBiased(self, size, scale, bias):
        vec = [0] * size
        for i in range(size):
            vec[i] = ((self.readShort() * scale[i]) / 0x7FFF) + bias[i]
        return vec

    def readUByteQuantizedVec(self, size):
        vec = [0] * size
        for i in range(size):
            vec[i] = ((self.readUByte() * 2) / 255) - 1
        return vec

    def readUByteVec(self, size):
        vec = [0] * size
        for i in range(size):
            vec[i] = self.readUByte()
        return vec

    def peekHex(self, length):
        hexdata = self.file.read(length)
        hexstr = ""
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
            bool_array.append(True if i == "1" else False)
        return {"count": sum(bool_array), "bones": bool_array}

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

    def readString(self, length):
        string = []
        for char in range(length):
            c = self.file.read(1)
            if c != b"\x00":
                string.append(c)
            if not c:
                break
        return b"".join(string)

    def readCString(self):
        string = []
        while True:
            c = self.file.read(1)
            if c == b"\x00":
                return b"".join(string)
            string.append(c)

    # writing
    def align(self, num, bit=0x0):
        padding = (num - (self.tell() % num)) % num
        self.writeHex(bytes([bit] * padding))

    def writeHex(self, bytes):
        self.file.write(bytes)

    def writeInt64(self, val):
        self.file.write(val.to_bytes(8, byteorder="little", signed=True))

    def writeUInt64(self, val):
        self.file.write(val.to_bytes(8, byteorder="little", signed=False))

    def writeInt(self, val):
        self.file.write(val.to_bytes(4, byteorder="little", signed=True))

    def writeUInt(self, val):
        self.file.write(val.to_bytes(4, byteorder="little", signed=False))

    def writeShort(self, val):
        self.file.write(val.to_bytes(2, byteorder="little", signed=True))

    def writeUShort(self, val):
        self.file.write(val.to_bytes(2, byteorder="little", signed=False))

    def writeByte(self, val):
        self.file.write(val.to_bytes(1, byteorder="little", signed=True))

    def writeUByte(self, val):
        self.file.write(val.to_bytes(1, byteorder="little", signed=False))

    def writeFloat(self, val):
        self.file.write(struct.pack("f", val))

    def writeShortVec(self, vec):
        for val in vec:
            self.writeShort(val)

    def writeShortQuantizedVec(self, vec):
        for i in range(len(vec)):
            self.writeShort(int(round(vec[i] * 0x7FFF)))

    def writeShortQuantizedVecScaledBiased(self, vec, scale, bias):
        for i in range(len(vec)):
            value = int(round(((vec[i] - bias[i]) * 0x7FFF) / scale[i]))
            if value > 0x7FFF:
                value = 0x7FFF
            elif value < -0x7FFF:
                value = -0x7FFF
            self.writeShort(value)

    def writeUByteQuantizedVec(self, vec):
        for val in vec:
            self.writeUByte(int(round(((val + 1) * 255) / 2)))

    def writeUByteVec(self, vec):
        for val in vec:
            self.writeUByte(val)

    def writeUShortFromFloatVec(self, vec):
        for val in vec:
            self.writeUShort(int(round(((val + 1) * 0xFFFF) / 2)))

    def writeFloatVec(self, vec):
        for val in vec:
            self.writeFloat(val)

    def writeUBytesFromBitBoolArray(self, vec):
        print(
            "Attempted to use writeUBytesFromBitBoolArray, but this function is not implemented yet!"
        )

    def writeUIntVec(self, vec):
        for val in vec:
            self.writeUInt(val)

    def writeIntVec(self, vec):
        for val in vec:
            self.writeInt(val)

    def writeCString(self, string):
        if len(string) > 0:
            self.writeHex(string)
            self.writeUByte(0)

    def writeString(self, string, length):
        self.writeHex(string)
        self.writeUByteVec([0] * (length - len(string)))

    def IOI_round(self, float):
        # please upgrade to a modulo solution
        byte_const = 1 / 255
        rounded_byte = 0
        byte = int(float / byte_const)
        if abs(float - (byte * byte_const)) > abs(float - ((byte + 1) * byte_const)):
            rounded_byte = byte
        else:
            rounded_byte = byte + 1

        return rounded_byte - 1
