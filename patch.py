import os

from pathlib import Path
import io
from typing import TypeVar
from binary import BinaryStream
import argparse
import struct
from upkreader import readerGet
from texture2d import Texture2D

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
    rrnames = rr["dNames"]

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

                    if name.split(".")[-1] == "Texture2D":
                        # tmpName = ".tmp.upk.data.file." + name
                        # with open(tmpName, "wb") as tf:
                        #     tf.write(writeData)
                        texBytes = io.BytesIO(writeData)
                        tex2d = Texture2D(texBytes, rrnames)
                        r = tex2d.reader
                        mm = tex2d.mipmaps
                        try:
                            r.seek(tex2d.firstAddress[0])
                        except:
                            print(name)
                            raise
                        r.writeUInt32(offe + r.offset()+4)
                        for m in mm:
                            r.seek(m["offset"]-4)
                            r.writeUInt32(offe + r.offset() + 4)
                        r.seek(0)
                        writeData = r.readBytes(tex2d.datasize)
                        # with open(tmpName, "rb") as tf:
                        #     writeData = tf.read()
                        # os.remove(tmpName)

                    newSize = size + sizeDiff

                    pr.seek(offe)
                    pr.writeBytes(writeData)

                    pr.seek(sizeOff)
                    pr.writeInt32(newSize)

                    pr.seek(headerOff)
                    pr.writeInt32(offe)

                        # bt.seek(0, os.SEEK_END)
                        # bts = bt.tell()
                        # bt.seek(0)
                        # ff = False
                        # while not ff:
                        #     a = struct.unpack("I", bt.read(4))[0]
                        #     if a <= len(rrnames):
                        #         n = rrnames[a].decode("ISO-8859-1")
                        #         if n == "None\x00":
                        #             ff = True
                        #
                        #         if n == "BoolProperty\x00":
                        #             bt.read(1)
                        #
                        #     if bt.tell() > 1024:
                        #         raise TypeError("*censored* -- OUT OF RANGE")
                        #
                        # bt.read(16)
                        # pr.seek(bt.tell() + offe)
                        # pr.writeInt32(pr.offset() + 4)
                        # first = struct.unpack("I", bt.read(4))[0]
                        # limit = bts + offe
                        # while bt.tell() < bts:
                        #     k = struct.unpack("I", bt.read(4))[0]
                        #     if (k < limit) and (k > first):
                        #         bt.seek(bt.tell() - 4)
                        #         break
                        # pr.seek(bt.tell() + offe)
                        # pr.writeInt32(pr.offset() + 4)


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




