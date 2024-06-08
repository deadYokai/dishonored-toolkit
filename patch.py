import os

from pathlib import Path

from binary import BinaryStream
import argparse
from upkreader import readerGet


def patch(filepath, ph, addDir = None, silent=False):
    
    sp = False
    if addDir is not None:
        sp = True
    rr = readerGet(filepath, silent=silent, split=sp)

    reader = rr["reader"]
    imports = rr["imports"]
    exports = rr["exports"]
    data = rr["data"]
    outDir = rr["dir"]
    headerSize = rr["headerSize"]

    dataOff = 0
    dataSize = 0

    if addDir is not None:
        files = Path(f"_DYpatched{os.sep}{addDir}").glob('*.*_patched')
    else:
        files = Path("_DYpatched").glob('*.*_patched')

    patchedFiles = []

    for pfile in files:
        oid = int(str(pfile).split(".")[1])
        ot = str(pfile).split(".")[2].split("_")[:-1]
        otype = '_'.join(ot)
        oname = str(pfile.stem.split(".")[0])
        patchedFiles.append(f"{oname}.{oid}.{otype}")


    a = True
    with open(str(filepath) + "_patched", "wb") as pf:
            pr = BinaryStream(pf)

            pr.seek(0)
            if ph:
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
                        tmpPath = f"_DYpatched/"
                        if addDir is not None:
                            tmpPath += f"{addDir}/"
                        tmpPath += f"{name}_patched"


                        psize = os.stat(tmpPath).st_size
                        with open(tmpPath, "rb") as f:
                            writeData = f.read()
                            sizeDiff = psize - size
                            offsetDiff = offsetDiff + sizeDiff
                            b = True
                    else:
                        sizeDiff = 0
                        reader.seek(offset)
                        writeData = reader.readBytes(size)

                    if a and b:
                        a = False
                        if not silent:
                            print("Patched Objects:")

                    oDiff = offsetDiff

                    if b:
                        oDiff = offsetDiff - sizeDiff

                    offe = offset + oDiff

                    if (not silent) and b:
                        print(f"- {name}\n  original size: {size}\n  patched size: {psize}\n  size diff: {sizeDiff}\n  offset: {offe}")

                    pr.seek(offe)
                    pr.writeBytes(writeData)

                    pr.seek(sizeOff)
                    pr.writeInt32(size + sizeDiff)

                    pr.seek(headerOff)
                    pr.writeInt32(offe)

                    if name.split(".")[-1] == "Texture2D":
                        pr.seek(offe + 281)
                        pr.writeInt32(pr.offset() + 4)
                        pr.seek(pr.offset() + 16)
                        pr.writeInt32(pr.offset() + 4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'UPK Patcher (Dishonored), uses files from folder "_DYpatched"', epilog = 'Work in progress')
    parser.add_argument("filename", help = "File to patch (saves as <filename>_patched in folder with file)")
    parser.add_argument("-p", "--patch-header", default=False, help = "Insert a header file from _DYpatched", action = argparse.BooleanOptionalAction)
    parser.add_argument("-s", "--split", default=False, help = "Get patched files from _DYpatched/<upk name>", action = argparse.BooleanOptionalAction)
    args = parser.parse_args()
    ad = None
    if args.split:
        ad = '.'.join(os.path.basename(args.filename).split(".")[::-1][-1::])
    patch(Path(args.filename), args.patch_header, ad)




