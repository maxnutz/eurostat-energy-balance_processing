from pathlib import Path
import pandas as pd
import numpy as np
import yaml
import nomenclature
import pyam


class EB_Processor:
    def __init__(
        self,
        config_path: str,
    ) -> None:
        self.config_path = config_path
        self.config = self.read_config()
        self.region = self.config["region"]
        self.validation_year = self.config["validation_year"]
        self.publication_year = np.nan
        self.definition_path = self.config["definition_path"]
        self.definitions, self.definitions_variables = self.read_definitions()
        # take default mapping path, if non is provided in config.
        default_mapping_path = Path("resources/mapping.default.yaml")
        self.mapping_path = (
            self.config["mapping_path"]
            if "mapping_path" in self.config
            else default_mapping_path
        )
        self.mapping_variables_codes = self.get_mapping_variables_codes()

    def __repr__(self):
        return (
            f"EB_Processor\n  country {self.region}\n  validation year: {self.validation_year}\n"
            + "using:\n  Energy Balance publication year: {self.publication_year}\n  definitions from: {self.definition_path}"
        )

    def read_config(self) -> dict:
        """Reads in config-file from class variable config_path."""
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)
        return config

    def read_definitions(self) -> nomenclature.DataStructureDefinition | pd.DataFrame:
        """Reads in definitions from class variable definition_path returning nomenclature.DataStructureDefinition and pandas Dataframe with variables."""
        dsd = nomenclature.DataStructureDefinition(self.definition_path)
        return dsd, dsd.variable.to_pandas()

    def get_mapping_variables_codes(self) -> dict:
        """Read mappings of Energy Balance codes to IAMC-Variables from yaml to return as dict."""


class IAMC_Creator(EB_Processor):
    def __init__(
        self,
        config_path: str,
        country: str,
        validation_year: str,
        publication_year: str,
        definition_path: str,
        definitions: dict,
    ) -> None:
        super().__init__(
            config_path,
            country,
            validation_year,
            publication_year,
            definition_path,
            definitions,
        )
        self.df_eb = self.fetch_and_load_eb_tsv()

    def fetch_and_load_eb_tsv(self) -> pd.DataFrame:
        """If needed, fetches energy balance data. Reads data from tsv file, preprocesses and returns dataframe."""

    def map_eb_codes(self) -> None:
        """Maps the Codes used in the Energy Balance to IAMC-Variables."""

    def calculate_variables(self) -> pyam.IamDataFrame:
        """Calculates the values of the defined variables using the Eurostat Energy Balance as Databasis and units defined in the variables definitions."""


class Validation_Creator(EB_Processor):
    def __init__(
        self,
        config_path: str,
        country: str,
        validation_year: str,
        publication_year: str,
        definition_path: str,
        definitions: dict,
    ) -> None:
        super().__init__(
            config_path,
            country,
            validation_year,
            publication_year,
            definition_path,
            definitions,
        )
        self.validation_definitions = self.build_validation_definitions()

    def build_validation_definitions(self) -> dict:
        """Builds a nomenclature.DataStructureDefinition for the validation criteria and returns as dict."""
