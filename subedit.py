import os
from pathlib import Path
from binary import BinaryStream
import yaml
import struct
import math
from unpack import unpack
from upkCompressor import DYCompressor
import argparse

dir = "_DYextracted"

def strFinder(r):
    off = r.offset()
    ls = r.readInt32()

    while ls == 0:
        h = r.offset()
        off = h
        ls = r.readInt32()

    if ls > 1000:
        r.readInt32()
        off = r.offset()
        ls = r.readInt32()

    is2b = False
    if ls < 0:
        is2b = True
        ls = abs(ls) * 2

    return [off, ls, r.readString(ls), is2b]

def unpackYaml(fp, outYaml):
    print("-- Extracting text from upk")
    if outYaml is None:
        print("Err: output yaml not provided")
        return

    upkFile = str(fp)

    if not os.path.isdir(dir):
        os.mkdir(dir)

    if os.path.isfile(outYaml):
        os.remove(outYaml)

    upkName = os.path.basename(str(fp)).split('.')[0]

    print(f"Unpacking {upkName}.upk")
    unpack(fp, "Blurb", True, True)

    files = Path(f"{dir}/{upkName}").glob('DisConv_Blurb.*')

    od = dict()

    for subFile in files:
        name = os.path.basename(subFile)
        print(f"Processing: {name}", end='\r')
        with open(subFile, "r+b") as fileObj:
            reader = BinaryStream(fileObj)

            seekList = [129, 154, 179]

            for val in seekList:
                reader.seek(val)
                sLen = reader.readInt32()
                if sLen != 0 and sLen > -5000 and sLen < 5000:
                    break

            isUtf16 = False
            try:
                if sLen < 0:
                    isUtf16 = True
                    sLen = abs(sLen) * 2
                text = reader.readBytes(sLen)
            except Exception:
                print(f"File: {subFile}; String Len: {sLen}", end="\n")

            try:
                enc = "utf-8"
                if isUtf16:
                    enc = "utf-16"
                od[name] = text.decode(enc).replace('\x00', '').replace('\n', '').strip()
            except UnicodeDecodeError:
                od[name] = str(text)

    with open(outYaml, "w") as yf:
        yaml.dump(od, yf)

def packYaml(fp, inYaml):
    print("-- Packing text to upk")
    if inYaml is None:
        print("Err: input yaml not provided")
        return

    if not os.path.isfile(inYaml):
        print("Err: input yaml not found")
        return
    
    if not os.path.isdir(dir):
        os.mkdir(dir)
    
    yod = dict()

    with open(inYaml, "r") as yf:
        yod = yaml.load(yf, Loader=yaml.SafeLoader)

    upkName = os.path.basename(str(fp)).split('.')[0]
    print(f"Unpacking {upkName}.upk")
    unpack(fp, "Blurb", True, True)

    files = Path(f"{dir}/{upkName}").glob('DisConv_Blurb.*')
    for subFile in files:
        fileSize = os.stat(subFile).st_size
        name = os.path.basename(subFile)
        if name in yod:
            with open(subFile, "r+b") as fileObj:
                reader = BinaryStream(fileObj)
                
                seekList = [129, 154, 179]
                for val in seekList:
                    reader.seek(val)
                    stringLen = reader.readInt32()
                    if stringLen != 0 and stringLen > -5000 and stringLen < 5000:
                        break
                enc = "utf-8"
                if stringLen < 0:
                    enc = "utf-16le"
                    stringLen = abs(stringLen) * 2
                s = reader.readBytes(stringLen)
                try:
                    s.decode(enc)
                except:
                    break

                reader.seek(reader.offset() + 76)
                # while True:
                #     pointer = reader.readInt32()
                #     try:
                #         if pointer == 1347584:
                #             reader.seek(reader.offset() - 3)
                #             pointer = reader.readInt32()
                #         if pointer == 1347653:
                #             reader.seek(reader.offset() - 3)
                #             pointer = reader.readInt32()
                #     except struct.error:
                #         break
                #
                #     if pointer == 5264 or pointer == 5132:
                #         reader.readInt32()
                #         break
                #
                # if pointer != 5264:
                #     reader.readBytes(92)
                #
                # reader.readBytes(56)
                #
                # numL = reader.readInt32()
                #
                # if numL > 1000:
                #     while True:
                #         numL = reader.readInt32()
                #         if numL > 0 and numL < 1000 and numL != 0:
                #             break
                #
                # if numL == 0:
                #     print("numL == 0")
                #     return
                # 
                # try:
                #     reader.readInt32()
                # except:
                #     pass
                
                i = 0
                arr = []
                while True:
                    try:
                        out = strFinder(reader)
                        i += 1
                        if out[2] == b"!!!! LOCALIZATION MISSING !!!!\x00":
                            i -= 1
                        elif out[2].startswith(b"LOC MISSING"):
                            i -= 1
                        else:
                            arr.append(out)
                    except struct.error:
                        break
                if arr != []:
                    a = arr[-1][2]
                    pStr = yod[name] + "\x00"
                    eStr = pStr.encode("utf-16")[2:]
                    lStr = len(pStr) * -1
                    reader.seek(0)
                    sData = reader.readBytes(arr[-1][0])
                    reader.seek(arr[-1][0] + arr[-1][1] + 4)
                    eData = reader.readBytes(fileSize - reader.offset())
                    newFile = str(subFile).replace("_DYextracted", "_DYpatched")
                    if not os.path.isdir(os.path.dirname(newFile)):
                        os.makedirs(os.path.dirname(newFile), exist_ok=True)
                
                    with open(newFile, "wb") as modded:
                        r = BinaryStream(modded)
                        r.writeBytes(sData)
                        r.writeInt32(lStr)
                        r.writeBytes(eStr)
                        r.writeBytes(eData)
                else:
                    print(f"WARN: No localization on {os.path.basename(subFile)}, skipping")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dishonored subtitle modifier", epilog="With love <3")
    parser.add_argument("filename", help="UPK file with sutitles (see upklist.db)")
    parser.add_argument("--output", help="Set output yaml file")
    parser.add_argument("--input", help="Set input yaml file")
    args = parser.parse_args()
    fp = Path(os.path.abspath(args.filename))

    if args.input != None and args.output is None:
        packYaml(fp, args.input)
    else:
        unpackYaml(fp, args.output)


