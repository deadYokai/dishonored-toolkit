import os
from os.path import isfile
import re
import struct
import sys
import json

import glob
from wand.image import Image, Color
from wand.drawing import Drawing
from wand.color import Color
from binary import BinaryStream
import texture2d
def create(inFile, fontFile):
    fn = os.path.basename(inFile)
    fd = os.path.dirname(inFile)
    dir = f"{fd}/_{fn}"

    size = [1024, 512]

    fontInfoFile = dir + "/fontInfo.json"   
    if not os.path.isfile(fontInfoFile):
        extract(inFile, dir, True)

    with open(fontInfoFile, "r") as infoFile:
        fontInfo = json.load(infoFile)
    
    charList = sorted(list(set([a for a in fontInfo["Charset"]])))[1::]
    newFontDds = Image(width=size[0], height=size[1])
    newFontDds.format = "dds"
    newFontDds.compression = "dxt5"
    x = 0 
    y = 48
    charTbl = []

    for i in range(0, 255): # range to FF00
        charTbl.append({"CharHex": chr(i).encode("utf-16le").hex(), "ID": i, "CharData": {"StartU": 0, "StartV": 0, "USize": 0, "VSize": 0, "TextureIndex": 0, "VerticalOffset": 0}})

    with Drawing() as draw:
        draw.font = fontFile
        draw.font_size = 40
        draw.fill_color = Color("white")
        for c in charList:
            fm = draw.get_font_metrics(text=c, image=newFontDds)
            w = int(fm.text_width)
            h = int(fm.text_height)

            if (x+w) > size[0]:
                x = 0
                y += h

            if ord(c) <=len(charTbl):
                charTbl[ord(c)] = {"CharHex": c.encode("utf-16le").hex(), "ID": ord(c), "CharData": {"StartU": x, "StartV": y, "USize": w, "VSize": h, "TextureIndex": 0, "VerticalOffset": 0}}
            else:
                charTbl.append({"CharHex": c.encode("utf-16le").hex(), "ID": len(charTbl), "CharData": {"StartU": x, "StartV": y, "USize": w, "VSize": h, "TextureIndex": 0, "VerticalOffset": 0}})
            draw.text(x, y, c)
            x = x + w

    
        draw(newFontDds)

    newFontDds.save(filename=f"{dir}/{fontInfo["ddsFile"]}")
    texture2dFile = dir + "/../" + fontInfo["ddsFile"].replace(".dds", "")

    with open(texture2dFile, "rb") as t2:
        with open(texture2dFile + "_patched", "wb") as tt:
            tt.write(t2.read())

    texture2d.process(texture2dFile + "_patched", f"{dir}/{fontInfo["ddsFile"]}")

    with open(dir + "/newCharTable.json", "w") as ncht:
        json.dump(charTbl, ncht, indent=4, ensure_ascii=False)

    fontR = getFileReader(inFile)
    reader = fontR["reader"]
    fHeader = reader.readBytes(20)
    
    reader.seek(fontR["offsets"]["charTableEnd"])
    fFontData1 = reader.readBytes(fontR["offsets"]["charList"] - fontR["offsets"]["charTableEnd"])

    reader.seek(fontR["offsets"]["charListEnd"])
    fFontData2 = reader.readBytes(fontR["offsets"]["charNum"][1] - fontR["offsets"]["charListEnd"])

    charTable = b''
    charTable += struct.pack("I", len(charTbl))
    charTable += bytes(4)
    for a in charTbl:
        cd = a["CharData"]
        charTable += struct.pack("I", cd["StartU"])
        charTable += struct.pack("I", cd["StartV"])
        charTable += struct.pack("I", cd["USize"])
        charTable += struct.pack("I", cd["VSize"])
        charTable += struct.pack("b", cd["TextureIndex"])
        charTable += struct.pack("I", cd["VerticalOffset"])

    newFontFile = fHeader
    newFontFile += struct.pack("I", len(charTable))
    newFontFile += bytes(4)
    newFontFile += charTable
    newFontFile += fFontData1

    charlistbytes = struct.pack("i", (len(charList) + 1) * -1)
    charlistbytes += ''.join(charList).encode("utf-16le")
    charlistbytes += bytes(2)

    charBytes = struct.pack("I", len(charlistbytes))
    charBytes += bytes(4)
    charBytes += charlistbytes

    newFontFile += charBytes
    newFontFile += fFontData2

    charIndexBytes = struct.pack("I", len(charTbl))
    for c in charTbl:
       charIndexBytes += bytes.fromhex(c["CharHex"])
       charIndexBytes += struct.pack("h", c["ID"])

    newFontFile += charIndexBytes

    with open(inFile + "_patched", "wb") as newFont:
        newFont.write(newFontFile)


