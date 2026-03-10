from pathlib import Path
import os
import re
import warnings
import gzip
import ast
from urllib.request import urlopen
import pandas as pd
import numpy as np
import yaml
import nomenclature
import pyam

from eurostat_energy_balance_processing.utils import write_to_excel, EU27_COUNTRY_CODES


class EB_Processor:
    def __init__(
        self,
        config_path: str,
    ) -> None:
        self.config_path = config_path
        self.config = self.read_config()
        self.region = self.config["region"]
        self.validation_year = self.config["validation_year"]
        self.publication_year = 2026  # TODO
        self.eb_unit = "GWh"
        self.definition_path = self.config["definition_path"]
        self.definitions, self.definitions_variables = self.read_definitions()
        # take default mapping path, if non is provided in config.
        default_mapping_path = Path("configs/mapping.default.yaml")
        self.mapping_path = (
            self.config["mapping_path"]
            if "mapping_path" in self.config
            else default_mapping_path
        )
        self.mapping_variables_codes = self.get_mapping_variables_codes()
        default_path_definitions_with_values = Path(
            f"resources/IAMC_eurostat_eb_{self.publication_year}.xlsx"
        )
        self.path_definitions_with_values = (
            Path(self.config["path_definitions_with_values"])
            if "path_definitions_with_values" in self.config
            else default_path_definitions_with_values
        )
        default_eb_input_path = Path("resources/estat_nrg_bal_c.tsv")
        self.eb_input_path = (
            Path(self.config["eb_input_path"])
            if "eb_input_path" in self.config
            else default_eb_input_path
        )

    def __repr__(self) -> str:
        return (
            f"EB_Processor\n  region: {self.region}\n  validation year: {self.validation_year}\n"
            + f"using:\n  Energy Balance publication year: {self.publication_year}\n  definitions from: {self.definition_path}"
        )

    @classmethod
    def process(cls, config_path: str) -> "IAMC_Creator | Validation_Creator":
        """Factory method to create appropriate processor based on state.

        Parameters
        ----------
        config_path : str
            Path to the configuration YAML file.

        Returns
        -------
        IAMC_Creator | Validation_Creator
            Returns IAMC_Creator if energy balance needs processing,
            Validation_Creator if already processed.
        """
        base = cls(config_path)

        if base._eb_already_processed():
            return Validation_Creator(base)
        else:
            return IAMC_Creator(base)

    def _eb_already_processed(self) -> bool:
        """Checks, if Energy Balance was already processed."""
        if os.path.exists(self.path_definitions_with_values):
            return True
        else:
            return False

    def read_config(self) -> dict:
        """Reads in config-file from class variable config_path."""
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)
        return config

    def read_definitions(
        self,
    ) -> tuple[nomenclature.DataStructureDefinition, pd.DataFrame]:
        """Reads in definitions from class variable definition_path.

        Returns
        -------
        tuple[nomenclature.DataStructureDefinition, pd.DataFrame]
            Variables definitions as DataStructureDefinition and DataFrame holding variables.
        """
        dsd = nomenclature.DataStructureDefinition(self.definition_path)
        return dsd, dsd.variable.to_pandas()

    def get_mapping_variables_codes(self) -> dict[str, dict[str, list[str]]]:
        """Read mappings of Energy Balance codes to IAMC-Variables from yaml.

        Returns
        -------
        dict[str, dict[str, list[str]]]
            Nested dict with two keys:
            - ``siec_dict``: maps IAMC carrier names to SIEC codes
            - ``nrg_dict``: maps IAMC variable templates to nrg_bal codes

        Raises
        ------
        FileNotFoundError
            If mapping file cannot be found.
        ValueError
            If YAML content is invalid.
        """
        mapping_path = Path(self.mapping_path)

        # Resolve relative path from project root (parent of package directory)
        if not mapping_path.is_absolute():
            project_root = Path(__file__).resolve().parents[1]
            mapping_path = project_root / mapping_path

        if not mapping_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping_data = yaml.safe_load(f)

        if not isinstance(mapping_data, dict):
            raise ValueError(f"Invalid mapping YAML structure in '{mapping_path}'.")

        def _import_yaml_list_to_str(value: object) -> list[str]:
            """Convert value to list of strings, handling None and single values."""
            if value is None:
                return []
            if isinstance(value, list):
                return [str(v) for v in value if v is not None]
            return [str(value)]

        siec_raw = mapping_data.get("siec", {})
        nrg_raw = mapping_data.get("nrg_bal", {})

        siec_dict: dict[str, list[str]] = {
            str(k): _import_yaml_list_to_str(v) for k, v in siec_raw.items()
        }
        nrg_dict: dict[str, list[str]] = {
            str(k): _import_yaml_list_to_str(v) for k, v in nrg_raw.items()
        }

        return {"siec_dict": siec_dict, "nrg_dict": nrg_dict}


