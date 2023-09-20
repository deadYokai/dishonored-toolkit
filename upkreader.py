import os

from pathlib import Path
from binary import BinaryStream
import argparse

from upkCompressor import DYCompressor
 
def readerGet(filepath, silent=False, split=False):
    if not filepath.is_file():
        raise Exception("File not found")

    # set signature of UPK
    sign_upk = int.from_bytes(bytes([158, 42, 131, 193]))

    ff = filepath.stem
    outDir = "_DYextracted"
    if split:
        outDir = f"{outDir}/{ff}"

    # open file and create stream
    fileObject = open(filepath, "r+b")
    reader = BinaryStream(fileObject)

    # read signature from file
    sign = reader.readUInt32()

    # check UPK signature
    if sign != sign_upk:
        raise Exception("Signature mismatch")


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

    if importCount <= 0 or exportCount <= 0 or nameCount <= 0:
        raise Exception("Invalid or corrupted package")

    importOffset = reader.readInt32()
    dependsOffset = reader.readInt32()

    somedata1 = reader.readInt32() # equals to headerSize

    # check if all ok
    # if headerSize != somedata1:
        # raise Exception(f"Something wrong...\nat {ff}")

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

    compressor = DYCompressor(compressionFlags)

    ctype = compressor.getCompression()

    if not silent:
        print(f"Package version: {pkgVersion}")
        print(f"Package License version: {pkgLVersion}")
        print(f"Engine version: {engineVer}")
        print(f"Cooker version: {cookerVer}")
        print(f"Compression: {ctype}")

    if ctype != "None":
        raise Exception("Compressed files not support yet\nPlease use Unreal Package Decompressor")

        #
        # Trying to decompress
        #
        # chunksnum = reader.readInt32()
        #
        # fname = filepath.stem
        #
        # if not os.path.isdir("_DYuncompressed"):
        #     os.mkdir("_DYuncompressed")
        #
        # with open(f"_DYuncompressed/{fname}.upk", "wb") as unfile:
        #     # for chunk in range(chunksnum):
        #     uOffset = reader.readInt32()
        #     uSize = reader.readInt32()
        #     cOffset = reader.readInt32()
        #     cSize = reader.readInt32()
        #
        #     reader.seek(cOffset)
        #     dataChunk = compressor.unpackLZO(reader)


    # raise Exception("BREAK")

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

    names.append("NULL")

    # create list for Exports
    reader.seek(exportOffset)
    exports = []
    for i in range(exportCount):
        export = {
            "ObjTypeRef": reader.readInt32(),
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
            "ObjTypeIdx": reader.readInt32(),
            "unknown2": reader.readInt32(),
            "OwnerRef": reader.readInt32(),
            "NameListIdx": reader.readInt32(),
            "unknown3": reader.readInt32()
        }
        imports.append(_import)

    data = []

    # just for print and format to data list
    for e in exports:
        _objName = names[e["NameListIdx"]]
        _objSize = e["ObjectFileSize"]
        _objOffset = e["DataOffset"]
        _objType = e["ObjTypeRef"]
        _objSizeOff = e["ObjectFileSizeOff"]
        _objOffOff = e["DataOffsetOff"]
        _e = ""

        if _objType < 0:
            _objType = names[imports[-_objType-1]["NameListIdx"]].decode("utf-8").replace("\x00", "")
        elif _objType > 0:
            _objType = names[exports[_objType-1]["NameListIdx"]].decode("utf-8").replace("\x00", "") # not tested yet
        else:
            _objType = "NULL"

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

    data.sort(key=lambda item: item["Offset"])

    return {"reader": reader, "data": data, "imports": imports, "exports": exports, "dir": outDir, "headerSize": headerSize}




