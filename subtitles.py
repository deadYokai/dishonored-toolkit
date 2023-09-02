import os
from pathlib import Path
from binary import BinaryStream
import yaml
import struct

outputYaml = "en.yaml"
files = Path("../_DYextracted").glob('DisConv_Blurb_*')
output_dict = dict()

numv = 2
def strFinder():
        off = reader.offset()
        ls = reader.readInt32()

        while ls == 0:
                h = reader.offset()
                off = h
                ls = reader.readInt32()

        if ls > 1000: # if starts with ?? FF FF FF
                reader.readInt32()
                off = reader.offset()
                ls = reader.readInt32()

        is2b = False
        if ls < 0:
                is2b = True
                ls = (abs(ls) * 2)

        return [off, ls, reader.readString(ls), is2b]

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
                # print(fileToExtract)
                # print(origText)
                output_dict[name] = str(origText)

        pointerOff1 = reader.offset()

        pointer = reader.readInt32()
        fPoint  = pointer
        if pointer != 5264:
                reader.readBytes(24)
                pointer = reader.readInt32()
        reader.readInt32()

        if pointer == 0:
                reader.readInt32()
                pointer = reader.readInt32()
                reader.readInt32()

        if pointer != 5264:
                reader.readBytes(128)

        reader.readBytes(56)

        numOff = reader.offset()
        lnum = reader.readInt32()

        reader.readInt32()

        i = 0 # ???

        arr = []

        while True:
                try:
                        out = strFinder()
                        i += 1
                        if out[2] == b"!!!! LOCALIZATION MISSING !!!!\x00":
                                i -= 1
                        elif out[2].startswith(b'LOC MISSING'):
                                i -= 1
                        else:
                                arr.append(out)
                except struct.error:
                        # print("END")
                        break;

        # just for debugging
        # break;

        # get last, because it's easier
        # and get broken

        try:
                a = arr[-1][2]
        except IndexError:
                a = ""
                print(fileToExtract)
                print(pointerOff1)
                print(fPoint)
                print(numOff)
                print(lnum)

#
# write original strings to loc file
#
# with open(outputYaml, "w") as yaml_file:
#     yaml.dump(output_dict, yaml_file)








