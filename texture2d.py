import struct
from binary import BinaryStream
import os
import sys

def extract(in_file):
    with open(os.path.dirname(in_file) + "/_names.txt", "r") as nf:
        names = nf.read().split("\n")

    with open(in_file, "rb") as tf:
        r = BinaryStream(tf)

        r.seek(28)
        size = []
        for a in range(4):
            size.append(r.readInt32())
            r.seek(r.offset() + 24)

        r.seek(r.offset() + 8)
        pixFmt = r.readInt32()

        r.readBytes(145)
        bytesLen = r.readInt32()
        r.readBytes(12)
        data = r.readBytes(bytesLen - 8)
        oSizeW = r.readInt32()
        oSizeH = r.readInt32()

        newDDS = b'DDS |\x00\x00\x00'
        newDDS += b'\x07\x10\x00\x00'
        newDDS += struct.pack("i", oSizeH)
        newDDS += struct.pack("i", oSizeW)
        newDDS += bytes(56)
        newDDS += struct.pack("i", 32)
        newDDS += struct.pack("i", 4)
        newDDS += names[pixFmt].replace("PF_", "").encode()
        newDDS += bytes(20)
        newDDS += struct.pack("i", 1)
        newDDS += bytes(24)
        newDDS += data
        with open(os.path.dirname(in_file) + "/" + os.path.basename(in_file) + ".dds", "wb") as nd:
            nd.write(newDDS)

if __name__ == "__main__":
    args = sys.argv[1::]
    if "-p" in args:
        pass
    else:
        extract(args[0])

