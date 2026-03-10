"""Tests for IAMC_Creator class in eurostat_energy_balance_processing.class_definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import yaml

from eurostat_energy_balance_processing.class_definitions import (
    EB_Processor,
    IAMC_Creator,
)


def create_mock_eb_processor(
    tmp_path: Path,
    mock_config_dict: dict[str, Any],
    mock_mapping_dict: dict,
    mock_definitions_variables_df: pd.DataFrame,
) -> EB_Processor:
    """Helper function to create a mocked EB_Processor."""
    config_file = tmp_path / "config.yaml"
    mock_config_dict["definition_path"] = str(tmp_path / "definitions")
    mock_config_dict["mapping_path"] = str(tmp_path / "mapping.yaml")
    mock_config_dict["path_definitions_with_values"] = str(tmp_path / "output.xlsx")
    mock_config_dict["eb_input_path"] = str(tmp_path / "eb_input.tsv")
    config_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    definitions_dir = tmp_path / "definitions"
    definitions_dir.mkdir()

    mapping_file = tmp_path / "mapping.yaml"
    mapping_file.write_text(yaml.dump(mock_mapping_dict), encoding="utf-8")

    mock_dsd = MagicMock()
    mock_variable = MagicMock()
    mock_variable.to_pandas.return_value = mock_definitions_variables_df
    mock_dsd.variable = mock_variable

    with patch(
        "eurostat_energy_balance_processing.class_definitions.nomenclature.DataStructureDefinition",
        return_value=mock_dsd,
    ):
        return EB_Processor(config_path=str(config_file))


class TestIAMCCreatorInit:
    """Tests for IAMC_Creator initialization."""

    def test_iamc_creator_init(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test IAMC_Creator initialization from parent processor."""
        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )

        creator = IAMC_Creator(parent)

        assert creator.region == "AT"
        assert creator.df_eb is None
        assert hasattr(creator, "mapping_variables_codes")


