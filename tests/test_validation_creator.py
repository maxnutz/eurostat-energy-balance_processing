"""Tests for Validation_Creator class in eurostat_energy_balance_processing.class_definitions."""

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
    Validation_Creator,
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


class TestValidationCreatorGetVariableTolerances:
    """Tests for Validation_Creator._get_variable_tolerances method."""

    def test_get_variable_tolerances_default(self) -> None:
        """Test that default tolerances are returned when no overrides apply."""
        # Create minimal Validation_Creator mock with only needed attributes
        creator = object.__new__(Validation_Creator)

        default_tolerances = {"low": 0.3, "medium": 0.4, "high": 0.5, "error": 1.0}
        sector_tolerances: dict[str, dict[str, float]] = {}
        carrier_tolerances: dict[str, dict[str, float]] = {}
        warning_levels = ["low", "medium", "high", "error"]

        result = creator._get_variable_tolerances(
            variable_name="Some Variable",
            warning_levels=warning_levels,
            default_tolerances=default_tolerances,
            sector_tolerances=sector_tolerances,
            carrier_tolerances=carrier_tolerances,
        )

        assert len(result) == 4
        assert result[0] == {"warning_level": "low", "rtol": 0.3}
        assert result[1] == {"warning_level": "medium", "rtol": 0.4}

    def test_get_variable_tolerances_carrier_override(self) -> None:
        """Test that carrier-specific tolerances override defaults."""
        creator = object.__new__(Validation_Creator)

        default_tolerances = {"low": 0.3, "medium": 0.4}
        sector_tolerances: dict[str, dict[str, float]] = {}
        carrier_tolerances = {"Electricity": {"low": 0.03}}
        warning_levels = ["low", "medium"]

        result = creator._get_variable_tolerances(
            variable_name="Final Energy|Electricity",
            warning_levels=warning_levels,
            default_tolerances=default_tolerances,
            sector_tolerances=sector_tolerances,
            carrier_tolerances=carrier_tolerances,
        )

        # Low should be overridden by carrier tolerance
        assert result[0] == {"warning_level": "low", "rtol": 0.03}
        # Medium should use default
        assert result[1] == {"warning_level": "medium", "rtol": 0.4}

    def test_get_variable_tolerances_sector_override(self) -> None:
        """Test that sector-specific tolerances override carrier and defaults."""
        creator = object.__new__(Validation_Creator)

        default_tolerances = {"low": 0.3, "medium": 0.4}
        sector_tolerances = {"Final Energy": {"low": 0.05}}
        carrier_tolerances = {"Electricity": {"low": 0.03}}
        warning_levels = ["low", "medium"]

        result = creator._get_variable_tolerances(
            variable_name="Final Energy|Electricity",
            warning_levels=warning_levels,
            default_tolerances=default_tolerances,
            sector_tolerances=sector_tolerances,
            carrier_tolerances=carrier_tolerances,
        )

        # Sector tolerance should override carrier tolerance
        assert result[0] == {"warning_level": "low", "rtol": 0.05}
        assert result[1] == {"warning_level": "medium", "rtol": 0.4}

    def test_get_variable_tolerances_no_match(self) -> None:
        """Test behavior when variable doesn't match any carrier or sector."""
        creator = object.__new__(Validation_Creator)

        default_tolerances = {"low": 0.3}
        sector_tolerances = {"Different Sector": {"low": 0.05}}
        carrier_tolerances = {"Different Carrier": {"low": 0.03}}
        warning_levels = ["low"]

        result = creator._get_variable_tolerances(
            variable_name="Primary Energy|Gas",
            warning_levels=warning_levels,
            default_tolerances=default_tolerances,
            sector_tolerances=sector_tolerances,
            carrier_tolerances=carrier_tolerances,
        )

        # Should use default
        assert result[0] == {"warning_level": "low", "rtol": 0.3}


class TestValidationCreatorBuildValidationDefinitions:
    """Tests for Validation_Creator.build_validation_definitions method."""

    def test_build_validation_definitions(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test full validation definitions building."""
        # Create existing output file
        output_file = tmp_path / "output.xlsx"
        pd.DataFrame({"test": [1]}).to_excel(output_file)
        mock_config_dict["path_definitions_with_values"] = str(output_file)

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.path_definitions_with_values = output_file

        # Mock pyam.IamDataFrame
        mock_iamdf = MagicMock()
        mock_df = pd.DataFrame(
            {
                "variable": ["Final Energy", "Final Energy|Electricity"],
                "value": [500.0, 110.0],
                "year": [2020, 2020],
            }
        )
        mock_iamdf.filter.return_value.as_pandas.return_value = mock_df

        with patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.IamDataFrame",
            return_value=mock_iamdf,
        ):
            creator = Validation_Creator(parent)
            result = creator.build_validation_definitions()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["variable"] == "Final Energy"
        assert result[0]["year"] == 2020
        assert result[0]["value"] == 500.0
        assert "validation" in result[0]

    def test_build_validation_definitions_skips_nan(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test that NaN values are skipped in validation definitions."""
        output_file = tmp_path / "output.xlsx"
        pd.DataFrame({"test": [1]}).to_excel(output_file)
        mock_config_dict["path_definitions_with_values"] = str(output_file)

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.path_definitions_with_values = output_file

        # Mock pyam.IamDataFrame with NaN values
        mock_iamdf = MagicMock()
        mock_df = pd.DataFrame(
            {
                "variable": ["Final Energy", "Missing Data"],
                "value": [500.0, np.nan],
                "year": [2020, 2020],
            }
        )
        mock_iamdf.filter.return_value.as_pandas.return_value = mock_df

        with patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.IamDataFrame",
            return_value=mock_iamdf,
        ):
            creator = Validation_Creator(parent)
            result = creator.build_validation_definitions()

        # Only non-NaN variable should be in result
        assert len(result) == 1
        assert result[0]["variable"] == "Final Energy"


