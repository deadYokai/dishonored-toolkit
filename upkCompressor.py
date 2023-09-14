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

    def unpackLZO(self, chunk, clen):
        reader = BinaryStream(io.BytesIO(chunk))
        signature = reader.readInt32()
        if signature != -1641380927:
            raise Exception("LZO: invalid signature")

        blocksize = reader.readInt32()
        print(blocksize)

        return "none"
        # return lzo.decompress(chunk, False, clen)

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

