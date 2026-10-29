"""Tests for EB_Processor class in eurostat_energy_balance_processing.class_definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import yaml

from eurostat_energy_balance_processing.class_definitions import (
    EB_Processor,
    IAMC_Creator,
    Validation_Creator,
)


class TestEBProcessorInit:
    """Tests for EB_Processor initialization."""

    def test_eb_processor_init_with_mocks(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test EB_Processor initialization with mocked dependencies."""
        # Create config file
        config_file = tmp_path / "config.yaml"
        mock_config_dict["definition_path"] = str(tmp_path / "definitions")
        mock_config_dict["mapping_path"] = str(tmp_path / "mapping.yaml")
        config_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

        # Create definitions directory
        definitions_dir = tmp_path / "definitions"
        definitions_dir.mkdir()

        # Create mapping file
        mapping_file = tmp_path / "mapping.yaml"
        mapping_file.write_text(yaml.dump(mock_mapping_dict), encoding="utf-8")

        # Mock nomenclature.DataStructureDefinition
        mock_dsd = MagicMock()
        mock_variable = MagicMock()
        mock_variable.to_pandas.return_value = mock_definitions_variables_df
        mock_dsd.variable = mock_variable

        with patch(
            "eurostat_energy_balance_processing.class_definitions.nomenclature.DataStructureDefinition",
            return_value=mock_dsd,
        ):
            processor = EB_Processor(config_path=str(config_file))

        assert processor.region == "AT"
        assert processor.validation_year == 2020
        assert processor.eb_unit == "GWh"

    def test_eb_processor_repr(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test EB_Processor string representation."""
        config_file = tmp_path / "config.yaml"
        mock_config_dict["definition_path"] = str(tmp_path / "definitions")
        mock_config_dict["mapping_path"] = str(tmp_path / "mapping.yaml")
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
            processor = EB_Processor(config_path=str(config_file))
            repr_str = repr(processor)

        assert "EB_Processor" in repr_str
        assert "AT" in repr_str
        assert "2020" in repr_str


class TestEBProcessorProcess:
    """Tests for EB_Processor.process factory method."""

    def test_process_returns_iamc_creator_when_not_processed(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test process() returns IAMC_Creator when output file doesn't exist."""
        config_file = tmp_path / "config.yaml"
        mock_config_dict["definition_path"] = str(tmp_path / "definitions")
        mock_config_dict["mapping_path"] = str(tmp_path / "mapping.yaml")
        mock_config_dict["path_definitions_with_values"] = str(
            tmp_path / "nonexistent.xlsx"
        )
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
            result = EB_Processor.process(config_path=str(config_file))

        assert isinstance(result, IAMC_Creator)

    def test_process_returns_validation_creator_when_processed(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test process() returns Validation_Creator when output file exists."""
        config_file = tmp_path / "config.yaml"
        mock_config_dict["definition_path"] = str(tmp_path / "definitions")
        mock_config_dict["mapping_path"] = str(tmp_path / "mapping.yaml")

        # Create existing output file
        output_file = tmp_path / "existing_output.xlsx"
        pd.DataFrame({"test": [1]}).to_excel(output_file)
        mock_config_dict["path_definitions_with_values"] = str(output_file)

        config_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

        definitions_dir = tmp_path / "definitions"
        definitions_dir.mkdir()

        mapping_file = tmp_path / "mapping.yaml"
        mapping_file.write_text(yaml.dump(mock_mapping_dict), encoding="utf-8")

        mock_dsd = MagicMock()
        mock_variable = MagicMock()
        mock_variable.to_pandas.return_value = mock_definitions_variables_df
        mock_dsd.variable = mock_variable

        # Mock pyam.IamDataFrame for Validation_Creator
        mock_iamdf = MagicMock()
        mock_df = pd.DataFrame(
            {
                "variable": ["Final Energy"],
                "value": [100.0],
                "year": [2020],
            }
        )
        mock_iamdf.filter.return_value.as_pandas.return_value = mock_df

        with patch(
            "eurostat_energy_balance_processing.class_definitions.nomenclature.DataStructureDefinition",
            return_value=mock_dsd,
        ), patch(
            "eurostat_energy_balance_processing.class_definitions.pyam.IamDataFrame",
            return_value=mock_iamdf,
        ):
            result = EB_Processor.process(config_path=str(config_file))

        assert isinstance(result, Validation_Creator)


class TestEBProcessorEbAlreadyProcessed:
    """Tests for EB_Processor._eb_already_processed method."""

    def test_eb_already_processed_true(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test _eb_already_processed returns True when file exists."""
        config_file = tmp_path / "config.yaml"
        mock_config_dict["definition_path"] = str(tmp_path / "definitions")
        mock_config_dict["mapping_path"] = str(tmp_path / "mapping.yaml")

        # Create existing output file
        output_file = tmp_path / "output.xlsx"
        output_file.touch()
        mock_config_dict["path_definitions_with_values"] = str(output_file)

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
            processor = EB_Processor(config_path=str(config_file))
            result = processor._eb_already_processed()

        assert result is True

    def test_eb_already_processed_false(
        self,
        tmp_path: Path,
        mock_config_dict: dict[str, Any],
        mock_mapping_dict: dict,
        mock_definitions_variables_df: pd.DataFrame,
    ) -> None:
        """Test _eb_already_processed returns False when file doesn't exist."""
        config_file = tmp_path / "config.yaml"
        mock_config_dict["definition_path"] = str(tmp_path / "definitions")
        mock_config_dict["mapping_path"] = str(tmp_path / "mapping.yaml")
        mock_config_dict["path_definitions_with_values"] = str(
            tmp_path / "nonexistent.xlsx"
        )
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
            processor = EB_Processor(config_path=str(config_file))
            result = processor._eb_already_processed()

        assert result is False


class TestEBProcessorReadConfig:
    """Tests for EB_Processor.read_config method."""

    def test_read_config_valid_yaml(self, tmp_path: Path) -> None:
        """Test read_config with valid YAML file."""
        config_content = {
            "region": "DE",
            "validation_year": 2021,
            "definition_path": "/test/path",
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump(config_content), encoding="utf-8")

        # Create a minimal EB_Processor mock to test read_config directly
        processor = object.__new__(EB_Processor)
        processor.config_path = str(config_file)

        result = processor.read_config()

        assert result["region"] == "DE"
        assert result["validation_year"] == 2021


class TestEBProcessorGetMappingVariablesCodes:
    """Tests for EB_Processor.get_mapping_variables_codes method."""

    def test_get_mapping_variables_codes_valid(
        self, tmp_path: Path, mock_mapping_dict: dict
    ) -> None:
        """Test get_mapping_variables_codes with valid mapping file."""
        mapping_file = tmp_path / "mapping.yaml"
        mapping_file.write_text(yaml.dump(mock_mapping_dict), encoding="utf-8")

        # Create minimal processor mock
        processor = object.__new__(EB_Processor)
        processor.mapping_path = str(mapping_file)

        result = processor.get_mapping_variables_codes()

        assert "siec_dict" in result
        assert "nrg_dict" in result
        assert "Coal" in result["siec_dict"]
        assert result["siec_dict"]["Coal"] == ["C0000X0350-0370", "P1000"]

    def test_get_mapping_variables_codes_file_not_found(self, tmp_path: Path) -> None:
        """Test get_mapping_variables_codes raises FileNotFoundError."""
        processor = object.__new__(EB_Processor)
        processor.mapping_path = str(tmp_path / "nonexistent.yaml")

        with pytest.raises(FileNotFoundError, match="Mapping file not found"):
            processor.get_mapping_variables_codes()

    def test_get_mapping_variables_codes_invalid_yaml(self, tmp_path: Path) -> None:
        """Test get_mapping_variables_codes raises ValueError for invalid structure."""
        mapping_file = tmp_path / "invalid.yaml"
        mapping_file.write_text("just a string, not a dict", encoding="utf-8")

        processor = object.__new__(EB_Processor)
        processor.mapping_path = str(mapping_file)

        with pytest.raises(ValueError, match="Invalid mapping YAML structure"):
            processor.get_mapping_variables_codes()

    def test_get_mapping_variables_codes_handles_none_values(
        self, tmp_path: Path
    ) -> None:
        """Test get_mapping_variables_codes handles None values correctly."""
        mapping_content = {
            "siec": {
                "Missing": None,
                "Empty": [],
            },
            "nrg_bal": {
                "Test": ["FC_E"],
            },
        }
        mapping_file = tmp_path / "mapping.yaml"
        mapping_file.write_text(yaml.dump(mapping_content), encoding="utf-8")

        processor = object.__new__(EB_Processor)
        processor.mapping_path = str(mapping_file)

        result = processor.get_mapping_variables_codes()

        assert result["siec_dict"]["Missing"] == []
        assert result["siec_dict"]["Empty"] == []
