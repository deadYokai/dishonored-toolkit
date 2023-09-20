import lzo
# import zlib
# import lzx
import io
from binary import BinaryStream

class DYCompressor:
    def __init__(self, compressorType):
        self.inputType = compressorType
        self.none = 0
        self.zlib = 1
        self.lzo = 2
        self.lzx = 4
        self.sign_upk = int.from_bytes(bytes([158, 42, 131, 193]))

    def unpackLZO(self, reader):
        cSign = reader.readUInt32()

        if cSign != self.sign_upk:
            raise Exception("Signature mismatch")

        blockSize = reader.readInt32()

        cSize = reader.readInt32()
        uSize = reader.readInt32()

        numBlock = (uSize + blockSize - 1) / blockSize

        print(numBlock)

        return lzo.decompress(cData)

    def getCompression(self):
        if self.inputType == 0:
            return "None"
        elif self.inputType == 1:
            return "ZLIB"
        elif self.inputType == 2:
            return "LZO"
        elif self.inputType == 4:
            return "LZX"
        else:
            return None

