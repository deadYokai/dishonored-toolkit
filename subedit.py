import os
from pathlib import Path
from binary import BinaryStream
import yaml
import struct
from unpack import unpack
from patch import patch
from upkElements import UpkElements
import argparse

dir = "_DYextracted"

def unpackYaml(fp, outYaml, lang = None):
    print("\x1b[6;30;42m-- Subtitle extractor --\x1b[0m")

    isINT = False
    if lang == None:
        lang = "INT"

    if lang == "INT":
        isINT = True

    if outYaml is None:
        print("\x1b[6;30;41mErr: output yaml not provided\x1b[0m")
        return

    if not os.path.isdir(dir):
        os.mkdir(dir)

    if os.path.isfile(outYaml):
        os.remove(outYaml)

    upkName = os.path.basename(str(fp)).split('.')[0]

    print(f"Unpacking {upkName}.upk")
    rr = unpack(fp, "DisConv_", True, True)
    types = ('DisConv_Blurb*', 'DisConv_PlayerChoice*', 'DisConv_NonWord*') # the tuple of file types
    files = []
    for fp in types:
        files.extend(Path(f"{dir}/{upkName}").glob(fp))
        

    od = dict()

    for subFile in files:
        name = os.path.basename(subFile)
        with open(subFile, "r+b") as fileObj:
            reader = BinaryStream(fileObj)
            reader.seek(0)
            e = UpkElements(rr["dNames"], reader)
            plChoice = False

            if "m_Choices_Static" in e.elements.keys():
                text = e.elements["m_Choices_Static"]
                plChoice = True
            elif "m_Text" in e.elements.keys():
                text = e.elements["m_Text"]
            else:
                print(f"\x1b[6;30;47mNotice:\x1b[0m {os.path.basename(subFile)} has no text")
                continue

            if isINT:
                textVal = text['value']
                if plChoice:
                    texVal = []
                    for a in range(len(textVal)):
                        textVal = text['value']
                        texVal.append(textVal[a]['m_ChoiceText'][0][0].replace('\x00', '').strip())
                    textVal = texVal
                else:
                    textVal = textVal[0].replace('\x00', '').strip()

                od[name] = textVal
            else:
                langs = e.resolveLang(e.endOffset)
                if langs[0]['Count'] == 0:
                    print(f"\x1b[6;30;47mNotice:\x1b[0m {os.path.basename(subFile)} has no translateble text")
                    continue
                textArr = []
                for l in range(len(langs)):
                    textArr.append(langs[l]['langs'][lang][0][1].replace('\x00','').strip())
                if len(textArr) == 1:
                    textArr = textArr[0]
                od[name] = textArr

    with open(outYaml, "w", encoding="utf8") as yf:
        yaml.dump(od, yf, allow_unicode=True, width=4096)

    print("\x1b[6;30;42m-- Done --\x1b[0m")

