![Forks](https://img.shields.io/github/forks/deadYokai/dishonored-toolkit?style=social) ![Stargazers](https://img.shields.io/github/stars/deadYokai/dishonored-toolkit?style=social)

<br/>
<p align="center">
  <h3 align="center">Dishonored Mod Toolkit</h3>

  <p align="center">
    I wrote tools to facilitate game modding
    <br/>
    <br/>
  </p>
</p>


## About The Project

At first I just wanted to replace the fonts, which I couldn't do because of manual work, which caused a lot of errors.

Therefore, to simplify, I made this project. And I replaced the fonts.

But there was another problem - subtitles. And to replace the subtitles, I had to expand this project.

Therefore, I am posting this project here in the hope that it will be useful to someone.

## Used Libs (Pypi)

* [configparser](https://pypi.org/project/configparser/)
* [PyYAML](https://pypi.org/project/PyYAML/)
* [cchardet](https://pypi.org/project/cchardet/)

## Usage

**WARNING:** Before working through these tools, you need to decompress a upk files.  [Unreal Package Decomressor](https://www.gildor.org/downloads)

#### File Structure:

**_DYextracted:** `ObjectName.ObjectId`

**_DYpatched:** `ObjectName.ObjectId_patched`

**_objects.txt:** `ObjectName.ObjectId; ObjectSize; ObjectOffset`

#### Unpack

```bash
python3 unpack.py -f <filter> upkfile
```

Example: `python3 unpack.py -f Blurb ../L_Tower_Script.upk`

#### Patch

```bash
python3 patch.py upkfile
```

Example: `python3 patch.py ../L_Tower_Script.upk`

**Notice:** files `_header` and `_objects.txt` not uses in patcher

#### ___

I will write something more here

## Acknowledgements

* [Dishonored font replace (JP)](https://awgsfoundry.com/blog-entry-549.html)
* [UPK File Format - Nexusmods wiki](https://wiki.nexusmods.com/index.php/UPK_File_Format_-_XCOM:EU_2012)
* [UPK File Format - Nexusmods forum](https://forums.nexusmods.com/index.php?/topic/1254328-upk-file-format/)

