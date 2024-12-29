import sys
import argparse
import tomllib
import logging
from pathlib import Path
from colorama import init, Fore
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

ServicesType: list[type[StorageDeployService]] = [
    MountService, NfsService, SambaService]
Services: dict[str, type[StorageDeployService]] = {
    t.arg_flag(): t for t in ServicesType}


def init_parser() -> Any:
    parser = argparse.ArgumentParser(
        description="Storage deployment cli tools", add_help=True)

    parser.add_argument("action", type=str, choices=[
                        "init", "apply", "stop", "remove"], default=None)
    parser.add_argument(f"--all", action='store_true', help="all-services")
    for service_type in ServicesType:
        parser.add_argument(f"--{service_type.arg_flag()}",
                            action='store_true', help=service_type.__name__)

    parser.add_argument('-c', "--config", type=Path,
                        help=f"config file path, defaults to {DEFAULT_CONFIG_PATH}", default=None)

    args = parser.parse_args()
    return args


def main():
    args = init_parser()
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

    if args.action == "init":
        init_cfg = StringIO()
        for service_flag in Services:
            if args.__dict__[service_flag] or args.all:
                service = Services[service_flag](config, config_target_dir)
                service.toml(init_cfg)
        with open(config_path, "w") as f:
            f.write(init_cfg.getvalue())
    else:
        systemctl("daemon-reload")
        for service_flag in Services:
            if args.__dict__[service_flag] or args.all:
                service = Services[service_flag](config, config_target_dir)
                match args.action:
                    case "apply":
                        service.update()
                        service.apply()
                    case "stop":
                        service.stop()
                    case "remove":
                        service.remove()

    # print(w.getvalue())


# sudo python3 -m storage_deploy.cli -c conf.toml
if __name__ == '__main__':
    main()
