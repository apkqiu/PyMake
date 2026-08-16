import glob as _glob


def glob(pattern: str):
    return _glob.iglob(pattern, recursive=True)


def extract_file_name(name: str):
    r = name.rfind(".")
    if r == -1:
        r = len(name)
    l = name.find("/") + 1
    return name[l:r]

n = extract_file_name