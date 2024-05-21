import struct
from binary import BinaryStream
import os
import sys
from wand.image import Image

def process(in_file, out_dds = None):
    pack = True
    if out_dds == None:
        pack = False
    with open(os.path.dirname(in_file) + "/_names.txt", "r") as nf:
        names = nf.read().split("\n")

    with open(in_file, "rb+") as tf:
        r = BinaryStream(tf)
        fsize = os.stat(in_file).st_size

        r.seek(28)
        size = []
        soff = []
        for a in range(4):
            soff.append(r.offset())
            size.append(r.readInt32())
            r.seek(r.offset() + 24)

        r.seek(r.offset() + 8)
        pixFmt = r.readInt32()

        r.readBytes(145)
        bl = r.offset()
        bytesLen = r.readInt32()
        r.readBytes(12)
        bd = r.offset()
        data = r.readBytes(bytesLen - 8)
        oSizeW = r.readInt32()
        oSizeH = r.readInt32()
        endData = r.readBytes(fsize - r.offset())
        pixFmtName = names[pixFmt].replace("PF_", "")
        if "RGBA" in pixFmtName:
            pixFmtName = "RGBA"
        allowedFmt = ["DXT5", "DXT1", "DXT3", "RGBA"]
        if not pixFmtName in allowedFmt:
            print(f"ERR: {pixFmtName} not supported.")
            return

        if not pack:
            newDDS = b'DDS |\x00\x00\x00'
            newDDS += b'\x07\x10\x00\x00'
            newDDS += struct.pack("i", oSizeH)
            newDDS += struct.pack("i", oSizeW)
            newDDS += bytes(56) # MipMaps
            newDDS += struct.pack("i", 32)

            if pixFmtName == "RGBA":
                newDDS += struct.pack("i", 66)
                newDDS += bytes(4)
                newDDS += struct.pack("i", 32)
                newDDS += b'\x00\x00\xFF\x00'
                newDDS += b'\x00\xFF\x00\x00'
                newDDS += b'\xFF\x00\x00\x00'
                newDDS += b'\x00\x00\x00\xFF'
            else:
                newDDS += struct.pack("i", 4)
                newDDS += pixFmtName.encode()
                newDDS += bytes(20)
                newDDS += struct.pack("i", 1)
                newDDS += bytes(24)
            newDDS += data
            with open(os.path.dirname(in_file) + "/" + os.path.basename(in_file) + ".dds", "wb") as nd:
                nd.write(newDDS)
        else:
            with Image(filename=out_dds) as oi:
                oiw = oi.width
                oih = oi.height
                oi.compression = pixFmtName.lower()
                if pixFmtName == "RGBA":
                    oi.compression = 'no'
                oi.save(filename=out_dds)

            with open(out_dds, "rb") as dds:
                dreader = BinaryStream(dds)
                dreader.seek(12)
                bsize = [dreader.readInt32(), dreader.readInt32()]
                if pixFmtName == "RGBA":
                    dreader.seek(dreader.offset() + 88)
                else:
                    dreader.seek(136)
                dsize = os.stat(out_dds).st_size
                data = dreader.readBytes(dsize - dreader.offset())

            r.seek(bd)
            r.clear()
            r.writeBytes(data)
            r.writeInt32(bsize[1])
            r.writeInt32(bsize[0])
            r.writeBytes(endData)
            a = False
            for i in range(len(soff)):
                r.seek(soff[i])
                if a:
                    r.writeInt32(bsize[0])
                else:
                    r.writeInt32(bsize[1])
                a = not a
            r.seek(bl - 4)
            r.writeInt32(len(data)+8)
            r.writeInt32(len(data)+8)



if __name__ == "__main__":
    args = sys.argv[1::]
    if "-p" in args:
        idx = args.index("-p")
        process(args[idx+1], args[idx+2])
    else:
        process(args[0])

