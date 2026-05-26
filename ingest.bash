#!/bin/bash

wget -q -O - \
  "https://nrt-prod.gina.alaska.edu/products?utf8=%E2%9C%93&satellites%5B%5D=snpp&satellites%5B%5D=noaa21&satellites%5B%5D=noaa20&processing_levels%5B%5D=edr_geotiff_l1&start_date=&end_date=&commit=Get+Products/" \
  | grep -oP 'href="[^"]*noaa20_viirs_AOD550[^"]*\.tif"' \
  | sed 's/href="//;s/"//' \
  | while read url; do
      wget -P ./tif "https://nrt-prod.gina.alaska.edu$url"
    done