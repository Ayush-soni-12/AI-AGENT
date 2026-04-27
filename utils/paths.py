from pathlib import Path



def resolve_path(base : str | Path,path : str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p.resolve()
    return (Path(base) / p).resolve()


def is_binary_file(path :str| Path) -> bool:
    try:
        with open(path, "rb") as f:
           chunk =  f.read(8192)
           return b"\x00" in chunk
    except Exception:
        return False