class TestValidationCreatorWriteToCodelistYaml:
    """Tests for Validation_Creator.write_to_codelist_yaml method."""

    def test_write_to_codelist_yaml(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test writing validation definitions to YAML file."""
        output_file = tmp_path / "output.xlsx"
        pd.DataFrame({"test": [1]}).to_excel(output_file)
        mock_config_dict["path_definitions_with_values"] = str(output_file)

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.path_definitions_with_values = output_file

        # Mock pyam.IamDataFrame
        mock_iamdf = MagicMock()
        mock_df = pd.DataFrame(
            {
                "variable": ["Final Energy"],
                "value": [500.0],
                "year": [2020],
            }
        )
        mock_iamdf.filter.return_value.as_pandas.return_value = mock_df

        with patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.IamDataFrame",
            return_value=mock_iamdf,
        ):
            creator = Validation_Creator(parent)
            creator.validation_codelist = creator.validation_definitions
            creator.write_to_codelist_yaml()

        # Verify file was created
        assert creator.path_codelist_yaml.exists()

        # Verify content
        with open(creator.path_codelist_yaml, "r") as f:
            written_content = yaml.safe_load(f)

        assert isinstance(written_content, list)
        assert written_content[0]["variable"] == "Final Energy"


class TestValidationCreatorRun:
    """Tests for Validation_Creator.run method."""

    def test_run_creates_yaml(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test that run() creates validation YAML file."""
        output_file = tmp_path / "output.xlsx"
        pd.DataFrame({"test": [1]}).to_excel(output_file)
        mock_config_dict["path_definitions_with_values"] = str(output_file)

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.path_definitions_with_values = output_file

        # Mock pyam.IamDataFrame
        mock_iamdf = MagicMock()
        mock_df = pd.DataFrame(
            {
                "variable": ["Final Energy"],
                "value": [500.0],
                "year": [2020],
            }
        )
        mock_iamdf.filter.return_value.as_pandas.return_value = mock_df

        with patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.IamDataFrame",
            return_value=mock_iamdf,
        ), patch("builtins.print"):
            creator = Validation_Creator(parent)
            creator.run()

        # Verify YAML file was created
        assert creator.path_codelist_yaml.exists()


class TestValidationCreatorLoadPyamData:
    """Tests for Validation_Creator._load_pyam_data method."""

    def test_load_pyam_data_from_attribute(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test _load_pyam_data returns existing attribute when present."""
        output_file = tmp_path / "output.xlsx"
        pd.DataFrame({"test": [1]}).to_excel(output_file)
        mock_config_dict["path_definitions_with_values"] = str(output_file)

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.path_definitions_with_values = output_file

        # Create a mock IamDataFrame that will be set as attribute
        mock_iamdf = MagicMock()
        mock_df = pd.DataFrame(
            {
                "variable": ["Final Energy"],
                "value": [500.0],
                "year": [2020],
            }
        )
        mock_iamdf.filter.return_value.as_pandas.return_value = mock_df

        with patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.IamDataFrame",
            return_value=mock_iamdf,
        ) as mock_pyam_class:
            # Make isinstance check work
            mock_pyam_class.__class__ = type(mock_iamdf)
            creator = Validation_Creator(parent)

        # pyam.IamDataFrame should have been called to load data
        assert mock_pyam_class.called

    def test_load_pyam_data_file_not_found(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test _load_pyam_data raises FileNotFoundError when file missing."""
        # Don't create the output file
        mock_config_dict["path_definitions_with_values"] = str(
            tmp_path / "nonexistent.xlsx"
        )

        parent = create_mock_eb_processor(
            tmp_path, mock_config_dict, mock_mapping_dict, mock_definitions_variables_df
        )
        parent.path_definitions_with_values = tmp_path / "nonexistent.xlsx"

        with pytest.raises(FileNotFoundError, match="IAMC output file not found"):
            Validation_Creator(parent)
