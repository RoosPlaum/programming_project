# Effects of the 100 km/h Daytime Speed Limit on Traffic Safety on Dutch Motorways

TIL6022 Python Programming — group project (group 3).

On 16 March 2020 the daytime speed limit (06:00–19:00) on most Dutch motorways was lowered from
120/130 km/h to 100 km/h. This project investigates how registered accidents and accident rates
changed on the affected motorway sections, compared with sections where the limit did not change.
Accidents are linked to road sections and traffic volumes, and the change is estimated with
difference-in-differences and event-study Poisson models, split by accident severity and light condition.

## Data

| Dataset | Source | Used for |
|---|---|---|
| BRON (registered accidents + road network NWB), 2018–2025 | <https://downloads.rijkswaterstaatdata.nl/bron/> | accidents, severity, light condition, speed limit, location |
| INWEVA (traffic volumes per road section), 2023–2025 | <https://downloads.rijkswaterstaatdata.nl/inweva/> | road sections and vehicle-kilometres (the 2023 release contains 2018–2023) |

The data is **not** stored in this repository (several GB). It is public and is downloaded with
`download_data.py`.

## How to run

1. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

2. Download and unpack the data into `data/` (several GB, takes a while the first time; years that are
   already present are skipped):

   ```bash
   python download_data.py
   ```

3. Open `data_exploration_Teun.ipynb` and run all cells (Kernel → Restart & Run All). The notebook links
   the accidents to the road sections and produces all figures and tables of the report.

4. Optional: draw the map of treated and comparison sections (Figure 1). The map is saved in `figures/`.

   ```bash
   python map_sections.py
   ```

## Files

| File | Content |
|---|---|
| `data_exploration_Teun.ipynb` | main notebook: data preparation, linking, classification and all analyses (sub-questions 1–4) |
| `download_data.py` | downloads and unpacks BRON and INWEVA |
| `map_sections.py` | map of treated and comparison motorway sections (Figure 1) |
| `nl_outline.txt` | outline of the Netherlands used by `map_sections.py` (CBS/PDOK) |
| `project_proposal.ipynb` / `.html` | project proposal |
| `requirements.txt` | required Python packages |

## Authors

Meike Rademaker, Harmen Schutte, Teun Quaadvliet, Lieke van Essenberg and Roos Plaum.
The contribution of each author is described in the appendix of the report.
