import os
from os.path import isfile
import re
import sys
import json
import fontforge

import glob
from wand.image import Image, Color
from binary import BinaryStream
from texture2d import process
def create(inFile, fontFile):
    fn = os.path.basename(inFile)
    fd = os.path.dirname(inFile)
    dir = f"{fd}/_{fn}"

    fontInfoFile = dir + "/fontInfo.json"   
    if not os.path.isfile(fontInfoFile):
        extract(inFile, dir)

    with open(fontInfoFile, "r") as infoFile:
        fontInfo = json.load(infoFile)
    
    charList = sorted(list(set([a for a in fontInfo["Charset"]])))[1::]
    font = fontforge.open(fontFile)
    font.encoding = "UnicodeFull"
    for c in charList:
        font.selection.select(("more", None), ord(c))
    for glyph in font:
        print(glyph)
        if font[glyph].isWorthOutputting():
            svgFile = dir + "/testSubject/" + font[glyph].glyphname + ".svg"
            font[glyph].export(svgFile)
            with Image(filename=svgFile, background=Color("transparent"), resolution=fontInfo["FontHeight"]) as img:
                img.format = "dds"
                img.compression = "dxt5"
                img.opaque_paint(target="#000000", fill="white")
                img.save(filename=svgFile.replace(".svg", ".dds"))
            os.remove(svgFile)

def extract(fileToExtract, out):

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

        if not os.path.isdir(out):
                os.mkdir(out)

        reader.seek(offCharNum + charTableLen)

        reader.readBytes(160)
        
        fontDataLen = reader.readInt32()
        reader.readInt32()
        fdo = reader.offset()
        reader.readBytes(32)
        fontNameSize = reader.readInt32()
        fontName = reader.readBytes(fontNameSize).decode("utf-8")
        
        important24bytes = reader.readBytes(24)
        fontHeight = reader.readFloat()
        reader.readBytes(16)
        charDataLen = reader.readInt32()
        reader.readInt32()
        charLen = reader.readInt32() * -2
        chars = reader.readBytes(charLen).decode("utf-16le")

        reader.seek(fdo + fontDataLen)
        #yPadding = reader.readInt32()
        reader.readBytes(16)
        charNum2 = reader.readInt32()

        with open(f"{out}/fontInfo.json", "w", encoding="utf-8") as inf:
            json.dump({"Name": fontName, "Charset": chars, "FontHeight": fontHeight}, inf, ensure_ascii=False, indent=4)

        name = os.path.basename(fileToExtract).split(".")[0]
        ddsGlob = glob.glob(f"{out}/../{name}*.dds")
        if ddsGlob == []:
            tex = glob.glob(f"{out}/../{name}*.Texture2D")[0]
            process(tex)
            ddsGlob = glob.glob(f"{out}/../{name}*.dds")
        ddsFile = Image(filename=ddsGlob[0])
        os.makedirs(f"{out}/chars", exist_ok=True)

        with open(f"{out}/charTable.json", "w", encoding="utf-8") as cf:
            charIdx = sorted(list(set([ord(a) for a in chars])))[1::]
            print(charIdx)
            charsTex = []
            reader.seek(offCharTable)
            cx = 0
            for c in range(charNum):
                dd = {"StartU": reader.readInt32(), 
                      "StartV": reader.readInt32(), 
                      "USize": reader.readInt32(),
                      "VSize": reader.readInt32(),
                      "TextureIndex": int.from_bytes(reader.readByte()),
                      "VerticalOffset": reader.readInt32()}
                charsTex.append(dd)
                
                x = dd["StartU"]
                y = dd["StartV"]
                w = dd["USize"]
                h = dd["VSize"]
                if c >=32: # before is null chars
                    if w != 0 and h != 0:
                        with ddsFile[x:w+x, y:h+y] as cImg:
                            ch = chr(charIdx[cx])
                            charTex = ch.encode("utf-16le").hex()
                            cImg.save(filename=f"{out}/chars/{c}.{charTex}.dds")
                            cx += 1

            json.dump(charsTex, cf, indent=4, ensure_ascii=False)


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
