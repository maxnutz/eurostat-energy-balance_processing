from pathlib import Path
import pandas as pd
import pyam


def write_to_excel(
    df: pyam.IamDataFrame | pd.DataFrame, outputpath: str | Path
) -> None:
    """Writes pyam.IamDataFrame or pandas DataFrameto an Excel file."""
    if isinstance(outputpath, str):
        outputpath = Path(outputpath)
    if not str(outputpath).endswith(".xlsx"):
        outputpath = outputpath.with_suffix(".xlsx")
        print(f"WARNING: adapted outputpath to {outputpath} for xlsx-suffix.")
    if outputpath.exists():
        print(f"INFO: overwrite existing file in {outputpath}.")
    if isinstance(df, pyam.IamDataFrame):
        df.to_excel(outputpath)
        print("IamDataFrame written to", outputpath)
    elif isinstance(df, pd.DataFrame):
        df.to_excel(outputpath)
        print("DataFrame written to", outputpath)
    else:
        raise TypeError(
            f"Unsupported type of dataframe: {type(df)}. Expected one of pyam.IamDataFrame or pd.DataFrame."
        )


EU27_COUNTRY_CODES = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GR": "Greece",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IT": "Italy",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MT": "Malta",
    "NL": "Netherlands",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SE": "Sweden",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "EU27_{year}": "EU27",
}
