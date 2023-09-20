import os
from pathlib import Path
from binary import BinaryStream
import yaml
import struct
import math
from unpack import unpack
from upkCompressor import DYCompressor

outputYaml = "en.yaml"

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

def extractSubs(folder=""):

        files = Path(f"_DYextracted").glob('DisConv_Blurb.*')
        if folder != "":
                files = Path(f"_DYextracted/{folder}").glob('DisConv_Blurb.*')

        for fileToExtract in files:
                fileSize = os.stat(fileToExtract).st_size
                pname = os.path.basename(fileToExtract)
                name = f"{folder}-{pname}"
                fileObject = open(fileToExtract, "r+b")
                reader = BinaryStream(fileObject)

                seeklist = [129, 154, 179]

                for val in seeklist:
                        reader.seek(val)
                        stringLen = reader.readInt32()
                        if stringLen != 0 and stringLen > -5000 and stringLen < 5000:
                                break

                isu16 = False
                try:
                        if stringLen < 0:
                                isu16 = True
                                stringLen = abs(stringLen) * 2
                        origText = reader.readBytes(stringLen)
                except Exception:
                        print(f"File: {fileToExtract}; type = {types}; stringLen: {stringLen}", end="\n")

                skip = False
                try:
                        encoding = "utf-8"
                        if isu16:
                                encoding = "utf-16"
                        output_dict[name] = origText.decode(encoding).replace("\x00", "").replace('\n',"").strip()
                except UnicodeDecodeError:
                        skip = True # skip \x88
                        output_dict[name] = str(origText)

                if output_dict[name] == "Follow me, Corvo!":
                        patch = False
                else:
                        patch = False

                skip = True
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
# mass export to yaml -- for my scopes, can be changed in future
#
workdir = "_DYworking"

with open("upklist.db", "r") as Upks:

    if not os.path.isdir(workdir):
        os.mkdir(workdir)

    os.chdir(f'{workdir}')

    if os.path.isfile(outputYaml):
        os.remove(outputYaml)

    for tupk in Upks:
        upk = tupk.replace("\n", "")
        upkname = os.path.basename(upk)

        end = "\r"
        print(f"Processing {upkname}................", end=end)
        unpack(Path(f"unpacked/{upkname}"), "Blurb", True, True)
        extractSubs(upkname.split(".")[0])

        with open(outputYaml, "a") as yaml_file:
                yaml.dump(output_dict, yaml_file)

        output_dict = dict()








