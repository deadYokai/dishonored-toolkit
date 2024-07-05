import sys
import os

from binary import BinaryStream

class UpkElements:

    def __init__(self, names, reader):
        self.names = names
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


    def resolveArr(self):
        arrByteLen = self.reader.readInt64() # unknown
        len = self.reader.readUInt32()
        arr = []
        for i in range(len):
            n = self.getName(self.reader.readInt64())
            arr.append({n["name"]: self.resolve(n["type"])})
        return arr

    def resolveObj(self):
        self.reader.readInt64()
        someName = self.names[self.reader.readInt32()]
        return someName

    def resolveStr(self):
        unknown = self.reader.readInt64()
        stringLen = self.reader.readInt32()
        if stringLen == 0:
            return ''
        enc = "ISO-8859-1"
        if stringLen < 0:
            stringLen = stringLen * -2
            enc = "UTF-16"
        return self.reader.readBytes(stringLen).decode(enc)

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
                lang = self.names[langCode]
                k = True
                string = []
                while k:
                    stringLen = self.reader.readInt32()
                    if stringLen == 0:
                        string.append('')
                    else:
                        enc = "ISO-8859-1"
                        if stringLen < 0:
                            stringLen = stringLen * -2
                            enc = "UTF-16"
                        string.append(self.reader.readBytes(stringLen))
                    pointer = self.reader.offset()
                    if self.reader.offset() >= self.fileSize - 4:
                        k = False
                        break
                    if self.reader.readInt32() != 0:
                        k = False
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
        print(eClass.resolveLang(eClass.endOffset))
