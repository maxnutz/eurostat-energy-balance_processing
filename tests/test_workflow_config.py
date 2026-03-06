from pathlib import Path

from eurostat_energy_balance_processing.workflow import (
    get_default_config_path,
    load_config,
    resolve_config_path,
)


def test_default_config_exists() -> None:
    assert get_default_config_path().exists()


def test_resolve_config_path_uses_argument(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("run:\n  name: custom\n", encoding="utf-8")
    assert resolve_config_path(str(cfg)) == cfg.resolve()
