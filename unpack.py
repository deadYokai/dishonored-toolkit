import os

from pathlib import Path
from binary import BinaryStream
import argparse

from upkCompressor import DYCompressor
from upkreader import readerGet

def unpack(filepath, namefilter=None, split=False, silent=False, dry=False):

    rr = readerGet(filepath, silent, split)

    reader = rr["reader"]
    imports = rr["imports"]
    exports = rr["exports"]
    data = rr["data"]
    outDir = rr["dir"]
    headerSize = rr["headerSize"]

    # extract objects
    if not silent:
        print(f"Objects:")

    if not dry:
        # check if exists folder
        os.makedirs(outDir, exist_ok=True)

        if os.path.isfile(f"{outDir}/_objects.txt"):
            os.remove(f"{outDir}/_objects.txt")

        # extract header
        reader.seek(0)
        with open(f"{outDir}/_header", "wb") as headerFile:
            headerFile.write(reader.readBytes(headerSize))

    objid = 0
    for obj in data:
        objFileName = obj["FileName"].decode("utf-8").replace('\x00','')
        objSize = obj["Size"]
        objOffset = obj["Offset"]
        objHeaderOff = obj["DataOff"]
        objHeaderSize = obj["SizeOff"]
        objType = obj["Type"]

        skip = False
        if namefilter != None:
            if objFileName.find(namefilter) == -1:
                skip = True

        objFileName += f".{objid}"
        if not skip:
            p = f"{outDir}/{objFileName}.{objType}"

            if not silent:
                print(f"- {objFileName}\n  type: {objType}\n  size: {objSize}\n  offset: {objOffset}")

            reader.seek(objOffset)
            fileBytes = reader.readBytes(objSize)

            if not dry:
                with open(p, "wb") as objFile:
                    objFile.write(fileBytes)


        if not dry:
            with open(f"{outDir}/_objects.txt", "a") as objFile:
                objFile.write(f"{objFileName}.{objType}; {objHeaderSize}; {objSize}; {objHeaderOff}; {objOffset}\n")

        objid += 1
    if not dry:
        with open(f"{outDir}/_names.txt", "w") as namesFile:
            for l in rr["names"]:
                namesFile.write(l.decode("ISO-8859-1").replace("\x00", "") + "\n")
    return rr

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'UPK Unpacker (Dishonored)', epilog = 'Work in progress')
    parser.add_argument("filename", help = "File to unpack")
    parser.add_argument("-f", "--filter", help = "Filter files by name")
    parser.add_argument("--split", help = "Create dir in _DYextracted", default=False, action = argparse.BooleanOptionalAction)
    parser.add_argument("--dry-run", help = "Run without changes", default=False, action = argparse.BooleanOptionalAction)
    args = parser.parse_args()
    fp = Path(args.filename)
    unpack(fp, args.filter, dry=args.dry_run, split=args.split)










