#!/usr/bin/python3
import sys
import argparse
import tomllib
from pathlib import Path
from sd_common import *
from mount_service import MountService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(filename)s:%(lineno)d] %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


parser = argparse.ArgumentParser(description="Storage deployment cli tools")
parser.add_argument('-c', "--config", type=Path,
                    help=f"config file path, defaults to {DEFAULT_CONFIG_PATH}", default=DEFAULT_CONFIG_PATH)
args = parser.parse_args()


def main():
    config_path: Path = args.config
    config_target_dir = config_path.parent
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    else:
        config_target_dir.mkdir(parents=True, exist_ok=True)
        config_path.touch()
        config = {}
    logger.info(f"config file: {config_path}")

    systemctl("daemon-reload")
    mount_service = MountService(config, config_target_dir)
    mount_service.update()
    mount_service.apply()


if __name__ == '__main__':
    main()

