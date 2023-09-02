import os
from pathlib import Path
from binary import BinaryStream
import yaml
import struct
import math

outputYaml = "en.yaml"
files = Path("_DYextracted").glob('DisConv_Blurb.*')
output_dict = dict()

patch = False

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

        if types == b"\xe6":
                reader.seek(154)
        else:
                reader.seek(179)

        stringLen = reader.readInt32()

        origText = reader.readBytes(stringLen)

        skip = False
        try:
                output_dict[name] = origText.decode("utf-8").replace("\x00", "")
        except UnicodeDecodeError:
                skip = True # skip \x88
                output_dict[name] = str(origText)

        if output_dict[name] == "Follow me Corvo!":
                patch = True
        else:
                patch = False

        if not skip:
                while True:
                        try:
                                pointerOff1 = reader.offset().to_bytes(2, "big")
                                pointer = reader.readInt32()
                                if pointer == 1347584:
                                        pointerOff1 = reader.offset().to_bytes(2, "big")
                                        reader.seek(reader.offset() - 3)
                                        pointer = reader.readInt32()
                                if pointer == 1347653:
                                        pointerOff1 = reader.offset().to_bytes(2, "big")
                                        reader.seek(reader.offset() - 3)
                                        pointer = reader.readInt32()
                        except struct.error:
                                print(fileToExtract)
                                break;
                        if pointer == 5264 or pointer == 5132:
                                reader.readInt32()
                                break

                if pointer != 5264:
                        reader.readBytes(92)

                reader.readBytes(56)

                fPoint  = pointer
                numOff = reader.offset().to_bytes(2, "big")
                lnum = reader.readInt32()

                if lnum > 1000:
                        while True:
                                lnum = reader.readInt32()
                                if lnum > 0 and lnum < 1000 and lnum != 0:
                                        break;

                # check if this has a translations
                if lnum != 0:
                        try:
                                reader.readInt32()
                        except:
                                pass
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
                                if patch:
                                        print(fileToExtract)
                                        print(a)
                                        print(len(a))
                                        rstr = "Сюди, Корво!".encode("utf-16")[2:]
                                        print(arr[-1][0])
                                        rlen = math.ceil(len(rstr)/2) * -1
                                        print(len(rstr)/2)
                                        reader.seek(0)
                                        startdata = reader.readBytes(arr[-1][0])
                                        reader.seek(arr[-1][0] + arr[-1][1] + 4)
                                        otherdata = reader.readBytes(fileSize - reader.offset())
                                        path = str(fileToExtract).replace("_DYextracted", "_DYpatched") + "_patched"

                                        if not os.path.isdir("_DYpatched"):
                                                os.mkdir("_DYpatched")

                                        with open(path, "wb") as patched:
                                                ps = BinaryStream(patched)
                                                ps.writeBytes(startdata)
                                                ps.writeInt32(rlen)
                                                ps.writeBytes(rstr)
                                                ps.writeBytes(otherdata)
                                        # r.writeInt32(rlen)
                                        # r.writeBytes(rstr)
                        except IndexError:
                                a = ""
                                # print(fileToExtract)
                                # print(pointerOff1)
                                # print(fPoint)
                                # print(numOff)
                                # print(lnum)

#
# write original strings to loc file
#
# with open(outputYaml, "w") as yaml_file:
    # yaml.dump(output_dict, yaml_file)








