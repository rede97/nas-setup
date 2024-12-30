import shutil
import logging
from io import StringIO
from typing import Any
from dataclasses import dataclass
from .sd_common import *

logger = logging.getLogger(__name__)
UDEVIL_CONFIG_PATH = Path("/etc/udevil/udevil.conf")
UDEVIL_SERVICE_NAME = "devmon@{0}.service"


@dataclass
class UdevilConfig:
    user: str = ""
    config: str = ""
    disable: bool = False


class UdevilService(StorageDeployService):
    @staticmethod
    def arg_flag() -> str:
        return "udevil"

    def __init__(self, cfg: dict, config_target_dir: Path) -> None:
        super().__init__(cfg, config_target_dir)
        self.config_target_path = self.config_target_dir / "udevil_config/udevil.conf"
        self.config_backup_path = config_target_dir / "udevil_backup/udevil.conf"
        self.config_target_path.parent.mkdir(exist_ok=True)
        self.config_backup_path.parent.mkdir(exist_ok=True)
        self.udevil_config = UdevilConfig(**self.cfg.get("udevil", {}))
        self.udevil_service_name = UDEVIL_SERVICE_NAME.format(self.udevil_config.user)

    def toml(self, w: StringIO):
        uidevil_config: dict[str, Any] = self.cfg.get("udevil", {})
        if len(uidevil_config) == 0:
            uidevil_config["user"] = "test"
            cfg = trim_general_config_file(UDEVIL_CONFIG_PATH, comment={"#"}).get(
                None, ""
            )
            uidevil_config["config"] = cfg
        toml_gen_elem_table(w, uidevil_config, f"udevil")
        return super().toml(w)

    def update(self):
        with open(self.config_target_path, mode="wt") as f:
            logger.info(f"update: {self.config_target_path}")
            f.write(self.udevil_config.config)
        return super().update()

    def apply(self, **kwargs):
        if self.udevil_config.disable:
            return
        self.stop()
        if UDEVIL_CONFIG_PATH.exists():
            if UDEVIL_CONFIG_PATH.is_symlink():
                logger.info(f"unlink: {UDEVIL_CONFIG_PATH}")
                UDEVIL_CONFIG_PATH.unlink()
            else:
                logger.info(f"backup: {UDEVIL_CONFIG_PATH}")
                shutil.move(UDEVIL_CONFIG_PATH, self.config_backup_path)

        logger.info(f"link: {UDEVIL_CONFIG_PATH} → {self.config_target_path}")
        UDEVIL_CONFIG_PATH.symlink_to(self.config_target_path)
        logger.info(f"service start and enable: {self.udevil_service_name}")
        systemctl("start", self.udevil_service_name)
        systemctl("enable", self.udevil_service_name)
        return super().apply(**kwargs)

    def stop(self):
        logger.info(f"stop: {self.udevil_service_name}")
        systemctl("stop", self.udevil_service_name)
        return super().stop()

    def remove(self):
        if UDEVIL_CONFIG_PATH.is_symlink():
            logger.info(f"unlink: {UDEVIL_CONFIG_PATH}")
            UDEVIL_CONFIG_PATH.unlink()
        elif UDEVIL_CONFIG_PATH.exists():
            logger.warning(
                f"recovery udevil config already exists: {UDEVIL_CONFIG_PATH}"
            )
            return

        if self.config_backup_path.exists():
            self.stop()
            logger.info(f"recovery: {UDEVIL_CONFIG_PATH}")
            shutil.move(self.config_backup_path, UDEVIL_CONFIG_PATH)
        return super().remove()
