# -*- coding: utf-8 -*-
# Pre-genera griglie batimetriche EMODnet (zone predefinite + Mediterraneo) come binari Int16 + manifest.
# Sorgente: EMODnet Bathymetry WCS (coverage emodnet__mean, EPSG:4326, assi "Lat Long", ris. nativa ~0.00104 deg).
import os, json, urllib.request, ssl, io
import numpy as np
from PIL import Image

OUT = os.path.dirname(os.path.abspath(__file__))
WCS = "https://ows.emodnet-bathymetry.eu/wcs"
NATIVE = 0.0010416666666666667
ctx = ssl.create_default_context()
NODATA = 32767  # sentinella Int16 per NaN/terra-non-valida

# Zone predefinite del Mediterraneo (box <= ~10 deg^2 per stare sotto il limite EMODnet di 97.66 MB/richiesta)
# (chiave, nome, latS, latN, lonW, lonE, maxpx)
ZONES = [
    ("tirreno",  "Mar Tirreno (centro)",      39.5, 42.5, 10.0, 13.5, 320),
    ("adriatico","Mar Adriatico (centro)",    42.0, 45.0, 13.0, 16.0, 320),
    ("ionio",    "Mar Ionio",                 37.0, 40.0, 16.5, 19.5, 320),
    ("ligure",   "Mar Ligure",                43.0, 44.3,  7.5, 10.0, 320),
    ("sardo",    "Mare di Sardegna (E)",      39.0, 41.5,  7.8, 10.3, 320),
    ("sicilia",  "Canale di Sicilia",         36.0, 38.0, 11.5, 14.5, 320),
]

def fetch(latS, latN, lonW, lonE, maxpx):
    dlon, dlat = lonE - lonW, latN - latS
    sf = min(maxpx / (dlon / NATIVE), maxpx / (dlat / NATIVE), 1.0)
    url = (f"{WCS}?service=WCS&version=2.0.1&request=GetCoverage&coverageId=emodnet__mean"
           f"&format=image/tiff&subset=Lat({latS},{latN})&subset=Long({lonW},{lonE})"
           f"&scalefactor={sf:.5f}")
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MareNav3D/1.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=180) as r:
                blob = r.read()
            im = Image.open(io.BytesIO(blob))
            a = np.array(im).astype("float64")      # riga 0 = Nord
            a[(a < -11000) | (a > 9000)] = np.nan
            return a
        except Exception as e:
            last = e
            import time; time.sleep(2)
    raise last

manifest = {"zones": []}
for key, nome, latS, latN, lonW, lonE, maxpx in ZONES:
    try:
        a = fetch(latS, latN, lonW, lonE, maxpx)
    except Exception as e:
        print(f"ERR {key}: {repr(e)[:120]}"); continue
    nrows, ncols = a.shape
    z = a.copy()
    z[~np.isfinite(z)] = NODATA
    z = np.clip(np.round(z), -32766, 32766).astype("<i2")
    z[np.array(np.isnan(a))] = NODATA
    z.tofile(os.path.join(OUT, f"{key}.bin"))
    sea = np.isfinite(a) & (a < 0)
    manifest["zones"].append({
        "key": key, "nome": nome,
        "latN": round(latN, 5), "latS": round(latS, 5), "lonW": round(lonW, 5), "lonE": round(lonE, 5),
        "rows": int(nrows), "cols": int(ncols), "nodata": NODATA,
        "depth_min": int(np.nanmin(a)) if np.isfinite(a).any() else None,
        "predef": key != "med",
        "bytes": int(z.nbytes),
    })
    print(f"OK {key:10s} {ncols}x{nrows}  {z.nbytes//1024:5d} KB  prof_min {int(np.nanmin(a))} m  mare%{round(100*sea.mean())}")

json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"), indent=1)
tot = sum(z["bytes"] for z in manifest["zones"]) // 1024
print(f"\nmanifest.json scritto, {len(manifest['zones'])} griglie, totale {tot} KB")