def getFileReader(fileToExtract):

        # open file and create stream
        fileSize = os.stat(fileToExtract).st_size
        fileObject = open(fileToExtract, "r+b")
        reader = BinaryStream(fileObject)

        reader.readBytes(20)

        offOffset = reader.offset()
        charTableLen = reader.readInt32()

        reader.readInt32()

        offCharNum = reader.offset()
        charNum = reader.readInt32()

        offCharTable = reader.offset()


        reader.seek(offCharNum + charTableLen)
        endTable = reader.offset()
        reader.readBytes(160)
        
        fontDataLenOff = reader.offset()
        fontDataLen = reader.readInt32()
        reader.readInt32()
        fdo = reader.offset() # font data start offset
        reader.readBytes(32)
        fontNameSize = reader.readInt32()
        fontName = reader.readBytes(fontNameSize).decode("utf-8")
        
        important24bytes = reader.readBytes(24)
        fontHeight = reader.readFloat()
        reader.readBytes(16)
        charListOff = reader.offset()
        charDataLen = reader.readInt32() # string with string len size
        reader.readInt32()
        charLen = reader.readInt32() * -2
        chars = reader.readBytes(charLen).decode("utf-16le")
        endCharsOff = reader.offset()

        reader.seek(fdo + fontDataLen)
        #yPadding = reader.readInt32()
        reader.readBytes(16)
        ct = reader.offset()
        charNum2 = reader.readInt32()
        return {"reader": reader, "fontInfo": {"fontName": fontName, "fontHeight": fontHeight, "CharNum": charNum, "Charset": chars}, "offsets": {"charTableLen": offOffset, "charNum": [offCharNum, ct], "charTable": offCharTable, "charList": charListOff, "fontDataLen": fontDataLenOff, "fontData": fdo, "charTableEnd": endTable, "charListEnd": endCharsOff}}

def extract(fileToExtract, out, jsonOnly = False):

        if not os.path.isdir(out):
                os.mkdir(out)
        fontR = getFileReader(fileToExtract)
        reader = fontR["reader"]
        charNum = fontR["fontInfo"]["CharNum"]
        ct = fontR["offsets"]["charNum"][1]
        offCharTable = fontR["offsets"]["charTable"]


        name = os.path.basename(fileToExtract).split(".")[0]
        ddsGlob = glob.glob(f"{out}/../{name}*.dds")
        if ddsGlob == []:
            tex = glob.glob(f"{out}/../{name}*.Texture2D")[0]
            texture2d.process(tex)
            ddsGlob = glob.glob(f"{out}/../{name}*.dds")
        ddsFile = Image(filename=ddsGlob[0])
        fontR["fontInfo"]["ddsFile"] = os.path.basename(ddsGlob[0])
        with open(f"{out}/fontInfo.json", "w", encoding="utf-8") as inf:
            json.dump(fontR["fontInfo"], inf, ensure_ascii=False, indent=4)

        if not jsonOnly:
            os.makedirs(f"{out}/chars", exist_ok=True)

        with open(f"{out}/charTable.json", "w", encoding="utf-8") as cf:
            charTableArr = []
            reader.seek(ct+4)
            for c in range(charNum):
                charTableArr.append({"CharHex": reader.readBytes(2).hex(), "ID": reader.readInt16()})

            reader.seek(offCharTable)
            for c in range(charNum):
                dd = {"StartU": reader.readInt32(), 
                      "StartV": reader.readInt32(), 
                      "USize": reader.readInt32(),
                      "VSize": reader.readInt32(),
                      "TextureIndex": int.from_bytes(reader.readByte()),
                      "VerticalOffset": reader.readInt32()}
                
                charTableArr[c]["CharData"] = dd

                x = dd["StartU"]
                y = dd["StartV"]
                w = dd["USize"]
                h = dd["VSize"]
                if not jsonOnly:
                    if w != 0 and h != 0:
                        with ddsFile[x:w+x, y:h+y] as cImg:
                            charTex = charTableArr[c]["CharHex"]
                            cImg.save(filename=f"{out}/chars/{c}.{charTex}.dds")

            json.dump(charTableArr, cf, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    args = sys.argv[1::]
    for arg in args:
        if arg.startswith("-"):
            param = arg.split("-")[1]
            if param == "e":
                if len(args) > args.index(arg) + 1:
                    filename = args[args.index(arg) + 1]
                    fn = os.path.basename(filename)
                    fd = os.path.dirname(filename)
                    extract(filename, f"{fd}/_{fn}")
                break
            if param == "p":
                if len(args) > args.index(arg) + 2:
                    filename = args[args.index(arg) + 1]
                    fontfile = args[args.index(arg) + 2]
                    create(filename, fontfile)
                break
