import os
from pathlib import Path
from binary import BinaryStream
import yaml

outputYaml = "en.yaml"
files = Path("_DYextracted").glob('DisConv_Blurb_*')
output_dict = dict()


def strFinder(first, e6):
        global numv
        numv += 1
        if e6:
                if not first:
                        reader.readInt32()
                        reader.readInt32()
        first = False
        if not e6:
                if numv == 3:
                        reader.readInt32()
                        reader.readInt32()
                        numv = 0
        ls = reader.readInt32()
        if ls < 0:
                ls = abs(ls) * 2
        return reader.readString(ls)

for fileToExtract in files:
        fileSize = os.stat(fileToExtract).st_size
        name = Path(fileToExtract).stem
        fileObject = open(fileToExtract, "r+b")
        reader = BinaryStream(fileObject)

        reader.seek(102)

        types = reader.readByte()

        e6 = False
        if types == b"\xe6":
                e6 = True
                reader.seek(154)
        else:
                reader.seek(179)

        stringLen = reader.readInt32()

        origText = reader.readBytes(stringLen)

        try:
                output_dict[name] = origText.decode("utf-8").replace("\x00", "")
        except UnicodeDecodeError:
                print(fileToExtract)
                print(origText)
                output_dict[name] = str(origText)

        print(fileToExtract)
        # print(off)
        # while reader.readByte() == b"\x0d":
                # print(13)

        if e6:
                first = True
                numv = 2
                reader.readBytes(40) # from 3A20 or 3B20
                lnum = reader.readInt32()
                for i in range(lnum):
                        print(strFinder(first, e6).decode("utf-16"))
                        first = False
                break;

#
# with open(outputYaml, "w") as yaml_file:
#     yaml.dump(output_dict, yaml_file)








