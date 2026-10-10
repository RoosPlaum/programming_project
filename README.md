# Effects of the 100 km/h Daytime Speed Limit on Traffic Safety on Dutch Motorways

TIL6022 Python Programming — group project.

On 16 March 2020 the daytime speed limit (06:00–19:00) on most Dutch motorways was lowered from
120/130 km/h to 100 km/h. This project investigates how registered accidents and accident rates
changed on the affected motorway sections, compared with sections where the limit did not change.

## Data

| Dataset | Source | Used for |
|---|---|---|
| BRON (registered accidents + road network NWB), 2018–2025 | <https://downloads.rijkswaterstaatdata.nl/bron/> | accidents, severity, light condition, location |
| INWEVA (traffic volumes per road section), 2023–2025 | <https://downloads.rijkswaterstaatdata.nl/inweva/> | road sections and vehicles per day |

The data is **not** stored in this repository (several GB). It is downloaded automatically.

## How to run

```bash
pip install -r requirements.txt
```

Open `data_exploration.ipynb` and run all cells. The first cell downloads the data to `data/`
if it is not there yet (several GB, takes a while the first time; years already present are skipped).

The data can also be downloaded separately:

```bash
python download_data.py
```

## Files

| File | Content |
|---|---|
| `data_exploration.ipynb` | loads the data, selects motorway accidents and links them to INWEVA road sections |
| `download_data.py` | downloads and unpacks BRON and INWEVA |
| `project_proposal.ipynb` / `.html` | project proposal |

## Authors

[names]