class IAMC_Creator(EB_Processor):

    def __init__(self, parent_processor: EB_Processor) -> None:
        self.__dict__.update(parent_processor.__dict__)
        self.df_eb = None

    def run(self) -> None:
        """Executes IAMC processing."""
        print("INFO: processing energy balance...")
        self.df_eb = self.fetch_and_load_eb_tsv()
        self.df_eb_with_values = self.map_eb_codes_to_calc_values()
        self.pyam_dsd_with_values = self.structure_pyam_from_pandas(
            self.df_eb_with_values
        )
        write_to_excel(
            df=self.pyam_dsd_with_values, outputpath=self.path_definitions_with_values
        )

    def fetch_and_load_eb_tsv(self) -> pd.DataFrame:
        """
        Load and parse Eurostat energy balance TSV data.

        The function first looks for `resources/estat_nrg_bal_c.tsv`.
        If that file does not exist, it is downloaded from the Eurostat API
        and saved to the resources folder before loading.

        Parameters
        ----------
        filepath_tsv : str | None, optional
            overwrites the default filepath. If file does not exist, API download
            saves to that location.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: freq, nrg_bal, siec, unit, geo, and year columns
        """
        resource_path = self.eb_input_path
        api_url = (
            "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
            "nrg_bal_c?format=TSV&compressed=true"
        )
        if not self.eb_input_path.exists():
            warning_msg = (
                f"Eurostat Energy Balance input in '{self.eb_input_path}' not found. Downloading from Eurostat API; "
                "this can take some time..."
            )
            warnings.warn(warning_msg, UserWarning)

            resource_path.parent.mkdir(parents=True, exist_ok=True)

            with urlopen(api_url) as response:
                payload = response.read()

            # `compressed=true` returns gzip-compressed bytes.
            # Fallback to plain UTF-8 content if decompression fails.
            try:
                content = gzip.decompress(payload).decode("utf-8")
            except OSError:
                content = payload.decode("utf-8")

            resource_path.write_text(content, encoding="utf-8")

        # Read TSV file, treating the header specially
        df = pd.read_csv(resource_path, sep=",|\t", dtype=str, engine="python")

        # Strip whitespace from column names (e.g. ' 1990 ' or
        # 'geo\TIME_PERIOD')
        df.columns = [col.strip() for col in df.columns]

        # If the special combined geo column is present, rename it to 'geo'
        if "geo\\TIME_PERIOD" in df.columns and "geo" not in df.columns:
            df.rename(columns={"geo\\TIME_PERIOD": "geo"}, inplace=True)

        # Set column names properly (after renaming) for later logic
        col_names = list(df.columns)

        # Convert numeric columns to float, handling ':' as missing
        # Years are expected after the first five columns
        year_columns = col_names[5:]
        for year_col in year_columns:
            if year_col in df.columns:
                df[year_col] = pd.to_numeric(
                    df[year_col].replace(":", np.nan), errors="coerce"
                )
        df = df[df["unit"] == self.eb_unit.upper()]
        df = df[df["geo"] == self.region]
        return df

    def map_eb_codes_to_calc_values(self) -> None:
        """Maps the Codes used in the Energy Balance to IAMC-Variables."""
        year_cols = [
            col for col in self.df_eb.columns if re.fullmatch(r"\d{4}", str(col))
        ]
        if not year_cols:
            raise ValueError("No year columns found in eb_df.")

        def _get_variable_list(df_variables: pd.DataFrame) -> list[str]:
            if "variable" in df_variables.columns:
                return df_variables["variable"].astype(str).tolist()
            else:
                raise ValueError(
                    "Dataset holding variable definitions is not of valid nomenclature.DataStructureDefinition.variable - structure."
                )

        def _match_nrg_template(
            variable_name: str, mapping: dict[str, list[str]]
        ) -> tuple[str | None, dict[str, str]]:
            """Matching Energy Balance NRG-codes to part-definitions of IAMC-Variables."""
            for template in mapping:
                pattern = "^" + re.escape(template) + "$"
                placeholders = re.findall(r"\{([^}]+)\}", template)
                for placeholder in placeholders:
                    pattern = pattern.replace(
                        r"\{" + re.escape(placeholder) + r"\}", r"(.+?)", 1
                    )

                match = re.match(pattern, variable_name)
                if match:
                    values = {
                        placeholder: match.group(i + 1)
                        for i, placeholder in enumerate(placeholders)
                    }
                    return template, values

            return None, {}

        def _get_siec_codes(placeholder_values: dict[str, str]) -> list[str] | None:
            siec_codes: list[str] = []

            for placeholder, value in placeholder_values.items():
                if placeholder in {
                    "Final Energy Carrier",
                    "Electricity Generation by Source",
                }:
                    codes = self.mapping_variables_codes["siec_dict"].get(value, None)
                    if codes is None:
                        continue
                    if not codes:
                        continue
                    if codes == [None]:
                        return None
                    siec_codes.extend([code for code in codes if code is not None])
            return sorted(set(siec_codes))

        def _calculate_single_variable(variable_name: str) -> pd.Series:
            """
            Calculate the values of a single variable by matching the variable name to NRG-codes.

            Parameters
            ----------
            variable_name : str
                The name of the variable to be calculated.

            Returns
            -------
            pd.Series
                A pandas Series containing the calculated values of the variable.

            Notes
            -----
            This function uses a combination of regular expressions and dictionary lookups to
            match the variable name to NRG-codes, and then uses these codes to subset the
            Eurostat Energy Balance data and calculate the values of the variable. If no
            matching NRG-codes are found, the function returns a pandas Series with NaN values.
            """
            template, placeholder_values = _match_nrg_template(
                variable_name, self.mapping_variables_codes["nrg_dict"]
            )
            if template is None:
                return pd.Series(np.nan, index=year_cols, dtype=float)

            nrg_codes = self.mapping_variables_codes["nrg_dict"].get(template, [])
            if not nrg_codes:
                return (pd.Series(np.nan, index=year_cols, dtype=float),)

            siec_codes = _get_siec_codes(placeholder_values)
            if siec_codes is None:
                return (pd.Series(np.nan, index=year_cols, dtype=float),)

            if not siec_codes:
                siec_codes = ["TOTAL"]

            result = pd.Series(0.0, index=year_cols, dtype=float)
            has_data = False

            for code in nrg_codes:
                sign = -1.0 if str(code).startswith("-") else 1.0
                clean_code = str(code).lstrip("-")

                subset = self.df_eb.loc[self.df_eb["nrg_bal"] == clean_code].copy()
                if siec_codes:
                    subset = subset.loc[subset["siec"].isin(siec_codes)]

                if subset.empty:
                    continue

                values = (
                    subset[year_cols]
                    .apply(pd.to_numeric, errors="coerce")
                    .sum(axis=0, min_count=1)
                )
                result = result.add(sign * values, fill_value=np.nan)
                has_data = True

            if not has_data:
                return pd.Series(np.nan, index=year_cols, dtype=float)

            return result

        variable_list = _get_variable_list(self.definitions_variables)

        calculated_records: list[dict[str, object]] = []
        for variable in variable_list:
            value_series = _calculate_single_variable(variable)
            record = {"variable": variable, **value_series.to_dict()}
            calculated_records.append(record)

        calculated_values_df = pd.DataFrame(calculated_records).set_index("variable")

        df = self.definitions_variables.merge(
            calculated_values_df, on="variable", how="left"
        )
        df["unit"] = [self.eb_unit] * len(df)
        return df

    def structure_pyam_from_pandas(self, df: pd.DataFrame) -> pyam.IamDataFrame:
        """Create pyam.IamDataFrame from pandas DataFrame including units-conversion."""

        # column renaming
        col_renaming_dict = {
            "variable": "variable_name",
            "unit": "unit_EB",
        }
        df = df.rename(
            columns={k: v for k, v in col_renaming_dict.items() if k in df.columns}
        )

        # create columns to drop
        columns_to_drop = [col for col in df.columns if col in ["EB", "note", "crf"]]
        if columns_to_drop:
            df = df.drop(columns=columns_to_drop)
        dsd = pyam.IamDataFrame(
            data=df.drop_duplicates(),
            model=f"Eurostat Energy Balance {self.publication_year}",
            scenario="Historical Reference",
            region=EU27_COUNTRY_CODES[self.region],
            variable="variable_name",
            unit="unit_EB",
        )

        variable_unit_defs = (
            self.definitions_variables[["variable", "unit"]]
            .drop_duplicates(subset=["variable"])
            .copy()
        )
        target_unit_map: dict[str, str] = {}

        def _first_unit(unit_value: object) -> str | None:
            if unit_value is None:
                return None
            if isinstance(unit_value, list):
                first = unit_value[0]
                return None if pd.isna(first) else str(first)
            elif isinstance(unit_value, str):
                stripped = unit_value.strip()
                if not stripped:
                    return None
                if stripped.startswith("[") and stripped.endswith("]"):
                    parsed = ast.literal_eval(stripped)
                    if isinstance(parsed, list):
                        if not parsed:
                            return None
                        first = parsed[0]
                        return None if pd.isna(first) else str(first)
                else:
                    return stripped

        for _, row in variable_unit_defs.iterrows():
            target_unit = _first_unit(row["unit"])
            if target_unit is not None:
                target_unit_map[row["variable"]] = target_unit

        converted_df = dsd
        pairs_to_check = converted_df.as_pandas()[
            ["variable", "unit"]
        ].drop_duplicates()

        failed_conversion: list[tuple[str, str, str]] = []

        for _, pair in pairs_to_check.iterrows():
            variable_name = str(pair["variable"])
            current_unit = str(pair["unit"])
            target_unit = target_unit_map.get(variable_name)

            if target_unit is None or current_unit == target_unit:
                continue
            subset = converted_df.filter(variable=variable_name, unit=current_unit)
            remainder = converted_df.filter(
                variable=variable_name, unit=current_unit, keep=False
            )
            try:
                subset_converted = subset.convert_unit(
                    current=current_unit, to=target_unit, inplace=False
                )
                converted_df = pyam.concat([remainder, subset_converted])
            except Exception:
                converted_df = converted_df
                failed_conversion.append((variable_name, current_unit, target_unit))

        if len(failed_conversion) > 0:
            print(f"WARNING: {len(failed_conversion)} failed unit conversions:")
            print(failed_conversion)

        return converted_df


