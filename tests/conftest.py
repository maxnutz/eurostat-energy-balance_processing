"""Shared pytest fixtures for eurostat_energy_balance_processing tests.

This module provides synthetic test data fixtures to enable comprehensive testing
without relying on real data files or external dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mock_config_dict() -> dict[str, Any]:
    """Minimal configuration dictionary with all required keys.

    Returns
    -------
    dict[str, Any]
        Configuration dictionary for EB_Processor initialization.
    """
    return {
        "region": "AT",
        "validation_year": 2020,
        "definition_path": "/tmp/test_definitions",
        "validation_tolerance": {
            "low": 0.3,
            "medium": 0.4,
            "high": 0.5,
            "error": 1.0,
        },
        "validation_tolerance_sector": {
            "Final Energy": {"low": 0.05},
        },
        "validation_tolerance_carrier": {
            "Electricity": {"low": 0.03},
        },
    }


@pytest.fixture
def mock_config_file(tmp_path: Path, mock_config_dict: dict[str, Any]) -> Path:
    """Write config dictionary to a temporary YAML file.

    Parameters
    ----------
    tmp_path : Path
        pytest's built-in temporary directory fixture.
    mock_config_dict : dict
        The mock configuration dictionary.

    Returns
    -------
    Path
        Path to the created config file.
    """
    import yaml

    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")
    return config_file


@pytest.fixture
def mock_mapping_dict() -> dict[str, dict[str, list[str]]]:
    """Synthetic SIEC and NRG_BAL mappings.

    Returns
    -------
    dict[str, dict[str, list[str]]]
        Dictionary with 'siec' and 'nrg_bal' mappings.
    """
    return {
        "siec": {
            "Coal": ["C0000X0350-0370", "P1000"],
            "Electricity": ["E7000"],
            "Natural Gas": ["G3000"],
            "Oil": ["O4000XBIO"],
        },
        "nrg_bal": {
            "Final Energy": ["FC_E"],
            "Final Energy [by Carrier]|{Final Energy Carrier}": ["FC_E"],
            "Net Imports|{Final Energy Carrier}": ["IMP", "-EXP"],
        },
    }


@pytest.fixture
def mock_mapping_file(tmp_path: Path, mock_mapping_dict: dict) -> Path:
    """Write mapping dictionary to a temporary YAML file.

    Parameters
    ----------
    tmp_path : Path
        pytest's built-in temporary directory fixture.
    mock_mapping_dict : dict
        The mock mapping dictionary.

    Returns
    -------
    Path
        Path to the created mapping file.
    """
    import yaml

    mapping_file = tmp_path / "mapping.yaml"
    mapping_file.write_text(yaml.dump(mock_mapping_dict), encoding="utf-8")
    return mapping_file


@pytest.fixture
def mock_definitions_variables_df() -> pd.DataFrame:
    """Minimal DataFrame with variable and unit columns.

    Returns
    -------
    pd.DataFrame
        DataFrame mimicking nomenclature variable definitions.
    """
    return pd.DataFrame(
        {
            "variable": [
                "Final Energy",
                "Final Energy [by Carrier]|Electricity",
                "Final Energy [by Carrier]|Natural Gas",
                "Net Imports|Electricity",
            ],
            "unit": ["GWh", "GWh", "GWh", "GWh"],
        }
    )


@pytest.fixture
def mock_nomenclature_dsd(
    mock_definitions_variables_df: pd.DataFrame,
) -> MagicMock:
    """Mock nomenclature.DataStructureDefinition class.

    Parameters
    ----------
    mock_definitions_variables_df : pd.DataFrame
        The mock definitions DataFrame.

    Returns
    -------
    MagicMock
        Mocked DataStructureDefinition object.
    """
    mock_dsd = MagicMock()
    mock_variable = MagicMock()
    mock_variable.to_pandas.return_value = mock_definitions_variables_df
    mock_dsd.variable = mock_variable
    return mock_dsd


@pytest.fixture
def mock_eb_dataframe() -> pd.DataFrame:
    """Minimal Eurostat Energy Balance DataFrame with test data.

    Returns
    -------
    pd.DataFrame
        DataFrame mimicking Eurostat energy balance structure.
    """
    return pd.DataFrame(
        {
            "freq": ["A", "A", "A", "A", "A", "A"],
            "nrg_bal": ["FC_E", "FC_E", "FC_E", "IMP", "EXP", "FC_E"],
            "siec": ["E7000", "G3000", "TOTAL", "E7000", "E7000", "O4000XBIO"],
            "unit": ["GWH", "GWH", "GWH", "GWH", "GWH", "GWH"],
            "geo": ["AT", "AT", "AT", "AT", "AT", "AT"],
            "2019": [100.0, 200.0, 500.0, 150.0, 50.0, 100.0],
            "2020": [110.0, 210.0, 520.0, 160.0, 55.0, 110.0],
            "2021": [120.0, 220.0, 540.0, 170.0, 60.0, 120.0],
        }
    )


@pytest.fixture
def mock_pyam_iamdf() -> MagicMock:
    """Mock pyam.IamDataFrame with filter and as_pandas methods.

    Returns
    -------
    MagicMock
        Mocked IamDataFrame object.
    """
    mock_iamdf = MagicMock()

    # Create mock DataFrame for as_pandas return
    mock_df = pd.DataFrame(
        {
            "model": ["Eurostat Energy Balance 2026"] * 3,
            "scenario": ["Historical Reference"] * 3,
            "region": ["Austria"] * 3,
            "variable": ["Final Energy", "Final Energy [by Carrier]|Electricity", "Primary Energy"],
            "unit": ["GWh", "GWh", "GWh"],
            "year": [2020, 2020, 2020],
            "value": [520.0, 110.0, 1000.0],
        }
    )

    # Configure filter to return a mock that also has as_pandas
    filtered_mock = MagicMock()
    filtered_mock.as_pandas.return_value = mock_df
    mock_iamdf.filter.return_value = filtered_mock
    mock_iamdf.as_pandas.return_value = mock_df

    return mock_iamdf


@pytest.fixture
def mock_pyam_iamdf_with_nan() -> MagicMock:
    """Mock pyam.IamDataFrame with NaN values for testing skipping.

    Returns
    -------
    MagicMock
        Mocked IamDataFrame with NaN in value column.
    """
    mock_iamdf = MagicMock()

    mock_df = pd.DataFrame(
        {
            "model": ["Eurostat Energy Balance 2026"] * 3,
            "scenario": ["Historical Reference"] * 3,
            "region": ["Austria"] * 3,
            "variable": ["Final Energy", "Final Energy [by Carrier]|Electricity", "Missing Variable"],
            "unit": ["GWh", "GWh", "GWh"],
            "year": [2020, 2020, 2020],
            "value": [520.0, 110.0, np.nan],
        }
    )

    filtered_mock = MagicMock()
    filtered_mock.as_pandas.return_value = mock_df
    mock_iamdf.filter.return_value = filtered_mock

    return mock_iamdf


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory.

    Returns
    -------
    Path
        Path to the project root.
    """
    return Path(__file__).resolve().parents[1]
