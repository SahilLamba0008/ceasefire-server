from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key, data):
        raise NotImplementedError

    @abstractmethod
    def exists(self, key):
        raise NotImplementedError

    @abstractmethod
    def delete(self, key):
        raise NotImplementedError
