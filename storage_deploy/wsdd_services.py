import logging
from io import StringIO
from typing import Any
from .sd_common import *

logger = logging.getLogger(__name__)
WSDD_SERVICE_NAME = "wsdd.service"


# Web Service Discovery
class WsddService(StorageDeployService):
    @staticmethod
    def arg_flag() -> str:
        return "wsdd"

    def __init__(self, cfg: dict, config_target_dir: Path) -> None:
        super().__init__(cfg, config_target_dir)

    def toml(self, w: StringIO):
        wsdd_config: dict[str, Any] = self.cfg.get("wsdd", {})
        if len(wsdd_config) == 0:
            wsdd_config["disable"] = False
        toml_gen_elem_table(w, wsdd_config, f"wsdd")
        return super().toml(w)

    def update(self):
        wsdd_config: dict[str, Any] = self.cfg.get("wsdd", {})
        self.disable = wsdd_config.get("disable", False)
        return super().update()

    def apply(self, **kwargs):
        if self.disable:
            return
        systemctl("start", WSDD_SERVICE_NAME)
        systemctl("enable", WSDD_SERVICE_NAME)
        return super().apply(**kwargs)

    def stop(self):
        logger.info(f"stop: {WSDD_SERVICE_NAME}")
        systemctl("stop", WSDD_SERVICE_NAME)
        return super().stop()

    def remove(self):
        self.stop()
        return super().remove()
