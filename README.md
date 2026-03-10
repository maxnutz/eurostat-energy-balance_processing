![Python](https://img.shields.io/badge/python-3.11-blue)  [![license](https://img.shields.io/badge/License-MIT-blue)](https://github.com/maxnutz/eurostat-energy-balance_processing/blob/master/LICENSE) [![Tests](https://github.com/maxnutz/eurostat-energy-balance_processing/actions/workflows/tests.yml/badge.svg)](https://github.com/maxnutz/eurostat-energy-balance_processing/actions/workflows/tests.yml)

# Eurostat Energy Balance - processing

This repository is licensed under the [MIT License](LICENSE).

> [!NOTE]  
> This package is currently in an **early state of development**. Expect ongoing changes and updates. Documentation and Readme will be continuously updated with changes.

This package processes the Eurostat Energy Balance for a given set of defined IAMC-Variables to build a structured timeseries output and data basis for energy system model validation against the Eurostat Energy Balance.

## Quick start

### Installation

```bash
pip install .
```
### Project environment 
- use conda environment with
```bash
conda env create -f environment.yml
conda activate pyam
```

- use pixi environment by adding `pixi run` before statements in cli 

> [!WARNING]
> pixi environment ist not stable at the moment, eventually, nomenclature needs to be added manually to the pixi environment with `pixi run pip install nomenclature-iamc`

### Config
- General section: 
    - region: one of EU-27 countries, list of valid entries to be found [here](https://github.com/maxnutz/eurostat-energy-balance_processing/blob/e513c6bda1ee25c1e73eba4de1685f1c716511b2/eurostat_energy_balance_processing/utils.py#L25)
    - validation_year: year to be used to extract the data from for the validation outputs
    - definition_path: folderpath to variables definition-folder. no default!
    - mapping_path: filepath to yaml-file including the mapping of Eurostat codes to IAMC-Variable-parts. _defaults to config/mapping.default.yaml_
- validation tolerance: general validation tolerances to be used for all variables. [low, medium, high, error] refers to the respective warning levels.
- validation tolerance sector: overwrites the default validation tolerance for a specific sector
- validation tolerance carrier: overwrites the default validation tolerance for a specific carrier. 

> When special sector AND carrier tolerances are given, the sector tolerances overwrite the carrier tolerances.

### Run evaluation
The evaluation is executed from the file `workflow.py`:
```bash
python workflow.py
``` 
It is organized in two steps: 
- **Map Eurostat Energy Balance to IAMC-format:** Retrieve Eurostat Energy Balance from API, apply codes-mapping and calculate variables values. Writes an IAMC-formatted xlsx-files as output.
- **Create basis for validation:** Create valid nomenclature-yaml-file for validation purpose.

### Run tests

```bash
conda run -n pyam pytest tests/ -v
``` 

## Project structure

- Package code: `eurostat_energy_balance_processing/`
- Packaged default config: `configs/config.default.yaml`
- User/project configs: `configs/`
- Tests: `tests/`
- Versioned resources: `resources/`
- Non-versioned input and output files: `data/`



 



