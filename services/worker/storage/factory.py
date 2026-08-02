from config.settings import STORAGE_TYPE
from storage.local import LocalStorageBackend


def get_storage():
    if STORAGE_TYPE == "local":
        return LocalStorageBackend()

    raise ValueError(f"Unsupported STORAGE_TYPE: {STORAGE_TYPE}")
