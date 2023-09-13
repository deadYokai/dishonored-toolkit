import os

from pathlib import Path
from binary import BinaryStream
import argparse

def unpack():

    filepath = Path(args.filename)

    if not filepath.is_file():
        raise Exception("File not found")

    # set signature of UPK
    sign_upk = int.from_bytes(bytes([158, 42, 131, 193]))

    outDir = "_DYextracted"

    # open file and create stream
    fileObject = open(filepath, "r+b")
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
        names.append(reader.readBytes(nameLen)) # .decode('utf-8').replace('\x00','')

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
            _e = ".Font"
        if _objType == -3:
            _e = ".ObjectReferencer"
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

    # check if exists folder
    if not os.path.isdir(outDir):
        os.mkdir(outDir)

    # extract header
    reader.seek(0)
    with open(f"{outDir}/_header", "wb") as headerFile:
        headerFile.write(reader.readBytes(headerSize))

    # extract objects
    objid = 0
    for obj in data:
        objFileName = obj["FileName"].decode("utf-8").replace('\x00','')
        objSize = obj["Size"]
        objOffset = obj["Offset"]

        skip = False
        if args.filter != None:
            if objFileName.find(args.filter) == -1:
                skip = True

        if not skip:
            objFileName += f".{objid}"

            p = f"{outDir}/{objFileName}"

            print(f"- {objFileName}\n  size: {objSize}\n  offset: {objOffset}")

            reader.seek(objOffset)
            fileBytes = reader.readBytes(objSize)

            with open(f"{outDir}/_objects.txt", "a") as objFile:
                objFile.write(f"{objFileName}; {objSize}; {objOffset}\n")

            with open(p, "wb") as objFile:
                objFile.write(fileBytes)

        objid += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'UPK Unpacker (Dishonored)', epilog = 'Work in progress')
    parser.add_argument("filename", help = "File to unpack")
    parser.add_argument("-f", "--filter", help = "Filter files by name")
    args = parser.parse_args()
    unpack()










