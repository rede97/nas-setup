import sys
import argparse
import tomllib
import logging
from pathlib import Path
from .sd_common import *
from .mount_service import MountService
from .nfs_service import NfsService
from .samba_service import SambaService

logging.basicConfig(
    level=logging.INFO,
    format='[%(filename)s:%(lineno)d] %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(description="Storage deployment cli tools")
parser.add_argument('-c', "--config", type=Path,
                    help=f"config file path, defaults to {DEFAULT_CONFIG_PATH}", default=None)
args = parser.parse_args()


def main():
    config_path: Path = args.config

    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
        if not config_path.exists():
            logger.info(f"init: {config_path}")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.touch()

    config_target_dir = config_path.parent
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    logger.info(f"config file: {config_path}")

    w = StringIO()
    # systemctl("daemon-reload")
    mount_service = MountService(config, config_target_dir)
    # mount_service.update()
    # mount_service.apply()
    # mount_service.remove()
    # mount_service.toml(w)
    # nfs_service = NfsService(config, config_target_dir)
    # nfs_service.update()
    # nfs_service.apply()
    # nfs_service.remove()
    # nfs_service.toml(w)

    samba_service = SambaService(config, config_target_dir)
    # samba_service.update()
    samba_service.toml(w)
    print(w.getvalue())


# sudo python3 -m storage_deploy.cli -c conf.toml
if __name__ == '__main__':
    main()
