#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 5 2025

@author: qdmchenry
"""
import arcpy
import glob
import re
import os
import sys
import datetime
import configparser
import argparse
import pytz

AK_time = pytz.timezone('America/Anchorage')
starttime = AK_time.localize(datetime.datetime.now())
print("Python Start Time: " + str(starttime))

def setupAPRX(templatePath, newProjectPath):
    # Accesses template APRX, copies to new path
    temp_aprx = arcpy.mp.ArcGISProject(templatePath)
    temp_aprx.saveACopy(newProjectPath)
    del temp_aprx
    return arcpy.mp.ArcGISProject(newProjectPath)

def SubsetNewTifs(folder):
    last12 = datetime.datetime.now() - datetime.timedelta(hours=12)
    newTifs = []
    for filePath in glob.glob(folder + "/*"):
        if os.path.isfile(filePath):
            timeModded = datetime.datetime.fromtimestamp(os.path.getmtime(filePath))
            newTifs.append(filePath)
    print("Processing the following tifs:")
    print(newTifs)
    return newTifs

starttime = datetime.datetime.now()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description="ArcGIS Server publishing scripts for Air Quality Models"
    )

    parser.add_argument(
        "--source_dir",
        "-i",
        type=str,
        default="/home/ags/ArcAQ/AOD_tifs",
        help="Source directory containing new .tif files"
    )
    parser.add_argument(
        "--config_file",
        "-c",
        type=str,
        default="/home/ags/ArcAQ/server-files/fire-dev-2/AOD.ini",
        help="Path to configuration INI file that contains the file paths"
    )
    args = parser.parse_args()
    sourceDir = args.source_dir
    configFile = args.config_file
    config = configparser.ConfigParser()
    config.read(configFile)

    cleanAPRX = config.get('Arc', 'cleanAPRX')
    newAPRX = config.get('Arc', 'newAPRX')
    lyrxGM = config.get('Arc', 'lyrxGM')
    symPath = config.get('Arc', 'symLYRX')
    tifDIR = config.get('Arc', 'tifDIR')

    sdDraftDir = config.get('Pub', 'sdDraftDIR')
    sdDir = config.get('Pub', 'sdDIR')
    MODEL = config.get('Pub', 'MODEL')
    SERVICE_NAME = config.get('Pub', 'SERVICE_NAME')

    arcpy.env.workspace = lyrxGM
    arcpy.env.overwriteOutput = True

    ##### Copy blank aprx, import template map file #####

    aprx = setupAPRX(cleanAPRX, newAPRX)
    mPub = aprx.listMaps()[0]

    ##### Use glob to grab all new tifs #####
    
    allFiles = glob.glob(tifDIR + "/*")

    newTifs = SubsetNewTifs(sourceDir)
    metadata = []
    models = ['N20', 'N21', 'NPP'] # [

#1. noaa21_viirs_AOD550_20250805_164830_alaska_polar_fit.tif
#2. noaa21_viirs_AOD550_20250805_164830_alaska_polar_fit
#4. noaa21 viirs AOD550 20250805 164830  alaska polar   fit
#   0       1       2       3       4       5   6       7

    def parse_file_info(filePath):
        """Parses the filename to extract model and time information."""
        fileName = os.path.basename(filePath)
        fileSplit = fileName.split("_")
        if "noaa20" in fileName:
            model = models[0] 
        elif "noaa21" in fileName:
            model = models[1]
        else:
            model = models[2]

        print(f"parsing filename: {fileName}")
        modelDate = fileSplit[3]
        modelTime = fileSplit[4]
        
        return fileName, model, modelDate, modelTime

    def convert_to_datetime(modelDate, modelTime):
    # Remove underscore if present
        timeStr = modelDate + modelTime[0:4]
        return AK_time.localize(datetime.datetime.strptime(timeStr, '%Y%m%d%H%M'))

    def create_lyrx(filePath, fileName):
        """Creates a .lyrx version of the .tif file if it doesn't already exist."""
        lyrPath = os.path.join(lyrxGM, fileName + ".lyrx")
        if not os.path.exists(lyrPath):
            print(f"Creating layer: {fileName}")
            arcpy.management.MakeRasterLayer(filePath, fileName)
            arcpy.management.SaveToLayerFile(fileName, lyrPath)
            print(arcpy.GetMessages())
        else:
            print(lyrPath, "already exists, skipping")
        return(lyrPath)
    
    def add_layer_to_map(mPub, lyrPath, fileName, label, symPath):
        """Adds the .lyrx layer to the map and renames it."""
        print(f"Adding to map: {lyrPath}")
        mPub.addDataFromPath(lyrPath)
        lyr = mPub.listLayers(fileName)[0]
        lyr.name = lyr.name.replace(fileName, label)
        arcpy.management.ApplySymbologyFromLayer(lyr, symPath)
        return lyr.name

    for filePath in newTifs:
        # Set up empty dictionary
        tmpdict = {}
        fileName, model, modelDate, modelTime = parse_file_info(filePath)
        # Parse information of out .tif file name
        modelDateTime = convert_to_datetime(modelDate, modelTime)
        tmpdict["modelDateTime"] = modelDateTime
        tmpdict["model"] = model
        tmpdict["fileName"] = filePath
        
        # Create Layer Name
        label = f"AOD {str(modelDateTime.strftime('%H:%M %m/%d/%Y %Z'))}"
        tmpdict["label"] = label
        lyrName = fileName + ".lyrx"
        lyrPath = create_lyrx(filePath, fileName)
        tmpdict["lyrPath"] = lyrPath
        tmpdict["lyrName"] = lyrName
        metadata.append(tmpdict)

    ##### Create group layer ####

    for m in models:
        mPub.createGroupLayer(m)

    ##### For loop to add layers to group layers in the proper order #####

    def add_lyr_to_group(mPub, groupLyr, lyrPath, label, symPath):
        lyrFile = arcpy.mp.LayerFile(lyrPath)
        lyr_name = os.path.splitext(os.path.basename(lyrPath))[0]
        mPub.addLayerToGroup(groupLyr, lyrFile, 'BOTTOM')#[0]
        lyr = groupLyr.listLayers()[-1]
        lyr.name = lyr.name.replace(lyr.name, label)
        arcpy.management.ApplySymbologyFromLayer(lyr, symPath)
        return lyr

    sortedData = sorted(metadata, key=lambda d: d['modelDateTime'])
    first_lyr_0 = True
    first_lyr_1 = True
    first_lyr_2 = True
    for n, i in enumerate(sortedData):
        if i["model"] == models[0]:
            print(i["lyrPath"], "added to", models[0])
            symPath = symPath
            lyr = add_lyr_to_group(mPub, mPub.listLayers(models[0])[0], i["lyrPath"], i["label"], symPath)
            lyr.visible = first_lyr_0
            first_lyr_0 = False
        elif i["model"] == models[1]:
            print(i["lyrPath"], "added to", models[1])
            symPath = symPath
            lyr = add_lyr_to_group(mPub, mPub.listLayers(models[1])[0], i["lyrPath"], i["label"], symPath)
            lyr.visible = first_lyr_1
            first_lyr_1 = False
            
        else:
            print(i["lyrPath"], "added to", models[2])
            symPath = symPath
            lyr = add_lyr_to_group(mPub, mPub.listLayers(models[2])[0], i["lyrPath"], i["label"], symPath)
            lyr.visible = first_lyr_2
            first_lyr_2 = False

    aprx.save()
    del aprx

    serviceName = SERVICE_NAME

    ## Below code works to publish the service as type = overwrite 
    # Generate SDDraft file from the map
    serviceCredit = "AOD Model produced by GINA at the University of Alaska Fairbanks" 
    serviceSummary = ""
    serviceTags = "AOD"
    serviceDescription = ""
    serviceUseLimitations = ""
    print("Preparing " + serviceName + " service for publishing")
    sddraftFile = serviceName + ".sddraft"
    sddraftPath = os.path.join(sdDraftDir, sddraftFile)
    if os.path.exists(sddraftPath):
        os.remove(sddraftPath)

    print("Generating " + sddraftPath)
    sddraft = arcpy.sharing.CreateSharingDraft('STANDALONE_SERVER', 'MAP_SERVICE', serviceName, mPub)
    sddraft.offline = True
    sddraft.copyDataToServer = False
    sddraft.summary = serviceSummary
    sddraft.description = serviceDescription
    sddraft.tags = serviceTags 
    sddraft.useLimitations = serviceUseLimitations
    sddraft.offlineTarget = "ENTERPRISE_11"
    sddraft.overwriteExistingService = True
    sddraft.credits = serviceCredit
    sddraft.exportToSDDraft(sddraftPath)
    print (arcpy.GetMessages())

    ## Generate SD file
    if sddraftPath:
        sdFile = serviceName + ".sd"
        sdPath = os.path.join(sdDir, sdFile)
        if os.path.exists(sdPath):
            os.remove(sdPath)
    try:
        print("Staging " + sddraftPath + " to generate service definition at " + sdPath)
        arcpy.StageService_server(sddraftPath, sdPath)
    except:
        print (arcpy.GetMessages())
        sys.exit("Failed to stage service")
