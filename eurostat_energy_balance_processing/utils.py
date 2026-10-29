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


# Eurostat geo codes that differ from ISO 3166-1 alpha-2 (used by PyPSA)
EUROSTAT_TO_ISO_COUNTRY_CODES = {
    "EL": "GR",
    "UK": "GB",
}

INDUSTRY_NON_ENERGY_SIEC = {
    "Natural Gas": "G3000",
    "Oil": "O4000XBIO",
    "Coal": "C0000X0350-0370",
}

# Balance of the non-energy use per carrier. Eurostat reports no industrial
# non-energy use (FC_IND_NE) for solid fossil fuels, so for coal the
# non-energy use of all sectors (FC_NE) is used.
INDUSTRY_NON_ENERGY_BALANCE = {
    "Natural Gas": "FC_IND_NE",
    "Oil": "FC_IND_NE",
    "Coal": "FC_NE",
}


def calculate_industry_non_energy_shares(df_eb: pd.DataFrame) -> pd.DataFrame:
    """Calculate the non-energy share of industrial final consumption.

    The share is ``NE / (FC_IND_E + NE)`` per country, carrier and year for
    the carriers in ``INDUSTRY_NON_ENERGY_SIEC``, with ``NE`` the balance in
    ``INDUSTRY_NON_ENERGY_BALANCE`` (``FC_IND_NE``; ``FC_NE`` for coal).
    Combinations with a missing value or a zero denominator are dropped.

    Parameters
    ----------
    df_eb
        Energy balance as returned by ``IAMC_Creator.fetch_and_load_eb_tsv``
        (columns ``nrg_bal``, ``siec``, ``unit``, ``geo`` and one column per year),
        in a single unit.

    Returns
    -------
    pd.DataFrame
        Long table with columns ``country``, ``carrier``, ``siec``, ``year``,
        ``unit``, ``energy_use``, ``non_energy_use``, ``non_energy_share``.
    """
    year_columns = [col for col in df_eb.columns if str(col).isdigit()]
    siec_to_carrier = {v: k for k, v in INDUSTRY_NON_ENERGY_SIEC.items()}
    df = df_eb[df_eb["siec"].isin(siec_to_carrier)]
    non_energy_balance = (
        df["siec"].map(siec_to_carrier).map(INDUSTRY_NON_ENERGY_BALANCE)
    )
    df = df[(df["nrg_bal"] == "FC_IND_E") | (df["nrg_bal"] == non_energy_balance)]
    df = df.assign(nrg_bal=df["nrg_bal"].where(df["nrg_bal"] == "FC_IND_E", "NE"))
    long = df.melt(
        id_vars=["nrg_bal", "siec", "unit", "geo"],
        value_vars=year_columns,
        var_name="year",
    )
    wide = long.pivot_table(
        index=["geo", "siec", "unit", "year"],
        columns="nrg_bal",
        values="value",
        aggfunc="first",
    ).reindex(columns=["FC_IND_E", "NE"])
    total = wide["FC_IND_E"] + wide["NE"]
    wide["non_energy_share"] = wide["NE"] / total.where(total != 0)
    wide = wide.dropna().reset_index()
    result = pd.DataFrame(
        {
            "country": wide["geo"],
            "carrier": wide["siec"].map(siec_to_carrier),
            "siec": wide["siec"],
            "year": wide["year"].astype(int),
            "unit": wide["unit"],
            "energy_use": wide["FC_IND_E"],
            "non_energy_use": wide["NE"],
            "non_energy_share": wide["non_energy_share"],
        }
    )
    return result.sort_values(["country", "carrier", "year"]).reset_index(drop=True)


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
