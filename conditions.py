#####################################################################
# Conditions ('OpenMountainWatch')
# Reads the conditions (closures) from outdooractive and for each one:
#   - records it and if not duplicate, informs the destination
#
# Process:
# 1. the closure should be in a specific region (e.g. Sibiu)
# <region id="33306111" type="district" />
# 2. find all closures
# https://www.outdooractive.com/api/project/api-romaniatravel-guide/conditions?key=IR9FPKQ7-EMWGM7FJ-4OSSXRYX
# 3. get information about each of the found closures
# https://www.outdooractive.com/api/project/api-romaniatravel-guide/oois/252620006?key=IR9FPKQ7-EMWGM7FJ-4OSSXRYX&lang=ro
#
#####################################################################
# Version: 0.3.0
# Email: paul.wasicsek@gmail.com
# Status: dev
#####################################################################

import sqlite3
import configparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# import urllib
import datetime
import pandas as pd
import logging as log
import os
from random import randint
import time
from jira import JIRA
import xmltodict

# global variables
today = datetime.date.today().strftime("%Y-%m-%d")
now = datetime.date.today().strftime("%Y-%m-%d %H:%M")
c_xml = {}
geometry_description = ""

# Read initialization parameters
config = configparser.ConfigParser()
try:
    config.read("config.ini")
except Exception as err:
    print("Cannot read INI file due to Error: %s" % (str(err)))

OA_PROJECT = config["Outdooractive"]["Project"]
OA_KEY = config["Outdooractive"]["API"]

s = smtplib.SMTP_SSL(host=config["Email"]["Host"], port=config["Email"]["Port"])
# s.starttls()
s.ehlo()
s.login(config["Email"]["Email"], config["Email"]["Password"])

# Customize path to your SQLite database
database = config["Database"]["DB_Name"]

log.basicConfig(
    filename=config["Log"]["File"],
    level=os.environ.get("LOGLEVEL", config["Log"]["Level"]),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S ",
)

#
# Connect to the database
#
try:
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
except Exception as err:
    print("Connecting to DB failed due to: %s\n" % (str(err)))

# Improve https connection handling, see article:
# https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests
#
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

#
# Wait according to seetings in config.ini (try not to send too many requests in a too short time)
#
def wait():
    if config["Action"]["Execute"] == "Delay":
        # Include a waiting period, so the algorithm doesn't think it's automatic processing
        t = randint(int(config["Wait"]["Min"]), int(config["Wait"]["Max"]))
        time.sleep(t)


#
# Execute query and populates ? with param.
#
def execute(query, param=""):
    log.debug("SQL:" + query)
    if len(param) > 0:
        log.debug("Param:" + str(param))
    try:
        cursor.execute(query, param)
        if query.startswith("UPDATE") or query.startswith("INSERT"):
            cursor.execute("COMMIT")
    except Exception as err:
        print("Query Failed: %s\nError: %s" % (query, str(err)))


#
# Checks if a record already exists in the tabel
#
def exists(query):
    log.debug("Exists SQL:" + query)
    result = (0,)
    try:
        cursor.execute(query)
        result = cursor.fetchone()
    except Exception as err:
        print("Query Failed: %s\nError: %s" % (query, str(err)))
    print("Result:", result)
    return result[0]


#
#
#
def get_region(region):
    wait()
    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/oois/"
        + str(region["@id"])
        + "?key="
        + OA_KEY
        + "&lang=ro"
    )
    log.debug("Get region URL:" + url)
    region_xml = xmltodict.parse(session.get(url).text)
    region_type = region_xml["oois"]["region"]["category"]["@name"]
    region_name = region_xml["oois"]["region"]["title"]
    return region_type + "->" + region_name + " / "


#
# read the condition from Outdooractive
#
def read_condition(condition):
    global c_xml
    global geometry_description

    wait()
    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/oois/"
        + str(condition)
        + "?key="
        + OA_KEY
        + "&lang=ro"
    )
    log.debug("Condition URL:" + url)
    c_xml = xmltodict.parse(session.get(url).text)

    try:
        x_var = c_xml["oois"]["condition"]["longText"]
    except:
        c_xml["oois"]["condition"]["longText"] = ""

    try:
        x_var = c_xml["oois"]["condition"]["weatherDescription"]
    except:
        c_xml["oois"]["condition"]["weatherDescription"] = ""

    try:
        x_var = c_xml["oois"]["condition"]["localizedTitle"]["@lang"]
    except:
        c_xml["oois"]["condition"]["localizedTitle"] = {}
        c_xml["oois"]["condition"]["localizedTitle"]["@lang"] = ""

    try:
        x_var = c_xml["oois"]["condition"]["riskDescription"]
    except:
        c_xml["oois"]["condition"]["riskDescription"] = ""

    winter_activity = c_xml["oois"]["condition"]["winterActivity"]

    geometry_description = ""
    for record in c_xml["oois"]["condition"]["regions"]["region"]:
        # print(str(record["@id"]))
        geometry_description = geometry_description + get_region(record)

    date_processed = today


#
# Save the condition in the database
#   - if the condition is already stored (identified by id) then
def save_condition():
    global c_xml
    global geometry_description

    log.debug("c_xml dictionary #########\n\r" + str(c_xml))
    processed = "n"
    date_processed = today
    condition_saved = False
    query = (
        "SELECT EXISTS(SELECT 1 FROM conditions WHERE id='"
        + str(c_xml["oois"]["condition"]["@id"])
        + "')"
    )
    if exists(query) == 0:
        query = """INSERT INTO conditions (id, status, category_id, day_of_inspection,date_from,frontendtype,ranking,title,lang, long_text,winter_activity,geometry, lat, long, risk_description, weather_description,user_id, processed, date_processed, geometry_description)
        VALUES( ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);"""
        param = (
            c_xml["oois"]["condition"]["@id"],
            c_xml["oois"]["condition"]["meta"]["workflow"]["@state"],
            c_xml["oois"]["condition"]["category"]["@id"],
            c_xml["oois"]["condition"]["@dayOfInspection"],
            c_xml["oois"]["condition"]["@dateFrom"],
            c_xml["oois"]["condition"]["@frontendtype"],
            c_xml["oois"]["condition"]["@ranking"],
            c_xml["oois"]["condition"]["title"],
            c_xml["oois"]["condition"]["localizedTitle"]["@lang"],
            c_xml["oois"]["condition"]["longText"],
            c_xml["oois"]["condition"]["winterActivity"],
            c_xml["oois"]["condition"]["geometry"],
            0,
            0,
            c_xml["oois"]["condition"]["riskDescription"],
            c_xml["oois"]["condition"]["weatherDescription"],
            c_xml["oois"]["condition"]["meta"]["authorFull"]["id"],
            processed,
            date_processed,
            geometry_description,
        )
        execute(query, param)
        condition_saved = True
    return condition_saved


#
#   check if it's a new condition and inform by email and/or creating a Jira ticket
#
def execute_condition():
    print()


def main():
    log.info("=======================")
    log.info("Program start: " + str(now))
    log.info("=======================")
    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/conditions?key="
        + OA_KEY
    )
    log.debug("Base URL:" + url)

    # Read all the conditions you have access to through API
    xml = xmltodict.parse(session.get(url).text)
    for condition in xml["datalist"]["data"]:
        condition_id = condition["@id"]

        # collect all information related to the found condition
        read_condition(condition_id)

        # save the information in the database
        if save_condition():
            # execute defined actions
            execute_condition()


if __name__ == "__main__":
    main()
