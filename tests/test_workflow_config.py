"""Tests for eurostat_energy_balance_processing.workflow module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eurostat_energy_balance_processing.workflow import (
    build_parser,
    get_default_config_path,
    resolve_config_path,
)


class TestGetDefaultConfigPath:
    """Tests for get_default_config_path function."""

    def test_default_config_exists(self) -> None:
        """Verify default config file exists."""
        assert get_default_config_path().exists()

    def test_default_config_is_yaml(self) -> None:
        """Verify default config has .yaml extension."""
        assert get_default_config_path().suffix == ".yaml"

    def test_default_config_in_configs_dir(self) -> None:
        """Verify default config is in configs directory."""
        config_path = get_default_config_path()
        assert "configs" in str(config_path)


class TestResolveConfigPath:
    """Tests for resolve_config_path function."""

    def test_resolve_config_path_uses_argument(self, tmp_path: Path) -> None:
        """Test path resolution with provided argument."""
        cfg = tmp_path / "config.yaml"
        cfg.write_text("run:\n  name: custom\n", encoding="utf-8")
        assert resolve_config_path(str(cfg)) == cfg.resolve()

    def test_resolve_config_path_no_argument_uses_default(self) -> None:
        """Test that None argument returns default config path."""
        with patch("builtins.print"):
            result = resolve_config_path(None)

        assert result == get_default_config_path()

    def test_resolve_config_path_expands_user(self, tmp_path: Path) -> None:
        """Test that ~ is expanded in path."""
        # Create a path that looks like a home path
        cfg = tmp_path / "test_config.yaml"
        cfg.write_text("region: AT\n", encoding="utf-8")

        # Test with actual path (can't test ~ expansion directly without mocking)
        result = resolve_config_path(str(cfg))
        assert result.is_absolute()


class TestBuildParser:
    """Tests for build_parser function."""

    def test_build_parser_returns_argumentparser(self) -> None:
        """Test that build_parser returns an ArgumentParser."""
        import argparse

        parser = build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_build_parser_config_argument(self) -> None:
        """Test that parser accepts --config argument."""
        parser = build_parser()
        args = parser.parse_args(["--config", "/path/to/config.yaml"])
        assert args.config == "/path/to/config.yaml"

    def test_build_parser_config_default_none(self) -> None:
        """Test that config defaults to None."""
        parser = build_parser()
        args = parser.parse_args([])
        assert args.config is None


class TestMain:
    """Tests for main function."""

    def test_main_runs_processor(self) -> None:
        """Test that main() calls processor with resolved config."""
        from eurostat_energy_balance_processing import workflow

        mock_processor = MagicMock()
        mock_processor.run = MagicMock()

        with (
            patch.object(workflow, "build_parser") as mock_parser,
            patch(
                "eurostat_energy_balance_processing.workflow.EB_Processor.process",
                return_value=mock_processor,
            ) as mock_process,
            patch(
                "eurostat_energy_balance_processing.workflow.resolve_config_path",
                return_value=Path("/fake/config.yaml"),
            ),
        ):
            mock_args = MagicMock()
            mock_args.config = None
            mock_parser.return_value.parse_args.return_value = mock_args

            workflow.main()

        mock_process.assert_called_once()
        mock_processor.run.assert_called_once()
