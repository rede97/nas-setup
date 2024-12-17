import os
import subprocess
from pathlib import Path
from string import Template
from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class MountConfig:
    what: str = ""
    where: str = ""
    type: Optional[str] = None
    options: Optional[str] = None
    target: Optional[str] = None
    disable: bool = False

    @staticmethod
    def __lookup_dev_by_uuid(uuid: str) -> Optional[Path]:
        cmd = f"blkid -U {uuid}"
        output = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE).stdout
        dev_path_str = output.decode(encoding="utf-8").strip()
        if len(dev_path_str) != 0:
            return Path(dev_path_str)
        return None

    @staticmethod
    def __lookup_fstype_by_dev(dev: Path) -> Optional[str]:
        output = subprocess.run(
            f"blkid -s TYPE --output value {dev.absolute()}", shell=True, stdout=subprocess.PIPE).stdout
        fstype_str = output.decode(encoding="utf-8")
        if len(fstype_str) != 0:
            return fstype_str
        return None

    def __get_type(self) -> Union[str, Exception]:
        if self.what.startswith("UUID="):
            uuid = self.what.removeprefix("UUID=")
            dev_path = self.__lookup_dev_by_uuid(uuid)
            if dev_path is None:
                return ValueError(f"cannot find device by uuid: {uuid}")
        else:
            dev_path = Path(self.what)
        if dev_path.exists():
            fstype = self.__lookup_fstype_by_dev(dev_path)
            if fstype is None:
                return ValueError(f"Unknown fstype, device: {dev_path}")
            return fstype
        else:
            return FileExistsError(
                "Invalid `what` field to get fstype automatic, only local device is supported")

    def get_type(self) -> str:
        fs_type = self.__get_type()
        match self.type:
            case None:
                if isinstance(fs_type, str):
                    return fs_type
                raise fs_type
            case "" | "auto":
                if isinstance(fs_type, str):
                    return self.type
                print(f"Warning, fstype maybe invalid. {fs_type}")
            case _:
                if self.type != fs_type and isinstance(fs_type, ValueError):
                    raise fs_type
                return self.type
        return self.type

    def get_where(self) -> str:
        if self.where is None or len(self.where) == 0:
            raise ValueError("Invalid `where` for mount point")
        return str(Path(self.where).absolute())

    def get_target(self) -> str:
        if self.target is None:
            return ""
        elif not self.target.endswith(".target"):
            return f"{self.target}.target"
        else:
            return self.target


def __service_dir_rename(dir_name: str) -> str:
    return dir_name.replace(" ", "\\x20").replace("-", "\\x2d")


def gen_mount_service(cfg: MountConfig, target_dir: Path) -> Optional[str]:
    if cfg.disable:
        return None
    cfg.get_type()
    where_parents = Path(cfg.where).absolute().parts[1:]
    where_parents = list(map(__service_dir_rename, where_parents))
    
    
    return "-".join(where_parents) + ".mount"


def update_config(mounts: list[dict], target_path: Path, start=False, enable=False, enable_param: Optional[str] = None):
    for mount_cfg in mounts:
        print(mount_cfg)
        cfg = MountConfig(**mount_cfg)
        service_name = gen_mount_service(cfg, target_path)
        print(service_name)
