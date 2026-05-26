#!/bin/bash -l
echo "INFO:Starting run at $(date)"

SCRIPT=/home/ags/AOD_scripts/AOD_arcpy.py

CONFIG_FILE="/home/ags/ArcAQ/server-files/fire-dev-2/AOD.ini"
SD_DIR=$(awk -F "=" '/^\[Pub\]/ {f=1} f==1 && /^sdDIR/ {print $2; f=0}' "$CONFIG_FILE")
SD_PATH=$(awk -F "=" '/^\[Pub\]/ {f=1} f==1 && /SERVICE_NAME/ {print $2; f=0}' "$CONFIG_FILE" | xargs -I{} echo "$SD_DIR/{}.sd")
 
echo $SD_DIR
echo $SD_PATH

echo "INFO: Downloading and Converting Imagery"
# TODO: ADD IN PARAMS FOR FILEPATHS
conda run -n pyNCL python /home/ags/AOD_scripts/AOD_import.py

echo "INFO: Ingesting Imagery"

host_name=$(basename "$(hostname)" .novalocal)

if conda run -n esri python ${SCRIPT}
then
        echo "INFO: Imagery ingested. Publishing map service."
	if /opt/arcgis/server/tools/admin/createservice -u $ESRI_USER -p $ESRI_PASSWORD -s "https://$host_name:6443/arcgis" -f $SD_PATH --ignoressl;
	then
        	echo "INFO: Service published."
	else
        	echo "INFO: publish of ESRI service failed at $(date)."
fi
else
        echo "ERROR: Imagery not ingested sucsessfully"
fi

echo "INFO: Ending run at $(date)"
