#!/usr/bin/python3
import argparse
import tomllib
from pathlib import Path
from mount_service import update_config


DEFAULT_CONFIG_PATH = "/etc/store_deploy/conf.toml"

parser = argparse.ArgumentParser(description="Storage deployment cli tools")
# positional argument
parser.add_argument('-c', "--config", type=Path, help=f"config file path, defaults to {DEFAULT_CONFIG_PATH}", default=DEFAULT_CONFIG_PATH)
args = parser.parse_args()
# print(args)

def load_config(cfg: Path) -> dict:
    if cfg.exists():
        with open(cfg, "rb") as f:
            toml_cfg = tomllib.load(f)
            return toml_cfg
    else:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.touch()
        return {}

def pre_proc_config(cfg: dict) -> dict:
    cfg["mounts"] = cfg["mounts"] or []
    cfg["samba"] = cfg["samba"] or {}
    return cfg


cfg = load_config(args.config)

update_config(cfg["mounts"], Path("."))