import logging
import subprocess
import shutil
from io import StringIO
from pathlib import Path
from string import Template
from dataclasses import dataclass, fields
from typing import Optional, Union
from .sd_common import *

logger = logging.getLogger(__name__)
SYSTEMD_SERVICE_DIR = Path("/etc/systemd/system/")
MOUNTS_TOML_EXAMPLE = """
[[mounts]]
desc = "example"
what = "UUID=2ebdaf8a-2dee-4812-9c86-525d9b742ff2"
where = "/opt"
options = "nofail,rw,relatime,compress=zstd,subvol=opt"
target = "local-fs"
disable = true
"""


@dataclass
class MountConfig:
    what: str = ""
    where: str = ""
    type: Optional[str] = None
    options: Optional[str] = None
    target: Optional[str] = None
    desc: Optional[str] = None
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
        fstype_str = output.decode(encoding="utf-8").strip()
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
                if isinstance(fs_type, Exception):
                    logger.warning(
                        f"fstype maybe mismatch. {fs_type}")
                return "auto"
            case _:
                if self.type != fs_type and isinstance(fs_type, ValueError):
                    raise fs_type
                return self.type

    def get_what(self) -> str:
        if len(self.what) == 0:
            raise ValueError("Empty `what` field for mount device")
        return self.what

    def get_where(self) -> str:
        if len(self.where) == 0:
            raise ValueError("Empty `where` field for mount point")
        return str(Path(self.where).absolute())

    def get_target(self) -> str:
        if self.target is None or len(self.target) == 0:
            return "multi-user.target"
        elif not self.target.endswith(".target"):
            return f"{self.target}.target"
        else:
            return self.target

    def gen_service(self) -> str:
        w = StringIO()
        w.write("[Unit]\n")
        if self.desc:
            w.write(f"Description={self.desc}; {DECLARE}\n")
        else:
            w.write(f"Description={DECLARE}\n")
        w.write("\n[Mount]\n")
        w.write(f"What={self.get_what()}\n")
        w.write(f"Where={self.get_where()}\n")
        w.write(f"Type={self.get_type()}\n")
        if self.options:
            w.write(f"Options={self.options}\n")

        wanted_by = self.get_target()
        w.write("\n[Install]\n")
        if wanted_by:
            w.write(f"WantedBy={wanted_by}\n")

        return w.getvalue()


class MountService(StorageDeployService):
    @staticmethod
    def arg_flag() -> str:
        return "mnt"

    @staticmethod
    def __service_dir_rename(dir_name: str) -> str:
        return dir_name.replace(" ", "\\x20").replace("-", "\\x2d")

    def __clean_mount_service(self, only_stop=False):
        for mount_service in SYSTEMD_SERVICE_DIR.glob("*.mount"):
            if mount_service.is_symlink():
                mount_service_path = mount_service.resolve()
                if is_subdirectory(self.config_target_dir, mount_service_path):
                    if only_stop:
                        logger.info(f"service stop: {mount_service}")
                        systemctl("stop", mount_service.name)
                    else:
                        logger.info(
                            f"service stop and disable: {mount_service}")
                        systemctl("stop", mount_service.name)
                        systemctl("disable", mount_service.name)
                        logger.info(f"unlink: {mount_service_path}")
                        if mount_service.exists():
                            # systemctl disable will remove service automatically
                            mount_service.unlink()

    def __link_mount_service(self):
        for mount_service in self.service_target_dir.glob("*.mount"):
            mount_service = mount_service.absolute()
            target_service = SYSTEMD_SERVICE_DIR.joinpath(
                mount_service.name).absolute()
            if target_service.exists():
                logger.info(f"service stop and disable: {target_service}")
                systemctl("stop", target_service.name)
                systemctl("disable", target_service.name)
                logger.info(f"backup: {target_service}")
                shutil.move(
                    target_service, self.service_backup_dir.joinpath(target_service.name))
            elif target_service.is_symlink():
                target_service.unlink()
            logger.info(f"link: {target_service} → {mount_service}")
            target_service.symlink_to(mount_service)
            logger.info(f"service start and enable: {target_service}")
            systemctl("start", target_service.name)
            systemctl("enable", target_service.name)

    def __init__(self, cfg: dict, config_target_dir: Path) -> None:
        super().__init__(cfg, config_target_dir)
        self.service_target_dir = config_target_dir / "mount_service"
        self.service_backup_dir = config_target_dir / "mount_backup"
        self.service_backup_dir.mkdir(exist_ok=True)

    def toml(self, w: StringIO):
        cfgs: list[dict] = self.cfg.get("mounts", None)
        if cfgs is None or len(cfgs) == 0:
            w.write(MOUNTS_TOML_EXAMPLE)
        else:
            for cfg in cfgs:
                w.write(f"\n[[mounts]]\n")
                for field in fields(MountConfig):
                    field_content = cfg.get(field.name, None)
                    if field_content is None:
                        continue
                    w.write(f'{field.name} = {toml_gen_elem(field_content)}\n')
        return super().toml(w)

    def update(self):
        self.__clean_mount_service()
        if self.service_target_dir.exists():
            shutil.rmtree(self.service_target_dir)
        self.service_target_dir.mkdir()
        mounts_cfg = self.cfg.get("mounts", [])
        for mount_cfg in mounts_cfg:
            cfg = MountConfig(**mount_cfg)
            if cfg.disable:
                continue
            where_parents = Path(cfg.where).absolute().parts[1:]
            where_parents = list(
                map(MountService.__service_dir_rename, where_parents))
            service_name = "-".join(where_parents) + ".mount"
            mount_service_path = self.service_target_dir / service_name
            with open(mount_service_path, mode="wt") as f:
                logger.info(f"update: {mount_service_path}")
                f.write(cfg.gen_service())

    def apply(self, **kwargs):
        self.__link_mount_service()
        return super().apply()

    def stop(self):
        self.__clean_mount_service(only_stop=True)
        return super().stop()

    def remove(self):
        self.__clean_mount_service()
        for backup_service in self.service_backup_dir.glob("*.mount"):
            target_service = SYSTEMD_SERVICE_DIR.joinpath(backup_service.name)
            if target_service.exists():
                logger.warning(
                    f"recovery service already exists: {target_service}")
            else:
                logger.info(f"recovery: {target_service}")
                shutil.move(backup_service, target_service)
        return super().remove()
