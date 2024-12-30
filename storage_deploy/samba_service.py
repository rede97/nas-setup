import shutil
import logging
from io import StringIO
from typing import Any, Iterable
from dataclasses import dataclass
from .sd_common import *

logger = logging.getLogger(__name__)
SAMBA_CONFIG_PATH = Path("/etc/samba/smb.conf")
SAMBA_SERVICE_NAME = "smb.service"


RECYCLE_EXAMPLE = """\
recycle:repository = .recycle/%U
recycle:keeptree = yes
recycle:versions = yes
recycle:touch = yes
recycle:maxsixe = 0"""


@dataclass
class SambaConfig:
    policy: str = ""
    disable: bool = False


class SambaService(StorageDeployService):
    @staticmethod
    def arg_flag() -> str:
        return "smb"

    def __parse_samba_policies_config(self, policies: Iterable[str]):
        policy_text = StringIO()
        for sub_policy in policies:
            if sub_policy.startswith("$"):
                policy_ref_name = sub_policy.strip("$")
                policy_ref = self.samba_policies.get(policy_ref_name, None)
                if policy_ref is None:
                    raise ValueError(f"Unknown samba policy name: ${policy_ref_name}")
                policy_text.write(policy_ref)
            else:
                policy_text.write(sub_policy)
        return policy_text.getvalue()

    def __parse_samba_policy_define_config(self, samba_policies: dict[str, list | str]):
        for policy_name in samba_policies:
            policies = samba_policies[policy_name]
            if isinstance(policies, str):
                policies = (policies,)
            self.samba_policies[policy_name] = self.__parse_samba_policies_config(
                policies
            )

    def __parse_samba_config(self, samba_cfg: dict[str, Any]) -> SambaConfig:
        policies = samba_cfg.get("policies", [])
        if isinstance(policies, str):
            policies = (policies,)
        return SambaConfig(
            self.__parse_samba_policies_config(policies),
            samba_cfg.get("disable", False),
        )

    @staticmethod
    def __gen_samba_config(samba_configs: dict[str, SambaConfig]) -> str:
        w = StringIO()
        w.write(f"# /etc/samba/smb.conf: {DECLARE}\n")
        for samba_config_name, samba_config in samba_configs.items():
            if samba_config.disable:
                continue
            w.write(f"[{samba_config_name}]\n")
            w.write(f"{samba_config.policy}\n")
        return w.getvalue()

    def __init__(self, cfg: dict, config_target_dir: Path) -> None:
        super().__init__(cfg, config_target_dir)
        self.samba_policies = {}
        self.config_target_path = self.config_target_dir / "samba_config/smb.conf"
        self.config_backup_path = config_target_dir / "samba_backup/smb.conf"
        self.config_target_path.parent.mkdir(exist_ok=True)
        self.config_backup_path.parent.mkdir(exist_ok=True)

    def toml(self, w: StringIO):
        default_policy = {"enable_recycle": RECYCLE_EXAMPLE}
        toml_gen_elem_table(
            w, self.cfg.get("samba_policy", default_policy), "samba_policy"
        )

        samba_config = self.cfg.get("samba", {})
        if len(samba_config) == 0:
            default_config = trim_general_config_file(
                SAMBA_CONFIG_PATH, comment={";", "#"}
            )
            for samba_name in default_config:
                samba_config[samba_name] = {"policies": default_config[samba_name]}
        for samba_name in samba_config:
            if samba_name is None:
                continue
            toml_gen_elem_table(w, samba_config[samba_name], f"samba.{samba_name}")

        return super().toml(w)

    def update(self):
        self.__parse_samba_policy_define_config(self.cfg.get("samba_policy", {}))
        samba_configs: dict[str, Any] = self.cfg.get("samba", {})
        configs: dict[str, SambaConfig] = {}

        for samba_config_name, samba_config in samba_configs.items():
            configs[samba_config_name] = self.__parse_samba_config(samba_config)

        config = SambaService.__gen_samba_config(configs)
        with open(self.config_target_path, mode="wt") as f:
            logger.info(f"update: {self.config_target_path}")
            f.write(config)

        return super().update()

    def apply(self, **kwargs):
        self.stop()
        if SAMBA_CONFIG_PATH.exists():
            if SAMBA_CONFIG_PATH.is_symlink():
                logger.info(f"unlink: {SAMBA_CONFIG_PATH}")
                SAMBA_CONFIG_PATH.unlink()
            else:
                logger.info(f"backup: {SAMBA_CONFIG_PATH}")
                shutil.move(SAMBA_CONFIG_PATH, self.config_backup_path)

        logger.info(f"link: {SAMBA_CONFIG_PATH} → {self.config_target_path}")
        SAMBA_CONFIG_PATH.symlink_to(self.config_target_path)
        logger.info(f"service start and enable: {SAMBA_SERVICE_NAME}")
        systemctl("start", SAMBA_SERVICE_NAME)
        systemctl("enable", SAMBA_SERVICE_NAME)
        return super().apply(**kwargs)

    def stop(self):
        logger.info(f"stop: {SAMBA_SERVICE_NAME}")
        systemctl("stop", SAMBA_SERVICE_NAME)
        return super().stop()

    def remove(self):
        if SAMBA_CONFIG_PATH.is_symlink():
            logger.info(f"unlink: {SAMBA_CONFIG_PATH}")
            SAMBA_CONFIG_PATH.unlink()
        elif SAMBA_CONFIG_PATH.exists():
            logger.warning(f"recovery samba config already exists: {SAMBA_CONFIG_PATH}")
            return

        if self.config_backup_path.exists():
            self.stop()
            logger.info(f"recovery: {SAMBA_CONFIG_PATH}")
            shutil.move(self.config_backup_path, SAMBA_CONFIG_PATH)
        return super().remove()
