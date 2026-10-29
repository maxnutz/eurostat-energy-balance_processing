"""Tests for eurostat_energy_balance_processing.utils module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from eurostat_energy_balance_processing.utils import (
    EU27_COUNTRY_CODES,
    INDUSTRY_NON_ENERGY_SIEC,
    calculate_industry_non_energy_shares,
    write_to_excel,
)


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


class TestCalculateIndustryNonEnergyShares:
    """Tests for calculate_industry_non_energy_shares function."""

    @staticmethod
    def _eb(rows: list[tuple[str, str, str, float, float]]) -> pd.DataFrame:
        return pd.DataFrame(
            rows, columns=["nrg_bal", "siec", "geo", "2023", "2024"]
        ).assign(freq="A", unit="GWH")

    def test_share_per_country_carrier_and_year(self) -> None:
        df = self._eb(
            [
                ("FC_IND_E", "G3000", "AT", 90.0, 75.0),
                ("FC_IND_NE", "G3000", "AT", 10.0, 25.0),
                ("FC_IND_E", "O4000XBIO", "DE", 20.0, 20.0),
                ("FC_IND_NE", "O4000XBIO", "DE", 80.0, 60.0),
            ]
        )
        result = calculate_industry_non_energy_shares(df)
        assert list(result.columns) == [
            "country",
            "carrier",
            "siec",
            "year",
            "unit",
            "energy_use",
            "non_energy_use",
            "non_energy_share",
        ]
        shares = result.set_index(["country", "carrier", "year"])["non_energy_share"]
        assert shares[("AT", "Natural Gas", 2023)] == pytest.approx(0.1)
        assert shares[("AT", "Natural Gas", 2024)] == pytest.approx(0.25)
        assert shares[("DE", "Oil", 2024)] == pytest.approx(0.75)
        assert len(result) == 4

    def test_drops_missing_and_zero_denominator(self) -> None:
        df = self._eb(
            [
                ("FC_IND_E", "G3000", "AT", 0.0, float("nan")),
                ("FC_IND_NE", "G3000", "AT", 0.0, 5.0),
            ]
        )
        assert calculate_industry_non_energy_shares(df).empty

    def test_ignores_other_balances_and_carriers(self) -> None:
        df = self._eb(
            [
                ("FC_IND_E", "G3000", "AT", 1.0, 1.0),
                ("FC_IND_NE", "G3000", "AT", 1.0, 1.0),
                ("FC_NE", "G3000", "AT", 99.0, 99.0),
                ("FC_IND_E", "C0311", "AT", 5.0, 5.0),
                ("FC_IND_NE", "C0311", "AT", 5.0, 5.0),
            ]
        )
        result = calculate_industry_non_energy_shares(df)
        assert set(result["siec"]) == {INDUSTRY_NON_ENERGY_SIEC["Natural Gas"]}
        assert (result["non_energy_share"] == 0.5).all()

    def test_coal_uses_non_energy_use_of_all_sectors(self) -> None:
        df = self._eb(
            [
                ("FC_IND_E", "C0000X0350-0370", "AT", 90.0, 90.0),
                ("FC_IND_NE", "C0000X0350-0370", "AT", 99.0, 99.0),
                ("FC_NE", "C0000X0350-0370", "AT", 10.0, 30.0),
            ]
        )
        result = calculate_industry_non_energy_shares(df)
        shares = result.set_index(["carrier", "year"])["non_energy_share"]
        assert set(result["carrier"]) == {"Coal"}
        assert shares[("Coal", 2023)] == pytest.approx(0.1)
        assert shares[("Coal", 2024)] == pytest.approx(0.25)
