from .sd_common import *
from dataclasses import dataclass
from typing import Union


@dataclass
class NfsPoicy:
    access: str = ""
    options: str = ""


@dataclass
class NfsConfig:
    dir: str
    policy: tuple[NfsPoicy]
    disable = False


class NfsService(StorageDeployService):

    def update(self):
        return super().update()

    def apply(self, **kwargs):
        return super().apply(**kwargs)

    def stop(self):
        return super().stop()

    def remove(self):
        return super().remove()