class Validation_Creator(EB_Processor):

    def __init__(self, parent_processor: EB_Processor) -> None:
        self.__dict__.update(parent_processor.__dict__)
        self.pyam_dsd_with_values = self._load_pyam_data()
        self.validation_definitions = self.build_validation_definitions()
        self.path_codelist_yaml = (
            self.path_definitions_with_values.parents[0] / "validate_data.yaml"
        )

    def run(self) -> None:
        """Executes the Creation of validation definitions."""
        print("INFO: creating validation definitions...")
        self.validation_codelist = self.build_validation_definitions()
        self.write_to_codelist_yaml()

    def _load_pyam_data(self) -> pyam.IamDataFrame:
        """
        Load pyam IamDataFrame from existing attribute or from file.

        If `self.pyam_dsd_with_values` already exists and is a pyam.IamDataFrame,
        return it. Otherwise, read from the Excel file created by IAMC_Creator.

        Returns
        -------
        pyam.IamDataFrame
            The loaded or existing IamDataFrame with calculated values.

        Raises
        ------
        FileNotFoundError
            If the Excel file does not exist.
        """
        if hasattr(self, "pyam_dsd_with_values") and isinstance(
            self.pyam_dsd_with_values, pyam.IamDataFrame
        ):
            return self.pyam_dsd_with_values

        if not self.path_definitions_with_values.exists():
            raise FileNotFoundError(
                f"IAMC output file not found: {self.path_definitions_with_values} "
                "and value not set. Class structure should prevent this..."
            )
        return pyam.IamDataFrame(self.path_definitions_with_values)

    def _get_variable_tolerances(
        self,
        variable_name: str,
        warning_levels: list[str],
        default_tolerances: dict[str, float],
        sector_tolerances: dict[str, dict[str, float]],
        carrier_tolerances: dict[str, dict[str, float]],
    ) -> list[dict[str, str | float]]:
        """
        Determine tolerances for a variable across all warning levels.

        Priority: sector > carrier > default.

        Parameters
        ----------
        variable_name : str
            The IAMC variable name (e.g., "Primary Energy|Gas").
        warning_levels : list[str]
            All warning levels to include (e.g., ["low", "medium", "high", "error"]).
        default_tolerances : dict[str, float]
            Default tolerance values per warning level.
        sector_tolerances : dict[str, dict[str, float]]
            Sector-specific tolerances keyed by sector name.
        carrier_tolerances : dict[str, dict[str, float]]
            Carrier-specific tolerances keyed by carrier name.

        Returns
        -------
        list[dict[str, str | float]]
            List of dicts with "warning_level" and "rtol" keys.
        """
        # Extract carriers from variable name (parts between "|")
        variable_parts = variable_name.split("|")

        result: list[dict[str, str | float]] = []

        for level in warning_levels:
            # Start with default tolerance
            rtol = default_tolerances.get(level)

            # Check for carrier-specific tolerance (exact match)
            for carrier, carrier_tols in carrier_tolerances.items():
                if carrier in variable_parts:
                    if level in carrier_tols:
                        rtol = carrier_tols[level]
                    break

            # Check for sector-specific tolerance (startswith) - overrides carrier
            for sector, sector_tols in sector_tolerances.items():
                if variable_name.startswith(sector):
                    if level in sector_tols:
                        rtol = sector_tols[level]
                    break

            if rtol is not None:
                result.append({"warning_level": level, "rtol": rtol})

        return result

    def build_validation_definitions(self) -> list[dict]:
        """
        Build validation definitions for all variables.

        Creates validation entries in the following structure:
        - variable: <variable_name>
          year: <self.validation_year>
          value: <calculated value for that year>
          validation:
            - warning_level: <level>
              rtol: <tolerance value>

        Tolerances are determined by priority:
        1. Sector-specific (variable starts with sector name)
        2. Carrier-specific (exact carrier match between "|")
        3. Default from validation_tolerance

        Sector tolerances override carrier tolerances for the same warning level.

        Returns
        -------
        list[dict]
            List of validation definition dicts ready to be written to YAML.
        """
        # Get tolerance configurations from config
        default_tolerances: dict[str, float] = self.config.get(
            "validation_tolerance", {}
        )
        sector_tolerances: dict[str, dict[str, float]] = (
            self.config.get("validation_tolerance_sector", {}) or {}
        )
        carrier_tolerances: dict[str, dict[str, float]] = (
            self.config.get("validation_tolerance_carrier", {}) or {}
        )

        # Get all warning levels from default tolerances
        warning_levels = list(default_tolerances.keys())

        # Get data for validation year
        df = self.pyam_dsd_with_values.filter(year=self.validation_year).as_pandas()

        validation_list: list[dict] = []

        for _, row in df.iterrows():
            variable_name = str(row["variable"])
            value = row["value"]

            # Skip if value is NaN
            if pd.isna(value):
                continue

            # Build tolerances for this variable
            variable_tolerances = self._get_variable_tolerances(
                variable_name=variable_name,
                warning_levels=warning_levels,
                default_tolerances=default_tolerances,
                sector_tolerances=sector_tolerances,
                carrier_tolerances=carrier_tolerances,
            )

            # Build validation entry
            validation_entry = {
                "variable": variable_name,
                "year": self.validation_year,
                "value": float(value),
                "validation": variable_tolerances,
            }
            validation_list.append(validation_entry)

        return validation_list

    def write_to_codelist_yaml(self) -> None:
        """
        Write validation codelist to YAML file.

        Writes self.validation_codelist in the following structure:
        - variable: <variable_name>
          year: <year>
          value: <value>
          validation:
            - warning_level: <level>
              rtol: <tolerance>
        """
        with open(self.path_codelist_yaml, "w") as f:
            yaml.dump(
                self.validation_codelist,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
