from __future__ import annotations

import argparse
from pathlib import Path
import yaml

from eurostat_energy_balance_processing import EB_Processor


def get_default_config_path() -> Path:
    return Path(__file__).resolve().parent / "configs" / "config.default.yaml"


def resolve_config_path(config_arg: str | None) -> Path:
    if config_arg:
        return Path(config_arg).expanduser().resolve()
    else:
        print("WARNING: no config-file provided. Use default config.")
    return get_default_config_path()


def resolve_publication_year(publication_year_arg: int | None) -> int | None:
    if publication_year_arg:
        return publication_year_arg
    else:
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Process Eurostat energy balance data."
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config file. Defaults to packaged config.",
    )
    parser.add_argument(
        "--publication_year",
        default=None,
        type=int,
        help="Year of publication of the Eurostat Energy Balance to use. Defaults to current year.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path = resolve_config_path(args.config)
    publication_year = resolve_publication_year(args.publication_year)
    processor = EB_Processor.process(
        config_path=config_path, publication_year=publication_year
    )
    processor.run()


if __name__ == "__main__":
    main()
