import os
import re
import sys
import json

from binary import BinaryStream

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

        with open(f"{out}/charTable.json", "w", encoding="utf-8") as cf:
            chars = []
            reader.seek(offCharTable)
            for c in range(charNum):
                chars.append({"StartU": reader.readInt32(), 
                              "StartV": reader.readInt32(), 
                              "USize": reader.readInt32(),
                              "VSize": reader.readInt32(),
                              "TextureIndex": int.from_bytes(reader.readByte()),
                              "VerticalOffset": reader.readInt32()})
            json.dump(chars, cf, indent=4, ensure_ascii=False)


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
