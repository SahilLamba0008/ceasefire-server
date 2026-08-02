from pathlib import Path
import shutil

from config.settings import STORAGE_ROOT
from storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, root=STORAGE_ROOT):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, key):
        return self.root / key

    def save(self, key, data):
        destination = self._resolve_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(data), str(destination))
        return key

    def exists(self, key):
        return self._resolve_path(key).exists()

    def delete(self, key):
        path = self._resolve_path(key)
        if path.exists():
            path.unlink()