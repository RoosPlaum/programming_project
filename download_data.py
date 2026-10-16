"""Download en uitpakken van de data van de downloadserver van Rijkswaterstaat.

- BRON (geregistreerde ongevallen + wegennet) 2018-2025  -> data/BRON/01-01-JJJJ_31-12-JJJJ/
- INWEVA (verkeersintensiteiten) 2023-2025               -> data/INWEVA/INWEVA_JJJJ/
  (het historie-bestand van INWEVA 2023 bevat al 2018-2023)

Jaren die al uitgepakt zijn worden overgeslagen, dus je kunt dit veilig vaker uitvoeren.

Gebruik in een notebook:   from download_data import download_alles; download_alles()
Gebruik in de terminal:    python download_data.py
"""
import shutil
import zipfile
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent / "data"

BRON_JAREN = range(2018, 2026)
INWEVA_JAREN = range(2023, 2026)

BRON_URL = "https://downloads.rijkswaterstaatdata.nl/bron/01-01-{jaar}_31-12-{jaar}.zip"
INWEVA_URL = "https://downloads.rijkswaterstaatdata.nl/inweva/INWEVA_{jaar}.zip"


def download(url, zip_pad):
    """Download een bestand in stukjes en laat de voortgang zien."""
    zip_pad.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        totaal = int(r.headers.get("content-length", 0))
        klaar = 0
        with open(zip_pad, "wb") as f:
            for stuk in r.iter_content(chunk_size=1 << 20):   # stukjes van 1 MB
                f.write(stuk)
                klaar += len(stuk)
                if totaal:
                    print(f"\r  {zip_pad.name}: {klaar / 1e6:.0f} / {totaal / 1e6:.0f} MB", end="", flush=True)
    print()


def pak_uit(zip_pad, doelmap):
    """Pak een zip uit in doelmap. Zit alles in één map met dezelfde naam, dan wordt die map weggehaald."""
    doelmap.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_pad) as z:
        for naam in z.namelist():   # veiligheidscheck: niets buiten de doelmap uitpakken
            if not (doelmap / naam).resolve().is_relative_to(doelmap.resolve()):
                raise ValueError(f"Onveilig pad in {zip_pad.name}: {naam}")
        z.extractall(doelmap)
    inhoud = [p for p in doelmap.iterdir() if p.name != "__MACOSX"]
    if len(inhoud) == 1 and inhoud[0].is_dir() and inhoud[0].name == doelmap.name:
        for item in inhoud[0].iterdir():
            shutil.move(str(item), doelmap / item.name)
        inhoud[0].rmdir()


def haal_op(url, doelmap):
    if doelmap.is_dir():
        print(f"{doelmap.name}: al aanwezig, overgeslagen")
        return
    zip_pad = doelmap.parent / f"{doelmap.name}.zip"
    print(f"{doelmap.name}: downloaden van {url}")
    download(url, zip_pad)
    print(f"{doelmap.name}: uitpakken")
    pak_uit(zip_pad, doelmap)
    zip_pad.unlink()   # zip weggooien na uitpakken


def download_alles():
    for jaar in BRON_JAREN:
        haal_op(BRON_URL.format(jaar=jaar), DATA / "BRON" / f"01-01-{jaar}_31-12-{jaar}")
    for jaar in INWEVA_JAREN:
        haal_op(INWEVA_URL.format(jaar=jaar), DATA / "INWEVA" / f"INWEVA_{jaar}")


if __name__ == "__main__":
    download_alles()
