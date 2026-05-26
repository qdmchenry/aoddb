#!/usr/bin/env python
from __future__ import print_function, unicode_literals
import sys
import os
import requests
from datetime import datetime, timedelta

"""
npp_viirs_AOD550_20250805_171657_alaska_polar_fit.tif
noaa21_viirs_AOD550_20250805_164830_alaska_polar_fit.tif
noaa20_viirs_AOD550_20250805_155844_alaska_polar_fit.tif
"""

today = datetime.today().strftime("%Y%m%d")
yesterday = datetime.today() - timedelta(days=1)
yesterday = yesterday.strftime("%Y%m%d")
# Set download directory
DOWNLOAD_DIR = "/home/ags/ArcAQ/AOD_tif"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

BASE_URL = "https://nrt-ops.gina.alaska.edu/"
INDEX_URL = (
    "products.txt?action=index&commit=Get+Products"
    "&controller=products&end_date=&"
    "processing_levels%5B%5D=edr_geotiff_l1&sensors%5B%5D=viirs"
)

def fetch_product_index():
    url = BASE_URL + INDEX_URL
    print("[INFO] Fetching index from:", url)
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text.strip().splitlines()

def download_file(remote_path):
    full_url = remote_path
    filename = os.path.basename(remote_path)
    local_path = os.path.join(DOWNLOAD_DIR, filename)

    if os.path.exists(local_path):
        print("[SKIP] Already exists:", local_path)
        return local_path

    print("[DL] Downloading:", full_url)
    r = requests.get(full_url, stream=True)
    if r.status_code != 200 or "viirs_AOD550" not in filename:
        print("[ERROR] Status {} for {}".format(r.status_code, full_url))
        return None
    
    if yesterday in filename:
        sys.exit()

    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)

    print("[OK] Saved to:", local_path)
    return local_path

def main():
    lines = fetch_product_index()
    tif_paths = [line.strip() for line in lines if line.endswith(".tif") and not line.startswith("listing")]

    print("[INFO] {} TIFFs listed.".format(len(tif_paths)))

    for remote_path in tif_paths:
        local_path = download_file(remote_path)
        if not local_path:
            continue

    print("[DONE] All downloads and conversions complete.")
    print("[INFO] Sorting.")

if __name__ == "__main__":
    main()

