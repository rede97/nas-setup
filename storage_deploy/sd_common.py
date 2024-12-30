import sys
from io import StringIO
from pathlib import Path
from typing import Any, Optional
import subprocess
from argparse import ArgumentParser

DEFAULT_CONFIG_PATH = Path("/etc/store_deploy/conf.toml")
DECLARE = "Generated by storage-deploy script"


def is_subdirectory(parent_dir: Path, child_dir: Path):
    try:
        rel_path = str(Path(child_dir).relative_to(Path(parent_dir)))
        return not rel_path.startswith('..') and rel_path != ''
    except ValueError:
        return False


def systemctl(action: str, service: str = ""):
    cmd = " ".join(("systemctl", action, service))
    retcode = subprocess.run(
        cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr).returncode
    if retcode != 0:
        raise SystemError(f"run cmd: {cmd} with return code = {retcode}")


class StorageDeployService:
    @staticmethod
    def arg_flag() -> str:
        raise NotImplemented

    def __init__(self, cfg: dict, config_target_dir: Path) -> None:
        self.cfg = cfg
        self.config_target_dir = config_target_dir.absolute()

    def toml(self, w: StringIO):
        pass

    def update(self):
        pass

    def apply(self, **kwargs):
        pass

    def stop(self):
        pass

    def remove(self):
        pass


def toml_gen_elem(inst: Any) -> str:
    if isinstance(inst, str):
        if len(inst.splitlines()) > 1 or inst.endswith("\n"):
            return f"\'\'\'{inst}\'\'\'"
        else:
            return f"\'{inst}\'"
    elif isinstance(inst, list):
        content = ", ".join(map(toml_gen_elem, inst))
        return f"[ {content} ]"
    elif isinstance(inst, dict):
        content = ", ".join(
            map(lambda k: f'{k} = {toml_gen_elem(inst[k])}', inst))
        return f"{{ {content} }}"
    elif isinstance(inst, bool):
        if inst:
            return "true"
        else:
            return "false"
    else:
        return str(inst)


def toml_gen_elem_table(w: StringIO, inst: dict | list[dict], name: Optional[str] = None):
    if isinstance(inst, dict):
        if name is not None:
            w.write(f"\n[{name}]\n")
        for k, v in inst.items():
            w.write(f"{k} = {toml_gen_elem(v)}\n")
    elif isinstance(inst, list):
        assert name is not None
        w.write(f"\n[[{name}]]\n")
        for e in inst:
            toml_gen_elem_table(w, e)


def trim_general_config(content: str, comment: set[str] = {"#"}) -> dict[str | None, str]:
    config_dict = {}
    tag = None
    config_content = StringIO()
    for line in content.splitlines(True):
        line = line.strip()
        if len(line) == 0 or line[0] in comment:
            continue
        elif line.startswith("["):
            end_idx = line.find("]", 1)
            if end_idx == -1:
                raise ValueError(f"invalid config content: `{line}`")
            config_dict[tag] = config_content.getvalue()
            tag = line[1: end_idx]
            config_content = StringIO()
        else:
            if len(line) != 0:
                config_content.write(line)
                config_content.write('\n')
    config_dict[tag] = config_content.getvalue()
    return config_dict


def trim_general_config_file(p: Path, comment: set[str] = {"#"}) -> dict[str | None, str]:
    with open(p, "rt") as f:
        return trim_general_config(f.read(), comment)
