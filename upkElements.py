import struct
import sys
import os

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
        self.genNames()

    def getName(self, i):
        n = self.names[i]
        if n == "None":
            if self.reader.offset() < self.fileSize - 8:
                i = self.reader.readInt64()
            else:
                i = self.reader.readInt32()

            if i > len(self.names):
                return {"name": "None", "type": "None"}
            n = self.names[i]
        if self.reader.offset() < self.fileSize - 8:
            nt = self.names[self.reader.readInt64()] 
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

    def resolveByte(self):
        return self.reader.readBytes(8).hex()

    def resolveFloat(self):
        self.reader.readInt64()
        return self.reader.readFloat()

    def resolveArr(self):
        self.reader.readInt64() # unknown
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
        return arr

    def resolveObj(self):
        self.reader.readInt64()
        someName = self.names[self.reader.readInt32()]
        return someName

    def resolveStr(self):
        unknown = self.reader.readInt64()
        strOff = self.reader.offset()
        stringLen = self.reader.readInt32()
        if stringLen == 0:
            return ''
        enc = "ISO-8859-1"
        if stringLen < 0:
            stringLen = stringLen * -2
            enc = "UTF-16"
        string = self.reader.readBytes(stringLen).decode(enc)
        return [string, strOff, self.reader.offset()]

    def resolveInt(self):
        intSize = self.reader.readInt64()
        if intSize == 4:
            return self.reader.readInt32()
        if intSize == 8:
            return self.reader.readInt64()
        
        return self.reader.readBytes(intSize)

    def resolveBool(self):
        self.reader.readInt64()
        if self.reader.readByte() == '\x00':
            return "False"
        return "True"

    def resolveStruct(self):
        structSize = self.reader.readInt64()
        structName = self.names[self.reader.readInt64()]
        return [structName, self.reader.readBytes(structSize).hex()]

    def genNames(self):
        self.reader.readBytes(4)
        while self.reader.offset() < self.fileSize:
            if self.reader.offset() < self.fileSize - 8:
                i = self.reader.readInt64()
            else:
                i = self.reader.readInt32()
            self.endOffset = self.reader.offset()
            n = self.getName(i)
            name = n["name"]
            nameType = n["type"]
            # print(name)
            # print(nameType)
            if nameType == "None":
                break
            self.elements[name] = {"type": nameType, "value": self.resolve(nameType)}

    def resolveLang(self, offset):
        self.reader.seek(offset)
        lNum = 1
        langs = []
        if 'm_Choices_Static' in self.elements:
            lNum = len(self.elements['m_Choices_Static']['value'])
        for l in range(lNum):
            count = self.reader.readUInt32()
            ll = dict()
            for i in range(count):
                langCode = self.reader.readUInt64()
                if langCode == 0:
                    langCode = self.reader.readUInt64()
                lang = self.names[langCode]
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
                    u64 = struct.unpack("Q", p + p2)[0]

                    # Just debug strings
                    # print("__")
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



if __name__ == "__main__":
    args = sys.argv[1::]
    with open(args[0], "rb") as f:
        workDir = os.path.dirname(args[0])
        with open(workDir + "/_names.txt", "r") as nf:
            names = nf.read().split("\n")

        eClass = UpkElements(names, BinaryStream(f))
        print(eClass.elements)
        print(eClass.endOffset)
        print(eClass.resolveLang(eClass.endOffset))
