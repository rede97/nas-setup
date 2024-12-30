import shutil
import logging
from dataclasses import dataclass
from io import StringIO
from typing import Any
from .sd_common import *

logger = logging.getLogger(__name__)
NFS_CONFIG_PATH = Path("/etc/exports")
NFS_SERVICE_NAME = "nfs-server.service"


@dataclass
class NfsPoicy:
    access: str = ""
    options: str = ""

    @property
    def config(self) -> str:
        return f"{self.access}({self.options})"


@dataclass
class NfsExportConfig:
    export: Path
    policies: list[NfsPoicy]
    disable: bool

    @property
    def config(self) -> str:
        policies_cfg = " ".join(map(lambda p: p.config, self.policies))
        return f"{self.export.absolute()}    {policies_cfg}"


class NfsService(StorageDeployService):
    @staticmethod
    def arg_flag() -> str:
        return "nfs"

    def __parse_nfs_config(self, nfs_export: dict[str, Any]) -> NfsExportConfig:
        policies: list[NfsPoicy] = []
        nfs_export_policies = nfs_export["policies"]
        if isinstance(nfs_export_policies, str):
            nfs_export_policies = (nfs_export_policies,)
        common_nfs_policies = self.cfg.get("nfs_policy", {})
        for policy in nfs_export_policies:
            if isinstance(policy, str):
                policy_ref_name = policy.strip("$")
                policy_ref = common_nfs_policies.get(policy_ref_name, None)
                if policy_ref is None:
                    raise ValueError(f"Unknown NFS policy {policy_ref_name}")
                policies.append(NfsPoicy(**policy_ref))
            if isinstance(policy, dict):
                policies.append(NfsPoicy(**policy))
        return NfsExportConfig(
            Path(nfs_export["export"]),
            policies,
            disable=nfs_export.get("disable", False),
        )

    @staticmethod
    def __gen_nfs_config(nfs_exports_cfg: list[NfsExportConfig]) -> str:
        w = StringIO()
        w.write(f"# /etc/exports: {DECLARE}\n")
        for exports_cfg in nfs_exports_cfg:
            if exports_cfg.disable:
                continue
            w.write(f"{exports_cfg.config}\n")
        return w.getvalue()

    def __init__(self, cfg: dict, config_target_dir: Path) -> None:
        super().__init__(cfg, config_target_dir)
        self.config_target_path = self.config_target_dir / "nfs_config/exports"
        self.config_backup_path = config_target_dir / "nfs_backup/exports"
        self.config_target_path.parent.mkdir(exist_ok=True)
        self.config_backup_path.parent.mkdir(exist_ok=True)

    def toml(self, w: StringIO):
        default_policy = {
            "local": NfsPoicy("172.16.0.0/24", "rw,async,no_subtree_check").__dict__
        }
        default_nfs = [{"path": "/srv/nfs", "policy": ["$local"]}]
        toml_gen_elem_table(w, self.cfg.get("nfs_policy", default_policy), "nfs_policy")
        toml_gen_elem_table(w, self.cfg.get("nfs", default_nfs), "nfs")
        return super().toml(w)

    def update(self):
        nfs_exports_cfg: list[NfsExportConfig] = []
        for nfs_cfg in self.cfg.get("nfs", []):
            nfs_exports_cfg.append(self.__parse_nfs_config(nfs_cfg))
        config = NfsService.__gen_nfs_config(nfs_exports_cfg)
        with open(self.config_target_path, mode="wt") as f:
            logger.info(f"update: {self.config_target_path}")
            f.write(config)

        return super().update()

    def apply(self, **kwargs):
        self.stop()
        if NFS_CONFIG_PATH.exists():
            if NFS_CONFIG_PATH.is_symlink():
                logger.info(f"unlink: {NFS_CONFIG_PATH}")
                NFS_CONFIG_PATH.unlink()
            else:
                logger.info(f"backup: {NFS_CONFIG_PATH}")
                shutil.move(NFS_CONFIG_PATH, self.config_backup_path)

        logger.info(f"link: {NFS_CONFIG_PATH} → {self.config_target_path}")
        NFS_CONFIG_PATH.symlink_to(self.config_target_path)
        logger.info(f"service start and enable: {NFS_SERVICE_NAME}")
        systemctl("start", NFS_SERVICE_NAME)
        systemctl("enable", NFS_SERVICE_NAME)
        return super().apply(**kwargs)

    def stop(self):
        logger.info(f"stop: {NFS_SERVICE_NAME}")
        systemctl("stop", NFS_SERVICE_NAME)
        return super().stop()

    def remove(self):
        if NFS_CONFIG_PATH.is_symlink():
            logger.info(f"unlink: {NFS_CONFIG_PATH}")
            NFS_CONFIG_PATH.unlink()
        elif NFS_CONFIG_PATH.exists():
            logger.warning(f"recovery nfs config already exists: {NFS_CONFIG_PATH}")
            return

        if self.config_backup_path.exists():
            self.stop()
            logger.info(f"recovery: {NFS_CONFIG_PATH}")
            shutil.move(self.config_backup_path, NFS_CONFIG_PATH)
        return super().remove()
