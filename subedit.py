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

def findElem(reader, names, elementName):
    startPos = reader.offset()
    reader.seek(0, os.SEEK_END)
    fs = reader.offset()
    reader.seek(startPos)
    found = -1
    while reader.offset() < fs-3:
        e = reader.readUInt32()
        if e < len(names):
            name = names[e].decode("ISO-8859-1").replace("\x00", '')
            if name == "BoolProperty":
                reader.readByte()

            if name == "StrProperty":
                reader.readInt32()
                k = reader.readUInt64()
                size = reader.readInt32()
                val = reader.readBytes(size)

            if name == elementName:
                found = reader.offset()
                break

    return found

def unpackYaml(fp, outYaml):
    print("\x1b[6;30;42m-- Subtitle extractor --\x1b[0m")

    if outYaml is None:
        print("\x1b[6;30;41mErr: output yaml not provided\x1b[0m")
        return

    if not os.path.isdir(dir):
        os.mkdir(dir)

    if os.path.isfile(outYaml):
        os.remove(outYaml)

    upkName = os.path.basename(str(fp)).split('.')[0]

    print(f"Unpacking {upkName}.upk")
    rr = unpack(fp, "DisConv", True, True)

    files = Path(f"{dir}/{upkName}").glob('DisConv_*')

    od = dict()

    for subFile in files:
        name = os.path.basename(subFile)
        with open(subFile, "r+b") as fileObj:
            reader = BinaryStream(fileObj)

            dataType = reader.readUInt32()
            if dataType == 0:
                dataType = reader.readUInt32()
            if rr["names"][dataType] == b"m_iBlurbGUID\x00":
                m_TextPos = findElem(reader, rr["names"], "m_Text")
                if m_TextPos == -1:
                    print(f"\x1b[6;30;47mNotice:\x1b[0m {os.path.basename(subFile)} has no text")
                    continue
                reader.seek(m_TextPos)
                reader.readInt32()
                reader.readInt64()
                reader.readInt64()
                intStrLen = reader.readInt32()
                enc = "ISO-8859-1"
                if intStrLen < 0:
                    enc = "utf-16le"
                    intStrLen = intStrLen * -2
                s = reader.readBytes(intStrLen)

                try:
                    od[name] = s.decode(enc).replace('\x00', '').replace('\n', '').strip()
                except:
                    print(f"File: {subFile}; String Len: {intStrLen}", end="\n")
            elif rr["names"][dataType] == b"m_Choices_Static\x00":
                findElem(reader, rr["names"], "ArrayProperty")
                reader.readInt32()
                reader.readUInt64() # some unknown???
                arrLen = reader.readUInt32()
                text = []
                for i in range(arrLen):
                    if rr["names"][reader.readUInt32()] == b"m_ChoiceText\x00":
                        reader.readBytes(20)
                        intStrOff = reader.offset()
                        intStrLen = reader.readInt32()
                        enc = "ISO-8859-1"
                        if intStrLen < 0:
                            enc = "utf-16le"
                            intStrLen = intStrLen * -2
                        intStr = reader.readBytes(intStrLen)
                        text.append(intStr.decode(enc).replace('\x00', '').replace('\n', '').strip())
                        reader.readBytes(8)
                od[name] = text
    with open(outYaml, "w", encoding="utf8") as yf:
        yaml.dump(od, yf, allow_unicode=True)

    print("\n\x1b[6;30;42m-- Done --\x1b[0m")

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
            n = names[i].decode("ISO-8859-1")
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
        size = i
        if not iS:
            r.readInt32()
            size = r.readInt32()
        stroff = r.offset()-4
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
    print("\x1b[6;30;42m-- Subtitle packer --\x1b[0m")

    if inYaml is None:
        print("\x1b[6;30;41mErr: input yaml not provided\x1b[0m")
        return

    if inp_lang is None:
        inp_lang = "INT"

    isINT = False
    if inp_lang == "INT":
        print("\x1b[6;30;43mWARNING: NOT TESTED FEATURE (using INT)\x1b[0m")
        isINT = True

    if not os.path.isfile(inYaml):
        print("\x1b[6;30;41mErr: input yaml not found\x1b[0m")
        return

    if not os.path.isdir(dir):
        os.mkdir(dir)

    yod = dict()

    with open(inYaml, "r", encoding="utf8") as yf:
        yod = yaml.load(yf, Loader=yaml.SafeLoader)

    upkName = os.path.basename(str(fp)).split('.')[0]
    print(f"Unpacking {upkName}.upk")
    rr = unpack(fp, "DisConv", True, True)
    nameIdx = -1
    files = Path(f"{dir}/{upkName}").glob('DisConv_*')
    print("Pathing Blurb files")
    for subFile in files:
        fileSize = os.stat(subFile).st_size
        name = os.path.basename(subFile)
        if name in yod:
            with open(subFile, "r+b") as fileObj:
                reader = BinaryStream(fileObj)
                dataType = reader.readUInt32()
                if dataType == 0:
                    dataType = reader.readUInt32()
                if rr["names"][dataType] == b"m_iBlurbGUID\x00":
                    continue
                    m_TextPos = findElem(reader, rr["names"], "m_Text")
                    if m_TextPos == -1:
                        print(f"\x1b[6;30;47mNotice:\x1b[0m {os.path.basename(subFile)} has no text")
                        continue
                    reader.seek(m_TextPos)
                    reader.readInt32()
                    reader.readInt64()
                    reader.readInt64()
                    intStrOff = reader.offset()
                    intStrLen = reader.readInt32()
                    enc = "ISO-8859-1"
                    if intStrLen < 0:
                        enc = "utf-16le"
                        intStrLen = intStrLen * -2
                    s = reader.readBytes(intStrLen)

                    try:
                        s = s.decode(enc)
                    except:
                        if isINT:
                            raise Exception("\x1b[6;30;41mErr: Something wrong happened at INT Lang\x1b[0m")
                        break

                    if not isINT:
                        m_iSpeakerPos = findElem(reader, rr["names"], "m_iSpeaker")
                        if m_iSpeakerPos == -1:
                            raise Exception(f"\x1b[6;30;41mErr:\x1b[0m m_iSpeaker not found in {os.path.basename(subFile)}")
                        findElem(reader, rr["names"], "IntProperty")
                        findElem(reader, rr["names"], "None")
                        reader.readInt32()
                        count = reader.readUInt32()
                        if rr["names"][count] == b'None\x00':
                            reader.readInt32()
                            count = reader.readUInt32()
                        if count == 0:
                            if fileSize != reader.offset():
                                raise
                            print(f"\x1b[6;30;47mNotice:\x1b[0m {os.path.basename(subFile)} has no translateble text")
                            continue
                        tl = []
                        for a in range(count):
                            t = getLangText(reader, rr["names"])
                            tl.append([t[2], t[0].decode(t[1]), t[3], t[4]])
                        if tl == []:
                            raise Exception("\x1b[6;30;41mErr: Something wrong at LangFinder\x1b[0m")
                        pStr = yod[name]
                        eStr = pStr.encode("utf-16le")
                        lStr = len(pStr) + 1
                        lStr = lStr * -1
                        eStr += b"\x00\x00"

                        tlIndex = -1

                        for i in range(len(tl)):
                            ln = rr["names"][tl[i][3]].decode().replace("\x00", "")
                            if ln == inp_lang:
                                tlIndex = i
                                nameIdx = tl[i][3]
                                break
                        reader.seek(0)
                        sData = reader.readBytes(tl[tlIndex][0])
                        reader.seek(tl[tlIndex][0] + tl[tlIndex][2] + 4)
                    else:
                        reader.seek(0)
                        sData = reader.readBytes(intStrOff)
                        pStr = yod[name]
                        eStr = pStr.encode("utf-16le")
                        lStr = len(pStr) + 1
                        lStr = lStr * -1
                        eStr += b"\x00\x00"
                        reader.seek(intStrOff + intStrLen + 4)

                    eData = reader.readBytes(fileSize - reader.offset())
                    newFile = str(subFile).replace("_DYextracted", "_DYpatched") + "_patched"
                    if not os.path.isdir(os.path.dirname(newFile)):
                        os.makedirs(os.path.dirname(newFile), exist_ok=True)

                    with open(newFile, "wb") as modded:
                        r = BinaryStream(modded)
                        r.writeBytes(sData)
                        r.writeInt32(lStr)
                        r.writeBytes(eStr)
                        r.writeBytes(eData)


                elif rr["names"][dataType] == b"m_Choices_Static\x00":
                    findElem(reader, rr["names"], "ArrayProperty")
                    reader.readInt32()
                    reader.readUInt64() # some unknown???
                    arrLen = reader.readUInt32()
                    text = []
                    for i in range(arrLen):
                        if rr["names"][reader.readUInt32()] == b"m_ChoiceText\x00":
                            reader.readBytes(20)
                            intStrOff = reader.offset()
                            intStrLen = reader.readInt32()
                            enc = "ISO-8859-1"
                            if intStrLen < 0:
                                enc = "utf-16le"
                                intStrLen = intStrLen * -2
                            intStr = reader.readBytes(intStrLen)
                            text.append([intStrOff, intStrLen, intStr])
                            reader.readBytes(8)

                    fileData = b''
                    if not isINT:
                        m_iSpeakerPos = findElem(reader, rr["names"], "m_pOwner")
                        if m_iSpeakerPos == -1:
                            raise Exception(f"\x1b[6;30;41mErr:\x1b[0m m_pOwner not found in {os.path.basename(subFile)}")
                        findElem(reader, rr["names"], "ObjectProperty")
                        findElem(reader, rr["names"], "None")
                        reader.readInt32()
                        langs = []
                        for i in range(arrLen):
                            count = reader.readUInt32()
                            if rr["names"][count] == b'None\x00':
                                reader.readInt32()
                                count = reader.readUInt32()
                            if count == 0:
                                if fileSize != reader.offset():
                                    raise
                                print(f"\x1b[6;30;47mNotice:\x1b[0m {os.path.basename(subFile)} has no translateble text")
                                continue
                            tl = []
                            for a in range(count):
                                t = getLangText(reader, rr["names"])
                                tl.append([t[2], t[0].decode(t[1]), t[3], t[4]])
                            if tl == []:
                                raise Exception("\x1b[6;30;41mErr: Something wrong at LangFinder\x1b[0m")
                            langs.append(tl)
                        for q in range(len(langs)):
                            pStr = yod[name][q]
                            eStr = pStr.encode("utf-16le")
                            lStr = len(pStr) + 1
                            lStr = lStr * -1
                            eStr += b"\x00\x00"
                            tlIndex = -1
                            tl = langs[q]
                            for i in range(len(tl)):
                                ln = rr["names"][tl[i][3]].decode().replace("\x00", "")
                                if ln == inp_lang:
                                    tlIndex = i
                                    nameIdx = tl[i][3]
                                    break
                            if q == 0:
                                reader.seek(0)
                                fileData += reader.readBytes(tl[tlIndex][0]) # from start file
                            
                            reader.seek(tl[tlIndex][0] + tl[tlIndex][2] + 4) # Offset + Size + Int32 string len
                            if q < len(langs) - 1:
                                eDataSize = langs[q+1][tlIndex][0] - reader.offset()
                            else:
                                eDataSize = fileSize - reader.offset()

                            fileData += struct.pack("i", lStr) + eStr
                            fileData += reader.readBytes(eDataSize)
                    
                    else:
                        for q in range(len(text)):
                            pStr = yod[name][q]
                            eStr = pStr.encode("utf-16le")
                            lStr = len(pStr) + 1
                            lStr = lStr * -1
                            eStr += b"\x00\x00"

                            if q == 0:
                                reader.seek(0)
                                fileData += reader.readBytes(text[q][0])

                            reader.seek(text[q][0] + text[q][1] + 4)

                            if q < len(text) - 1:
                                eDataSize = text[q+1][0] - reader.offset()
                            else:
                                eDataSize = fileSize - reader.offset()
                            
                            fileData += struct.pack("i", lStr) + eStr
                            fileData += reader.readBytes(eDataSize)

                    newFile = str(subFile).replace("_DYextracted", "_DYpatched") + "_patched"
                    if not os.path.isdir(os.path.dirname(newFile)):
                        os.makedirs(os.path.dirname(newFile), exist_ok=True)

                    with open(newFile, "wb") as modded:
                        modded.write(fileData)

    print(f"Packing {upkName}.upk")
    patch(fp, False, addDir=upkName, silent=True)

    if (rep_lang is not None) and (rep_lang != inp_lang):
        with open(str(fp) + "_patched", "rb+") as pf:
            pr = BinaryStream(pf)
            print(f"Replacing '{inp_lang}' to '{rep_lang}'")
            pr.seek(rr["offsetList"]["names"][nameIdx])
            pr.writeInt32(len(rep_lang) + 1)
            pr.writeBytes(rep_lang.encode() + b'\x00')

    print("\x1b[6;30;42m-- DONE --\x1b[0m")

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
