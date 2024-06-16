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

            enc = "utf-8"
            if isUtf16:
                enc = "utf-16le"
            try:
                od[name] = text.decode(enc).replace('\x00', '').replace('\n', '').strip()
            except UnicodeDecodeError:
                od[name] = str(text)
                pass

    with open(outYaml, "w") as yf:
        yaml.dump(od, yf)

def recPos(r, fs, names):
    noneIndex = names.index(b'None\x00')
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
    r.seek(of)
    r.readInt32()
    noneByteFind = r.readInt32()
    f = False
    while (noneByteFind != noneIndex) and (f == False):
        r.seek(r.offset() - 1)
        pbyte = r.readByte()
        if pbyte == b'\x00':
            f = True
        noneByteFind = r.readInt32()
 
    of = r.offset() - 4
    return of

def getLangText(r, names):
    iS = False
    i = r.readInt32()
    iOff = r.offset()
    if i == 0:
        while i == 0:
            i = r.readInt32()
            iOff = r.offset()
    k = r.readInt32()
    r.seek(iOff)
    if k != 0:
        while k != 0:
            ll = i
            if i < 0:
                ll = i * -2
            r.readBytes(ll)
            iOff = r.offset()
            i = r.readInt32()
            kk = r.offset()
            k = r.readInt32()
            r.seek(kk)
    nameInt = i
    if i < 0:
        iS = True
        n = "SOME" # just a dummy name in len 4, to skip some debug text
    else:
        try:
            n = names[i].decode("latin1")
        except:
            print("----- Oops")
            print(f"Position: {r.offset()}")
            print(f"Position HEX: {hex(r.offset())}")
            print(f"Int position: {iOff}")
            print(f"Int position HEX: {hex(iOff)}")
            print(f"Int value: {i}")
            print(f"Int value HEX: {hex(i)}")
            t = r.offset()
            print(f"Next 20 bytes: {r.readBytes(20)}")
            r.seek(t - 20)
            print(f"Prev 20 bytes: {r.readBytes(20)}")
            print("-----")
            raise
    if len(n) == 4:
        stroff = r.offset()
        size = i
        if not iS:
            r.readInt32()
            size = r.readInt32()
        enc = "ISO-8859-1"
        if size < 0:
            enc = "utf-16le"
            size = size * -2
        text = r.readBytes(size)
        if n == "SOME": # don't return debug text and find actual Lang
            return getLangText(r, names)
        return [text, enc, stroff, size, nameInt]
    else:
        r.seek(iOff)
        r.readBytes(i)
        return getLangText(r, names)

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
                #print(subFile)
                reader.readBytes(16)
                rp = recPos(reader, fileSize, rr["names"])
                if not rp:
                    continue
                reader.seek(rp + 8)
                count = reader.readUInt32()
                tl = []
                a = 0
                while a < count:
                    t = getLangText(reader, rr["names"])
                    tl.append([t[2], t[0].decode(t[1]), t[3], t[4]])
                    a += 1
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
                    ln = rr["names"][li[3]].decode().replace("\x00", "")
                    if ln == inp_lang:
                        tlIndex = tl.index(li)
                        nameIdx = li[3]
                        break
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