class TestIAMCCreatorFetchAndLoadEbTsv:
    """Tests for IAMC_Creator.fetch_and_load_eb_tsv method."""

    def test_fetch_and_load_eb_tsv_from_file(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
        mock_eb_dataframe: pd.DataFrame,
    ) -> None:
        """Test loading energy balance from existing TSV file."""
        # Create TSV input file
        tsv_file = tmp_path / "eb_input.tsv"
        tsv_content = "freq\tnrg_bal\tsiec\tunit\tgeo\\TIME_PERIOD\t2019\t2020\t2021\n"
        tsv_content += "A\tFC_E\tE7000\tGWH\tAT\t100\t110\t120\n"
        tsv_content += "A\tFC_E\tG3000\tGWH\tAT\t200\t210\t220\n"
        tsv_content += "A\tFC_E\tTOTAL\tGWH\tAT\t500\t520\t540\n"
        tsv_file.write_text(tsv_content, encoding="utf-8")

        mock_config_dict["eb_input_path"] = str(tsv_file)

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.eb_input_path = tsv_file

        creator = IAMC_Creator(parent)
        result = creator.fetch_and_load_eb_tsv()

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "nrg_bal" in result.columns
        assert all(result["geo"] == "AT")

    def test_fetch_and_load_eb_tsv_api_download(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test API download when local file doesn't exist."""
        mock_config_dict["eb_input_path"] = str(tmp_path / "nonexistent.tsv")

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.eb_input_path = tmp_path / "downloaded.tsv"

        creator = IAMC_Creator(parent)

        # Mock the API response
        mock_tsv_content = b"freq\tnrg_bal\tsiec\tunit\tgeo\\TIME_PERIOD\t2020\n"
        mock_tsv_content += b"A\tFC_E\tE7000\tGWH\tAT\t100\n"

        with patch(
            "eurostat_energy_balance_processing.class_definitions.urlopen"
        ) as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = mock_tsv_content
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            with pytest.warns(UserWarning, match="Downloading from Eurostat API"):
                result = creator.fetch_and_load_eb_tsv()

        assert isinstance(result, pd.DataFrame)


class TestIAMCCreatorMapEbCodesToCalcValues:
    """Tests for IAMC_Creator.map_eb_codes_to_calc_values method."""

    def test_map_eb_codes_to_calc_values(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
        mock_eb_dataframe: pd.DataFrame,
    ) -> None:
        """Test mapping EB codes to calculated values."""
        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )

        creator = IAMC_Creator(parent)
        creator.df_eb = mock_eb_dataframe

        result = creator.map_eb_codes_to_calc_values()

        assert isinstance(result, pd.DataFrame)
        assert "variable" in result.columns
        assert "unit" in result.columns

    def test_map_eb_codes_no_year_columns_raises_error(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test that ValueError is raised when no year columns exist."""
        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )

        creator = IAMC_Creator(parent)
        # DataFrame without year columns
        creator.df_eb = pd.DataFrame(
            {
                "freq": ["A"],
                "nrg_bal": ["FC_E"],
                "siec": ["E7000"],
                "unit": ["GWH"],
                "geo": ["AT"],
            }
        )

        with pytest.raises(ValueError, match="No year columns found"):
            creator.map_eb_codes_to_calc_values()


class TestIAMCCreatorStructurePyamFromPandas:
    """Tests for IAMC_Creator.structure_pyam_from_pandas method."""

    def test_structure_pyam_from_pandas(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test DataFrame to IamDataFrame conversion."""
        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )

        creator = IAMC_Creator(parent)

        input_df = pd.DataFrame(
            {
                "variable": ["Final Energy", "Final Energy [by Carrier]|Electricity"],
                "unit": ["GWh", "GWh"],
                "2020": [520.0, 110.0],
                "2021": [540.0, 120.0],
            }
        )

        # Mock pyam.IamDataFrame
        mock_iamdf = MagicMock()
        mock_iamdf.as_pandas.return_value = pd.DataFrame(
            {
                "variable": ["Final Energy"],
                "unit": ["GWh"],
            }
        )
        mock_iamdf.filter.return_value = mock_iamdf

        with patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.IamDataFrame",
            return_value=mock_iamdf,
        ), patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.concat",
            return_value=mock_iamdf,
        ):
            result = creator.structure_pyam_from_pandas(input_df)

        assert result is not None


class TestIAMCCreatorRun:
    """Tests for IAMC_Creator.run method."""

    def test_run_executes_workflow(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
        mock_eb_dataframe: pd.DataFrame,
    ) -> None:
        """Test that run() executes the full workflow."""
        # Create TSV file
        tsv_file = tmp_path / "eb_input.tsv"
        tsv_content = "freq\tnrg_bal\tsiec\tunit\tgeo\\TIME_PERIOD\t2019\t2020\t2021\n"
        tsv_content += "A\tFC_E\tE7000\tGWH\tAT\t100\t110\t120\n"
        tsv_file.write_text(tsv_content, encoding="utf-8")

        mock_config_dict["eb_input_path"] = str(tsv_file)

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.eb_input_path = tsv_file

        creator = IAMC_Creator(parent)

        # Mock pyam and write_to_excel to avoid file I/O
        mock_iamdf = MagicMock()
        mock_iamdf.as_pandas.return_value = pd.DataFrame(
            {"variable": ["Final Energy"], "unit": ["GWh"]}
        )
        mock_iamdf.filter.return_value = mock_iamdf

        mock_validation_creator = MagicMock()

        with patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.IamDataFrame",
            return_value=mock_iamdf,
        ), patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.concat",
            return_value=mock_iamdf,
        ), patch(
            "eurostat_energy_balance_processing.class_definitions.write_to_excel"
        ) as mock_write, patch(
            "eurostat_energy_balance_processing.class_definitions.Validation_Creator",
            return_value=mock_validation_creator,
        ) as mock_val_cls, patch(
            "builtins.print"
        ):
            creator.run()

        mock_write.assert_called_once()
        mock_val_cls.assert_called_once_with(creator)
        mock_validation_creator.run.assert_called_once()