def packYaml(fp, inYaml, inp_lang, rep_lang = None):
    print("\x1b[6;30;42m-- Subtitle packer --\x1b[0m")

    if inYaml is None:
        print("\x1b[6;30;41mErr: input yaml not provided\x1b[0m")
        return

    if inp_lang is None:
        inp_lang = "INT"

    isINT = False
    if inp_lang == "INT":
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
    files = Path(f"{dir}/{upkName}").glob('DisConv_*')
    print("Patching Blurb files")
    for subFile in files:
        fileSize = os.stat(subFile).st_size
        name = os.path.basename(subFile)
        if name in yod:
            with open(subFile, "r+b") as fileObj:
                reader = BinaryStream(fileObj)

                reader.seek(0)
                e = UpkElements(rr["dNames"], reader)

                plChoice = False

                if "m_Choices_Static" in e.elements.keys():
                    text = e.elements["m_Choices_Static"]
                    plChoice = True
                elif "m_Text" in e.elements.keys():
                    text = e.elements["m_Text"]
                else:
                    print(f"\x1b[6;30;47mNotice:\x1b[0m {os.path.basename(subFile)} has no text")
                    continue

                fileData = b''
                if isINT:
                    textVal = text['value']
                    reader.seek(0)
                    pStr = yod[name]
                    if plChoice:
                        for a in range(len(textVal)):
                            t = textVal[a]['m_ChoiceText'][0]
                            if a == 0:
                                fileData += reader.readBytes(t[1])
                            eStr = pStr[a].encode("utf-16le")
                            lStr = len(pStr[a]) + 1
                            lStr = lStr * -1
                            eStr += b"\x00\x00"
                            fileData += struct.pack("i", lStr)
                            fileData += eStr
                            reader.seek(t[2])
                            if a == len(textVal)-1:
                                fileData += reader.readBytes(fileSize - reader.offset())
                            else:
                                fileData += reader.readBytes(textVal[a+1]['m_ChoiceText'][1] - reader.offset())
                    else:
                        fileData += reader.readBytes(textVal[1])
                        cutOffset = reader.offset()
                        
                        try:
                            eStr = pStr.encode("ISO-8859-1")
                            lStr = len(pStr) + 1
                            eStr += b"\x00"
                        except:
                            eStr = pStr.encode("utf-16le")
                            lStr = len(pStr) + 1
                            lStr = lStr * -1
                            eStr += b"\x00\x00"
                        
                        fileData += struct.pack("i", lStr)
                        fileData += eStr
                        
                        cutLen = reader.readInt32()
                        if cutLen < 0:
                            cutLen = cutLen * -2
                        reader.readBytes(cutLen)

                        fileData += reader.readBytes(fileSize - reader.offset())

                else:
                    langs = e.resolveLang(e.endOffset)
                    if langs[0]['Count'] == 0:
                        print(f"\x1b[6;30;47mNotice:\x1b[0m {os.path.basename(subFile)} has no translateble text")
                        continue
                    textArr = []
                    for l in range(len(langs)):
                        textArr.append(langs[l]['langs'][inp_lang][0])

                    reader.seek(0)
                    pStr = yod[name]
                    fileData += reader.readBytes(textArr[0][0])
                    for i in range(len(textArr)):
                        if isinstance(pStr, list):
                            eStr = pStr[i].encode("utf-16le")
                            lStr = len(pStr[i]) + 1
                        else:
                            eStr = pStr.encode("utf-16le")
                            lStr = len(pStr) + 1
                        lStr = lStr * -1
                        eStr += b"\x00\x00"
                        fileData += struct.pack("i", lStr)
                        fileData += eStr
                        reader.seek(textArr[i][2])
                        if i == len(textArr)-1:
                            fileData += reader.readBytes(fileSize - reader.offset())
                        else:
                            fileData += reader.readBytes(textArr[i+1][0] - reader.offset())


                newFile = str(subFile).replace("_DYextracted", "_DYpatched") + "_patched"
                if not os.path.isdir(os.path.dirname(newFile)):
                    os.makedirs(os.path.dirname(newFile), exist_ok=True)

                with open(newFile, "wb") as modded:
                    modded.write(fileData)

    print(f"Packing {upkName}.upk")
    patch(fp, False, addDir=upkName, silent=True, end=True)

    if (rep_lang is not None) and (rep_lang != inp_lang):
        with open(str(fp) + "_patched", "rb+") as pf:
            pr = BinaryStream(pf)
            print(f"Replacing '{inp_lang}' to '{rep_lang}'")
            pr.seek(rr["offsetList"]["names"][rr["dNames"].index(inp_lang)])
            pr.writeInt32(len(rep_lang) + 1)
            pr.writeBytes(rep_lang.encode() + b'\x00')

    print("\x1b[6;30;42m-- DONE --\x1b[0m")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dishonored subtitle modifier", epilog="With love <3")
    parser.add_argument("filename", help="UPK file with sutitles (see upklist.db)")
    parser.add_argument("--output", help="Set output yaml file")
    parser.add_argument("--input", help="Set input yaml file")
    parser.add_argument("--langCode", help="LangCode to process")
    parser.add_argument("--langReplace", help="Replace a LangCode to custom")
    args = parser.parse_args()
    fp = Path(os.path.abspath(args.filename))

    if args.input != None and args.output is None:
        packYaml(fp, args.input, args.langCode, args.langReplace)
    else:
        unpackYaml(fp, args.output, args.langCode)
