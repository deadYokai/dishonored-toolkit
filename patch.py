import os

from pathlib import Path

from binary import BinaryStream
import argparse


def patch():
    # set signature of UPK
    sign_upk = int.from_bytes(bytes([158, 42, 131, 193]))


    filepath = Path(args.filename)

    if not filepath.is_file():
        raise Exception("File not found")


    outDir = "_DYextracted"

    # open file and create stream
    fileObject = open(args.filename, "r+b")
    reader = BinaryStream(fileObject)

    # read signature from file
    sign = reader.readUInt32()

    # check UPK signature
    if sign != sign_upk:
        raise Exception("Is not UE3 UPK file")


    # get some info and move
    pkgVersion = reader.readInt16()
    pkgLVersion = reader.readInt16()
    headerSize = reader.readInt32()
    folderLen = reader.readInt32()
    folderStr = reader.readBytes(folderLen)
    pkgFlags = reader.readInt32()
    nameCount = reader.readInt32()
    nameOffset = reader.readInt32()
    exportCount = reader.readInt32()
    exportOffset = reader.readInt32()
    importCount = reader.readInt32()
    importOffset = reader.readInt32()
    dependsOffset = reader.readInt32()

    somedata1 = reader.readInt32() # equals to headerSize

    # check if all ok
    if headerSize != somedata1:
        raise Exception("Something wrong...")

    # UNKNOWN DATA
    reader.readInt32()
    reader.readInt32()
    reader.readInt32()
    #

    guid = [reader.readInt32(), reader.readInt32(), reader.readInt32(), reader.readInt32()]
    genCount = reader.readInt32()

    genArr = []

    for i in range(genCount):
        genArr.append({"ExportCount": reader.readInt32(), "NameCount": reader.readInt32(), "NetObjectCount": reader.readInt32()})

    engineVer = reader.readInt32()
    cookerVer = reader.readInt32()
    compressionFlags = reader.readInt32()

    # create list for NameTable
    reader.seek(nameOffset)
    names = []
    for i in range(nameCount):
        nameLen = reader.readInt32()
        q = reader.readBytes(nameLen)
        names.append(q)

        # UNKNOWN DATA
        reader.readInt32()
        reader.readInt32()
        #


    # create list for Exports
    reader.seek(exportOffset)
    exports = []
    for i in range(exportCount):
        export = {
            "ObjType": reader.readInt32(),
            "ParentClassRef": reader.readInt32(),
            "OwnerRef": reader.readInt32(),
            "NameListIdx": reader.readInt32(),
            "Field5": reader.readInt32(),
            "Field6": reader.readInt32(),
            "PropertyFlags": reader.readInt32(),
            "Field8": reader.readInt32(),
            "ObjectFileSizeOff": reader.offset(),
            "ObjectFileSize": reader.readInt32(),
            "DataOffsetOff": reader.offset(),
            "DataOffset": reader.readInt32(),
            "Field11": reader.readInt32(),
            "NumAdditionalFields": reader.readInt32(),
            "Field13": reader.readInt32(),
            "Field14": reader.readInt32(),
            "Field15": reader.readInt32(),
            "Field16": reader.readInt32(),
            "Field17": reader.readInt32()
        }
        uf = []
        for j in range(export["NumAdditionalFields"]):
            uf.append(reader.readInt32())

        export["UnknownFields"] = uf

        exports.append(export)

    # create list for Imports
    reader.seek(importOffset)
    imports = []
    for i in range(importCount):
        _import = {
            "PackageID": reader.readInt32(),
            "unknown1": reader.readInt32(),
            "ObjType": reader.readInt32(),
            "unknown2": reader.readInt32(),
            "OwnerRef": reader.readInt32(),
            "NameListIdx": reader.readInt32(),
            "unknown3": reader.readInt32()
        }
        imports.append(_import)

    print(f"Package version: {pkgVersion}")
    print(f"Package License version: {pkgLVersion}")
    print(f"Engine version: {engineVer}")
    print(f"Cooker version: {cookerVer}")

    data = []
    print(f"Objects:")

    # just for print and format to data list
    for e in exports:
        _objName = names[e["NameListIdx"]]
        _objSize = e["ObjectFileSize"]
        _objOffset = e["DataOffset"]
        _objType = e["ObjType"]
        _objSizeOff = e["ObjectFileSizeOff"]
        _objOffOff = e["DataOffsetOff"]
        _e = ""

        if _objType == -1:
            _e = ".Package"
        if _objType == -2:
            _e = ".ObjectReferencer"
        if _objType == -3:
            _e = ".SwfMovie"
        if _objType == -4:
            _e = ".Texture2D"

        filename = _objName
        _object = {
            "FileName": filename,
            "Type": _objType,
            "Size": _objSize,
            "Offset": _objOffset,
            "SizeOff": _objSizeOff,
            "DataOff": _objOffOff,
        }
        data.append(_object)

    dataOff = 0
    dataSize = 0

    files = Path("_DYpatched").glob('*.*_patched')

    for pfile in files:
        oid = int(str(pfile).split(".")[1].split("_")[0])
        obj = data[oid]
        objFileName = obj["FileName"].decode('utf-8').replace('\x00','')
        print(objFileName)
        objSize = obj["Size"]
        objOffset = obj["Offset"]

        if objFileName != str(pfile.stem):
            raise Exception("Wrong filename")

        dataOff = objOffset
        fileSize = os.stat(args.filename).st_size

        reader.seek(0)
        dataBefore = reader.readBytes(objOffset)
        reader.seek(objOffset + objSize)
        dataAfter = reader.readBytes(fileSize - reader.offset())

        iSize = os.stat(pfile).st_size

        dataSize = iSize - objSize
        print(dataSize)
        with open(str(args.filename) + "_patched", "wb") as pf:
            pr = BinaryStream(pf)
            pr.writeBytes(dataBefore)

            with open(pfile, "rb") as f:
                pr.writeBytes(f.read())

            pr.writeBytes(dataAfter)

            pr.seek(obj["SizeOff"])
            pr.writeInt32(iSize)
            pr.seek(obj["DataOff"])
            print(objOffset + dataSize)
            pr.writeInt32(objOffset + dataSize)

            print(f"- {objFileName}\n  size: {objSize}\n  offset: {objOffset}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'UPK Patcher (Dishonored), uses files from folder "_DYpatched"', epilog = 'Work in progress')
    parser.add_argument("filename", help = "File to patch (saves as <filename>_patched in folder with file)")
    args = parser.parse_args()
    patch()




