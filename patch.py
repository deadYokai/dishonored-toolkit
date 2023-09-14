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

        index = f"{filename}.{_objOffset}"

        data.append(_object)

    dataOff = 0
    dataSize = 0

    files = Path("_DYpatched").glob('*.*_patched')

    patchedFiles = []

    for pfile in files:
        oid = int(str(pfile).split(".")[1].split("_")[0])
        oname = str(pfile.stem)
        patchedFiles.append(f"{oname}.{oid}")

    a = True
    with open(str(args.filename) + "_patched", "wb") as pf:
            pr = BinaryStream(pf)

            pr.seek(0)
            if args.patch_header:
                with open(f"{outDir}/_header", "rb") as head:
                    pr.writeBytes(head.read())
            else:
                reader.seek(0)
                pr.writeBytes(reader.readBytes(headerSize))

            offsetDiff = 0
            sizeDiff = 0
            with open(f"{outDir}/_objects.txt", "r") as listfile:
                for line in listfile:
                    odata = line.replace(' ', '').replace('\n','').split(";")
                    name = odata[0]
                    sizeOff = int(odata[1])
                    size = int(odata[2])
                    headerOff = int(odata[3])
                    offset = int(odata[4])

                    b = False
                    if name in patchedFiles:
                        psize = os.stat(f"_DYpatched/{name}_patched").st_size
                        with open(f"_DYpatched/{name}_patched", "rb") as f:
                            sizeDiff = psize - size
                            offsetDiff = offsetDiff + sizeDiff
                            writeData = f.read()
                            b = True
                    else:
                        sizeDiff = 0
                        reader.seek(offset)
                        writeData = reader.readBytes(size)

                    if a and b:
                        a = False
                        print("Patched Objects:")

                    oDiff = offsetDiff

                    if b:
                        print(f"- {name}\n  original size: {size}\n  patched size: {psize}\n  size diff: {sizeDiff}\n  offset: {offe}")
                        oDiff = offsetDiff - sizeDiff

                    offe = offset + oDiff


                    pr.seek(offe)
                    pr.writeBytes(writeData)

                    pr.seek(sizeOff)
                    pr.writeInt32(size + sizeDiff)

                    pr.seek(headerOff)
                    pr.writeInt32(offe)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'UPK Patcher (Dishonored), uses files from folder "_DYpatched"', epilog = 'Work in progress')
    parser.add_argument("filename", help = "File to patch (saves as <filename>_patched in folder with file)")
    parser.add_argument("-p", "--patch-header", default=False, help = "Insert a header file from _DYpatched", action = argparse.BooleanOptionalAction)
    args = parser.parse_args()
    patch()




