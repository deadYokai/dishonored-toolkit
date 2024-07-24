import struct
import sys
import os
from types import NoneType

from binary import BinaryStream

class UpkElements:

    def __init__(self, names, reader):
        self.names = names
        self.namesCount = len(names)
        self.reader = reader
        self.endOffset = 0
        self.reader.seek(0, os.SEEK_END)
        self.fileSize = self.reader.offset()
        self.reader.seek(0)
        self.elements = dict()
        self.elementsOffsets = dict()
        self.genNames()

    def setParam(self, paramName, paramValue, strEnc = "ISO-8859-1"):
        if not paramName in self.names:
            return False

        if paramValue == '' or paramValue.strip():
            paramValue = None
        

        paramType = self.elements[paramName]["type"]
        if paramType == "ByteProperty":
            if paramValue == None:
                return False
            paramValue = bytes.fromhex(paramValue)
        elif (paramType == "IntProperty") and (not isinstance(paramValue, int)):
            if paramValue == None:
                return False
            paramValue = struct.pack("I", 4) + struct.pack("i", int(paramValue))
        elif paramType == "StrProperty":
            if paramValue == None or (not isinstance(paramValue, str)):
                return False
            l = len(paramValue) + 1
            ad = b'\x00'
            if strEnc == "UTF-16":
                l = l * -2
                ad += b'\x00'
            l = struct.pack("i", l)
            paramValue = l + paramValue.encode(strEnc) + ad
            
        
        o = self.elementsOffsets[paramName]
        self.reader.seek(o)

        return True

    def getName(self, i):
        n = i
        if i >= 0 and i < self.namesCount:
            n = self.names[i]
        if n == "None":
            if self.reader.offset() < self.fileSize - 8:
                i = self.reader.readInt64()
            else:
                i = self.reader.readInt32()

            if i > len(self.names):
                return {"name": "None", "type": "None"}
            elif self.names[i] == "None" or i == 0:
                return {"name": "None", "type": "None"}

            n = self.names[i]
        nn = self.reader.readUInt64()
        if self.reader.offset() < self.fileSize - 8 and nn < self.namesCount:
            nt = self.names[nn]
        else:
            nt = n
        return {"name": n, "type": nt}

    def resolve(self, str):
        if str == "StructProperty":
            return self.resolveStruct()
        if str == "BoolProperty":
            return self.resolveBool()
        if str == "IntProperty":
            return self.resolveInt()
        if str == "StrProperty":
            return self.resolveStr()
        if str == "ArrayProperty":
            return self.resolveArr()
        if str == "ObjectProperty":
            return self.resolveObj()
        if str == "FloatProperty":
            return self.resolveFloat()
        if str == "ByteProperty":
            return self.resolveByte()
        if str == "NameProperty":
            return self.resolveName()
        
        return None, -1

    def resolveName(self):
        self.reader.readUInt64()
        valoff = self.reader.offset()
        a = self.names[self.reader.readUInt64()]
        return a, valoff

    def resolveByte(self):
        valoff = self.reader.offset()
        return self.reader.readBytes(8).hex(), valoff

    def resolveFloat(self):
        self.reader.readInt64()
        valoff = self.reader.offset()
        return self.reader.readFloat(), valoff

    def resolveArr(self):
        self.reader.readInt64() # unknown
        valoff = self.reader.offset()
        len = self.reader.readUInt32()
        arr = []
        for i in range(len):
            iInt = self.reader.readInt64()
            if (self.namesCount < iInt) or (iInt == 0):
                self.reader.seek(self.reader.offset() - 8)
                arr.append(self.reader.readBytes(4).hex())
            else:
                n = self.getName(iInt)
                arr.append({n["name"]: self.resolve(n["type"])})
        return arr, valoff

    def resolveObj(self):
        self.reader.readInt64()
        valoff = self.reader.offset()
        objBytes = self.reader.readInt32()
        if objBytes < self.namesCount:
            return self.names[objBytes], valoff
        return objBytes, valoff

    def resolveStr(self):
        unknown = self.reader.readInt64()
        strOff = self.reader.offset()
        stringLen = self.reader.readInt32()
        if stringLen == 0:
            return '', strOff
        enc = "ISO-8859-1"
        if stringLen < 0:
            stringLen = stringLen * -2
            enc = "UTF-16"
        string = self.reader.readBytes(stringLen).decode(enc)
        return [string, strOff, strOff + stringLen + 4], strOff

    def resolveInt(self):
        intSize = self.reader.readInt64()
        valoff = self.reader.offset()
        if intSize == 4:
            return self.reader.readInt32(), valoff
        if intSize == 8:
            return self.reader.readInt64(), valoff
        
        return self.reader.readBytes(intSize), valoff

    def resolveBool(self):
        self.reader.readInt64()
        valoff = self.reader.offset()
        if self.reader.readByte() == '\x00':
            return "False", valoff
        return "True", valoff

    def resolveStruct(self):
        structSize = self.reader.readInt64()
        valoff = self.reader.offset()
        structName = self.names[self.reader.readInt64()]
        return [structName, self.reader.readBytes(structSize).hex()], valoff

    def genNames(self):
        self.reader.readBytes(4)
        while self.reader.offset() < self.fileSize:
            po = self.reader.offset()
            if self.reader.offset() < self.fileSize - 8:
                i = self.reader.readInt64()
            else:
                i = self.reader.readInt32()
            self.endOffset = self.reader.offset()
            n = self.getName(i)
            name = n["name"]
            nameType = n["type"]
            # print(self.reader.offset())
            # print(name)
            # print(nameType)
            if nameType == "None":
                break
            dat = self.resolve(nameType)
            self.elements[name] = {"type": nameType, "value": dat[0], "valoff": dat[1]}
            self.elementsOffsets[name] = po

    def resolveLang(self, offset):
        if offset >= self.fileSize - 8:
            return [{"Count": 0, "langs": {}}]
        self.reader.seek(offset)
        lNum = 1
        langs = []
        if 'm_Choices_Static' in self.elements:
            lNum = len(self.elements['m_Choices_Static']['value'])
        for l in range(lNum):
            count = self.reader.readUInt32()
            ll = dict()
            flang = ''
            for i in range(count):
                langCode = self.reader.readUInt64()
                if langCode == 0:
                    langCode = self.reader.readUInt64()
                lang = self.names[langCode]
                if i == 0:
                    flang = lang
                k = True
                string = []
                while k:
                    strOff = self.reader.offset()
                    stringLen = self.reader.readInt32()
                    if stringLen == 0:
                        string.append([strOff, '', strOff + stringLen + 4])
                        k = False
                        break
                    else:
                        enc = "ISO-8859-1"
                        if stringLen < 0:
                            stringLen = stringLen * -2
                            enc = "UTF-16"
                        string.append([strOff, self.reader.readBytes(stringLen).decode(enc), strOff + stringLen + 4])
                    pointer = self.reader.offset()
                    if self.reader.offset() >= self.fileSize - 4:
                        k = False
                        break
                    

                    p = self.reader.readBytes(4)
                    p2 = self.reader.readBytes(4)
                    if self.fileSize == self.reader.offset():
                        k = False
                        break
                    u32 = struct.unpack("I", p)[0]

                    if u32 == count:
                        testLang = struct.unpack("I", p2)[0]
                        if testLang < self.namesCount:
                            if self.names[testLang] == flang:
                                k = False
                                self.reader.seek(self.reader.offset() - 8)
                                break
                    u64 = struct.unpack("Q", p + p2)[0]

                    # Just debug strings
                    # print("__")
                    # print(self.reader.offset())
                    # print(lang + "::" + str(langCode))
                    # print(stringLen)
                    # print(u32)
                    # print(u64)

                    q = 0
                    if (u32 == 0) and (u64 != 0):
                        self.reader.seek(pointer + 4)
                        u64 = self.reader.readUInt64()
                        pointer += 4
                        q = -4

                    if u64 < self.namesCount:
                        k = False
                    
                    if u64 == 0:
                        pointer += 8 + q
                    self.reader.seek(pointer)
                ll[lang] = string
            langs.append({"Count": count, "langs": ll})
        return langs


import traceback
if __name__ == "__main__":
    args = sys.argv[1::]
    with open(args[0], "rb") as f:
        workDir = os.path.dirname(args[0])
        with open(workDir + "/_names.txt", "r") as nf:
            names = nf.read().split("\n")
        try:
            eClass = UpkElements(names, BinaryStream(f))
            print(eClass.elements)
            eClass.setParam("SizeY", "")
            eClass.endOffset
            eClass.resolveLang(eClass.endOffset)
        except Exception:
            print(args[0])
            print(traceback.format_exc())
