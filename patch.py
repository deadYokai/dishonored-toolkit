import os

from pathlib import Path

from binary import BinaryStream
import argparse
from upkreader import readerGet


def patch():

    filepath = Path(args.filename)

    rr = readerGet(filepath)

    reader = rr["reader"]
    imports = rr["imports"]
    exports = rr["exports"]
    data = rr["data"]
    outDir = rr["dir"]
    headerSize = rr["headerSize"]

    dataOff = 0
    dataSize = 0

    files = Path("_DYpatched").glob('*.*_patched')

    patchedFiles = []

    for pfile in files:
        oid = int(str(pfile).split(".")[1])
        otype = str(pfile).split(".")[2].split("_")[0]
        oname = str(pfile.stem.split(".")[0])
        patchedFiles.append(f"{oname}.{oid}.{otype}")

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




