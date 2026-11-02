import os
import sys
from pathlib import Path


def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)


def _data_dir() -> Path:
    env = os.environ.get("WH_INFO_DATA_DIR")
    if env:
        return Path(env)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "WH_INFO"
    return Path(__file__).resolve().parent / "data"


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = _data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR = DATA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "whinfo.db"

SECRET_KEY = os.environ.get("WH_INFO_SECRET", "whinfo-local-secret-key-2024")
HOST = "127.0.0.1"
PORT = 5001
