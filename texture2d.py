from io import BytesIO
import struct
from binary import BinaryStream
import os
import sys
from wand.image import Image
from upkElements import UpkElements

class Texture2D:

    def __init__(self, in_file, rrnames = None):
        if rrnames == None:
            with open(os.path.dirname(in_file) + "/_names.txt", "r") as nf:
                self.names = nf.read().split("\n")
        else:
            self.names = rrnames
        self.file = in_file
        if isinstance(self.file, BytesIO):
            self.fileObj = self.file
            self.file.seek(0, os.SEEK_END)
            self.datasize = self.file.tell()
            self.file.seek(0)
        else:
            self.fileObj = open(in_file, "rb+")
            self.datasize = os.stat(self.file).st_size
        self.reader = BinaryStream(self.fileObj)
        self.firstAddress = [0, 0]
        imgInfo = self.getMipMaps()
        self.mipmaps = imgInfo[0]
        self.pixFmt = imgInfo[1]

    def getMipMaps(self):
        mipmapsList = []
        r = self.reader
        fsize = self.datasize
        textureElem = UpkElements(self.names, r)
        te = textureElem.elements
        pixFmt = te["EPixelFormat"]["type"]
        r.seek(textureElem.endOffset+12)
        p = r.offset()
        if r.readUInt32() != 0:
            r.seek(p)
        magicNumber = r.offset()
        self.firstAddress = [magicNumber, r.readUInt32()]
        magicNumber = self.firstAddress[1] - magicNumber

        oneMp = True
        someUnk = r.readUInt32()
        if someUnk > 1:
            oneMp = False
        pixFmtName = pixFmt.replace("PF_", "")
        #print(pixFmtName)
        sizeOffsets = [te["OriginalSizeX"]["valoff"], te["OriginalSizeY"]["valoff"]]
        oSizeW = te["OriginalSizeX"]["value"]
        oSizeH = te["OriginalSizeY"]["value"]
        i = 0
        currOff = r.offset()
        while currOff <=fsize - (16 if oneMp else 24):
            ### ONE MIPMAP: 0000 SIZEBYTES SIZEBYTES ADDRESS
            ### MULTI MIPMAPS: SIZEX SIZEY 0000 SIZEBYTES SIZEBYTES ADDRESS
            ### TEXTURE DATA
            if not oneMp:
                sizeOffsets = [r.offset(), r.offset()+4]
                oSizeW = r.readUInt32()
                oSizeH = r.readUInt32()
            r.readUInt32()
            bytesLen = r.readUInt32()
            r.readUInt32()
            ofst = r.readInt32()
            mm = ofst - magicNumber - r.offset() + 4 # find correct address
            if mm != 0:
                currOff = currOff + 4
                r.seek(currOff)
                continue
            currOff = r.offset()
            i += 1
            r.seek(r.offset() + bytesLen)
            mipmapsList.append({"offset": currOff, "address": ofst, "bytes": bytesLen, "sizeX": oSizeW, "sizeY": oSizeH, "sizeOffsets": sizeOffsets})
        return mipmapsList, pixFmtName

    def unpack(self):
        pixFmtName = self.pixFmt
        if "RGBA" in pixFmtName:
            pixFmtName = "RGBA"
        allowedFmt = ["DXT5", "DXT1", "DXT3", "RGBA"]
        if not pixFmtName in allowedFmt:
            print(f"ERR: {pixFmtName} not supported.")
            return
        r = self.reader
        i = 0
        for mm in self.mipmaps:
            newDDS = b'DDS |\x00\x00\x00'
            newDDS += b'\x07\x10\x00\x00'
            newDDS += struct.pack("i", mm["sizeY"])
            newDDS += struct.pack("i", mm["sizeX"])
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
            r.seek(mm["offset"]+8)
            newDDS += r.readBytes(mm["bytes"]-8)
            with open(os.path.dirname(self.file) + "/" + os.path.basename(self.file) + "." + str(i) + ".dds", "wb") as nd:
                nd.write(newDDS)
            i += 1
        self.fileObj.close()

    def pack(self, in_dds):
        if len(self.mipmaps) > 1:
            print("Textures with multiple mipmaps not supported")
            return
        with Image(filename=in_dds) as oi:
            if self.pixFmt == "RGBA":
                oi.compression = 'no'
            else:
                oi.compression = self.pixFmt.lower()
            oi.save(filename=in_dds)

        with open(in_dds, "rb") as dds:
            dreader = BinaryStream(dds)
            dreader.seek(12)
            bsize = [dreader.readInt32(), dreader.readInt32()]
            if self.pixFmt == "RGBA":
                dreader.seek(dreader.offset() + 88)
            else:
                dreader.seek(136)
            dsize = os.stat(in_dds).st_size
            data = dreader.readBytes(dsize - dreader.offset())
        
        r = self.reader
        r.seek(self.mipmaps[0]['offset'] + self.mipmaps[0]['bytes'] + 8)
        endData = r.readBytes(self.datasize - r.offset())
        r.seek(self.mipmaps[0]['offset']+8)
        r.clear()
        r.writeBytes(data)
        r.writeInt32(bsize[1])
        r.writeInt32(bsize[0])
        r.writeBytes(endData)

        r.seek(self.mipmaps[0]["sizeOffsets"][0])
        r.writeInt32(bsize[1])
        r.seek(self.mipmaps[0]["sizeOffsets"][1])
        r.writeInt32(bsize[0])

        r.seek(self.mipmaps[0]['offset']-12)
        r.writeInt32(len(data)+8)
        r.writeInt32(len(data)+8)
        self.fileObj.close()

if __name__ == "__main__":
    args = sys.argv[1::]
    if "-p" in args:
        idx = args.index("-p")
        tex2d = Texture2D(args[idx+1])
        tex2d.pack(args[idx+2])
    else:
        tex2d = Texture2D(args[0])
        tex2d.unpack()

    print(tex2d.mipmaps)
    print(tex2d.firstAddress)    

