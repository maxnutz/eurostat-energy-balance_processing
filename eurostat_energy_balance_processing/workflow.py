from __future__ import annotations

import argparse
from pathlib import Path
import yaml


def get_default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "configs" / "config.default.yaml"


def resolve_config_path(config_arg: str | None) -> Path:
    if config_arg:
        return Path(config_arg).expanduser().resolve()
    else:
        print("WARNING: no config-file provided. Use default config.")
    return get_default_config_path()

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process Eurostat energy balance data."
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config file. Defaults to packaged config.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path = resolve_config_path(args.config)


if __name__ == "__main__":
    main()
