import os
from os.path import basename
from pathlib import Path
from binary import BinaryStream
import yaml
import struct
import math
from unpack import unpack
from patch import patch
from upkCompressor import DYCompressor
import argparse
import re
import operator

dir = "_DYextracted"

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
    rr = unpack(fp, "Blurb", True, True)

    files = Path(f"{dir}/{upkName}").glob('DisConv_Blurb.*')

    od = dict()

    for subFile in files:
        name = os.path.basename(subFile)
        print(f"Processing: {name}", end='\r')
        with open(subFile, "r+b") as fileObj:
            reader = BinaryStream(fileObj)

            seekList = [129, 154, 179]

            reader.seek(36)

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

def recPos(r, fs):
    if r.offset() + 8 >=fs:
        return False

    q = True
    o = r.offset()
    p = 0

    while q:
        if r.offset() + 16 >=fs:
            q = False

        a = []
        k = []

        for i in range(3):
            a.append(r.readInt32())
            k.append(r.offset())

        r.seek(r.offset() - 11)

        if a == [0, 4, 0]:
            p = max(k)

    of = p
    #print(of)
    return of

def getLangText(r, fs):
    if r.offset() + 8 >=fs:
        return [False, None, "utf-8"]
    langCode = r.readInt32()
    if langCode == 0:
        langCode = r.readInt32()
    stroff = r.offset()
    skip = False
    enc = "latin1"
    if r.readInt32() != 0:
        r.seek(stroff)
        len = langCode
        skip = True
    else:
        len = r.readInt32()
    if len < 0:
        enc = "utf-16"
        len = abs(len) * 2
    stroff = r.offset() - 4
    text = r.readBytes(len)
    if re.search("LOC.* MISSING", text.decode(enc)):
        skip = True
    return [skip, text, enc, stroff, len, langCode]

def packYaml(fp, inYaml, inp_lang, rep_lang = None):
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
    rr = unpack(fp, "Blurb", True, True)
    nameIdx = -1
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

                reader.readBytes(16)
                rp = recPos(reader, fileSize)
                if not rp:
                    continue
                reader.seek(rp + 12)
                count = reader.readUInt32()
                tl = []
                a = 0
                while a < count:
                    t = getLangText(reader, fileSize)
                    if t[0]:
                        a -= 1
                    elif t[1] is not None:
                        tl.append([t[3], t[1].decode(t[2]), t[4], t[5]])
                        a += 1
                    else:
                        break
                if tl == []:
                    continue
                pStr = yod[name]
                eStr = pStr.encode("utf-16le")
                lStr = len(pStr) + 1
                lStr = lStr * -1
                eStr += b"\x00\x00"
                reader.seek(0)
                tlIndex = -1

                for li in tl:
                    if rr["names"][li[3]].decode().replace("\x00", "") == inp_lang:
                        tlIndex = tl.index(li)
                        nameIdx = li[3]
                sData = reader.readBytes(tl[tlIndex][0])
                reader.seek(reader.offset() + tl[tlIndex][2] + 8)
                eData = reader.readBytes(fileSize - reader.offset())
                newFile = str(subFile).replace("_DYextracted", "_DYpatched") + "_patched"
                if not os.path.isdir(os.path.dirname(newFile)):
                    os.makedirs(os.path.dirname(newFile), exist_ok=True)
            
                with open(newFile, "wb") as modded:
                    r = BinaryStream(modded)
                    r.writeBytes(sData)
                    r.writeInt32(lStr)
                    r.writeBytes(eStr)
                    r.writeInt32(0)
                    r.writeBytes(eData)

    patch(fp, False, addDir=upkName, silent=True)

    with open(str(fp) + "_patched", "rb+") as pf:
        pr = BinaryStream(pf)
        if (rep_lang is not None) and (rep_lang != inp_lang):
            pr.seek(rr["offsetList"]["names"][nameIdx])
            pr.writeInt32(len(rep_lang) + 1)
            pr.writeBytes(rep_lang.encode() + b'\x00')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dishonored subtitle modifier", epilog="With love <3")
    parser.add_argument("filename", help="UPK file with sutitles (see upklist.db)")
    parser.add_argument("--output", help="Set output yaml file")
    parser.add_argument("--input", help="Set input yaml file")
    parser.add_argument("--langCode", help="LangCode to replace")
    parser.add_argument("--langReplace", help="Replace a LangCode to custom")
    args = parser.parse_args()
    fp = Path(os.path.abspath(args.filename))

    if args.input != None and args.output is None:
        packYaml(fp, args.input, args.langCode, args.langReplace)
    else:
        unpackYaml(fp, args.output)


