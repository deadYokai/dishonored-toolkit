import os

from binary import BinaryStream

def extract(fileToExtract, out):

        # open file and create stream
        fileSize = os.stat(fileToExtract).st_size
        fileObject = open(fileToExtract, "r+b")
        reader = BinaryStream(fileObject)

        reader.readBytes(20)

        offOffset = reader.offset()
        offset = reader.readInt32()

        reader.readInt32()

        offCharNum = reader.offset()
        charNum = reader.readInt32()

        offCharTable = reader.offset()
        charTableSize = offset - offCharTable

        if not os.path.isdir(out):
                os.mkdir(out)

        with open(f"{out}/tempfile1", "wb") as temp:
                data = reader.offset()
                reader.seek(0)
                temp.write(reader.readBytes(data))

        with open(f"{out}/charTable", "wb") as objFile:
                objFile.write(reader.readBytes(charTableSize))

        part2 = reader.offset()
        reader.readBytes(228)

        fontNameSize = reader.readInt32()
        fontName = reader.readBytes(fontNameSize)

        # SOME BYTES AFTER
        reader.readBytes(44)

        dataSize = reader.readInt32()
        print(dataSize)
        reader.readInt32()
        reader.readInt32()

        reader.readBytes(dataSize)

        reader.readInt32()

        unknownOffset = reader.readInt32()+1

        reader.readBytes(unknownOffset)
        reader.readInt32()
        reader.readInt32()

        offCharNum2 = reader.offset()
        charNum2 = reader.readInt32()
        print(charNum2)
        if charNum2 != charNum:
                raise Exception("Something wrong...")

        reader.readBytes(1024)

        with open(f"{out}/offsets.txt", "w") as temp:
                temp.write(f"{offCharTable};{offCharNum2}")

        with open(f"{out}/tempfile2", "wb") as temp:
                data = reader.offset()
                reader.seek(part2)
                temp.write(reader.readBytes(data - part2))

        endData = reader.readBytes(fileSize - reader.offset())

        with open(f"{out}/endData", "wb") as temp:
                temp.write(endData)

# print(endData)

extract("origFiles/ChaletComprime-CologneEighty.Font", "_DYorigTemp")

# extract("moddedFiles/Emerge_BF.Font", "_DYmodTemp")

### PACKING NEW FILE






















