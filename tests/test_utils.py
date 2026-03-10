"""Tests for eurostat_energy_balance_processing.utils module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from eurostat_energy_balance_processing.utils import EU27_COUNTRY_CODES, write_to_excel


class TestEU27CountryCodes:
    """Tests for EU27_COUNTRY_CODES constant."""

    def test_eu27_country_codes_completeness(self) -> None:
        """Verify all 27 EU countries plus EU27 placeholder are included."""
        # 27 EU member states + 1 EU27 placeholder
        assert len(EU27_COUNTRY_CODES) == 28

    def test_eu27_country_codes_contains_required_keys(self) -> None:
        """Check that essential country codes are present."""
        required_codes = ["AT", "DE", "FR", "IT", "ES", "PL"]
        for code in required_codes:
            assert code in EU27_COUNTRY_CODES

    def test_eu27_contains_placeholder(self) -> None:
        """Verify EU27 placeholder key exists."""
        assert "EU27_{year}" in EU27_COUNTRY_CODES

    def test_austria_maps_correctly(self) -> None:
        """Test Austria mapping."""
        assert EU27_COUNTRY_CODES["AT"] == "Austria"


class TestWriteToExcel:
    """Tests for write_to_excel function."""

    def test_write_to_excel_adds_xlsx_suffix(self, tmp_path: Path) -> None:
        """Test that .xlsx suffix is added when missing."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        output_path = tmp_path / "output"

        with patch("builtins.print"):
            write_to_excel(df, output_path)

        expected_path = tmp_path / "output.xlsx"
        assert expected_path.exists()

    def test_write_to_excel_keeps_xlsx_suffix(self, tmp_path: Path) -> None:
        """Test that existing .xlsx suffix is preserved."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        output_path = tmp_path / "output.xlsx"

        with patch("builtins.print"):
            write_to_excel(df, output_path)

        assert output_path.exists()

    def test_write_to_excel_string_path(self, tmp_path: Path) -> None:
        """Test write_to_excel with string path input."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        output_path = str(tmp_path / "string_path_test")

        with patch("builtins.print"):
            write_to_excel(df, output_path)

        expected_path = tmp_path / "string_path_test.xlsx"
        assert expected_path.exists()

    def test_write_to_excel_pandas_dataframe(self, tmp_path: Path) -> None:
        """Test writing pandas DataFrame."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        output_path = tmp_path / "pandas_test.xlsx"

        with patch("builtins.print"):
            write_to_excel(df, output_path)

        assert output_path.exists()
        # Verify file is readable
        read_df = pd.read_excel(output_path)
        assert len(read_df) == 3

    def test_write_to_excel_pyam_dataframe(self, tmp_path: Path) -> None:
        """Test writing pyam IamDataFrame (mocked)."""
        mock_iamdf = MagicMock()
        mock_iamdf.__class__.__name__ = "IamDataFrame"
        output_path = tmp_path / "pyam_test.xlsx"

        # Patch the type check to recognize our mock as IamDataFrame
        with patch("builtins.print"), patch(
            "eurostat_energy_balance_processing.utils.pyam"
        ) as mock_pyam_module:
            mock_pyam_module.IamDataFrame = type(mock_iamdf)
            write_to_excel(mock_iamdf, output_path)

        mock_iamdf.to_excel.assert_called_once_with(output_path)

    def test_write_to_excel_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that existing files are overwritten."""
        df = pd.DataFrame({"col1": [1, 2]})
        output_path = tmp_path / "overwrite_test.xlsx"

        # Create initial file
        output_path.write_bytes(b"initial content")
        assert output_path.exists()

        with patch("builtins.print") as mock_print:
            write_to_excel(df, output_path)

        # Verify overwrite message was printed
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("overwrite" in call.lower() for call in calls)
