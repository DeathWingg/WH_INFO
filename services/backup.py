import shutil
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from config import DB_PATH, IMAGES_DIR, BACKUPS_DIR


def create_backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = BACKUPS_DIR / f"whinfo_{ts}.zip"
    tmp_db = BACKUPS_DIR / f"_tmp_{ts}.db"

    # backup seguro do SQLite
    src = sqlite3.connect(str(DB_PATH))
    dst = sqlite3.connect(str(tmp_db))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_db, "whinfo.db")
        for f in IMAGES_DIR.glob("*"):
            if f.is_file():
                z.write(f, f"images/{f.name}")
    try:
        tmp_db.unlink()
    except OSError:
        pass
    return out


def list_backups():
    return sorted(
        (p for p in BACKUPS_DIR.glob("whinfo_*.zip")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def restore_backup(zip_path: str) -> None:
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        if "whinfo.db" not in names:
            raise ValueError("Backup inválido: whinfo.db não encontrado")

        if DB_PATH.exists():
            shutil.copy2(
                DB_PATH, BACKUPS_DIR / f"pre_restore_{datetime.now():%Y%m%d_%H%M%S}.db"
            )

        with z.open("whinfo.db") as src, open(DB_PATH, "wb") as dst:
            shutil.copyfileobj(src, dst)

        for name in names:
            if name.startswith("images/") and not name.endswith("/"):
                target = IMAGES_DIR / Path(name).name
                with z.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
