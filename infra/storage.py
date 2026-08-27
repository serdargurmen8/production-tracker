"""
infra/storage.py
------------------
JSON dosyaları okuma/yazma yardımcıları.
Zaman aşımı (timeout) korumalıdır, asla donma ve kilitlenme yapmaz.
"""

import json
import os
from contextlib import contextmanager
from filelock import FileLock, Timeout


def _lock_path(path: str) -> str:
    return path + ".lock"


def json_read(path: str, default):
    """
    Dosyayı kilit beklemesi olmadan doğrudan okur.
    Asla takılmaz veya sayfayı dondurmaz.
    """
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


@contextmanager
def json_write(path: str, default):
    """
    Dosyaya yazarken maksimum 1 saniye kilit bekler.
    Kilit takılı kalsa bile akışı dondurmadan yazmayı tamamlar.
    """
    dir_name = os.path.dirname(path) or "."
    os.makedirs(dir_name, exist_ok=True)

    lock = FileLock(_lock_path(path), timeout=1.0)

    try:
        with lock:
            data = default
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = default

            yield data

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Timeout:
        # Kilit dosyası asılı kalmışsa kilitsiz doğrudan yaz
        data = default
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = default

        yield data

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)