import argparse
import os
import yaml

def convert(infile, outdir):
    if outdir is None:
        outdir = os.getcwd()

    if not os.path.isdir(outdir):
        os.mkdir(outdir)

    inDict = dict()
    sortedDict = {}
    
    print("-- Loading file")
    with open(infile, "r") as inyaml:
        inDict = yaml.load(inyaml, Loader=yaml.SafeLoader)

    print("-- Parsing keys")
    for k, v in inDict.items():
        keySplit = k.split("-")
        newKey = keySplit[1] + ".DisConv_Blurb"
        upkName = keySplit[0]
        if upkName not in sortedDict:
            sortedDict[upkName] = {}
        sortedDict[upkName][newKey] = v

    print("-- Writing to files")
    for dk, dv in sortedDict.items():
        path = os.path.join(outdir, (dk + ".yaml"))
        yamlDict = dv
        with open(path, "w", encoding="utf-8") as newYaml:
            yaml.dump(yamlDict, newYaml, allow_unicode=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Converts old yaml style to new (in this workspace)", epilog="May be unsused")
    parser.add_argument("yamlfile", help="Input yaml file")
    parser.add_argument("--output", help="Output dir")
    args = parser.parse_args()

    convert(args.yamlfile, args.output)

