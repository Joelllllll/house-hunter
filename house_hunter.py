#!/usr/bin/env python3
from argparse import ArgumentParser
import json
import logging
import os
import queue
import requests
import threading


import folium
import webbrowser

"""This script takes a json schema of house features/properties and searches the website Domain.com for properties
and plots the geopoints on a map useing folium"""

LOG = logging.getLogger("house_hunter")
logging.basicConfig(level = logging.INFO)

## Endpoints
TOKEN_URL = "https://auth.domain.com.au/v1/connect/token"
RESIDENTIAL_ENDPOINT = "https://api.domain.com.au/v1/listings/residential/_search"
LISTINGS_ENDPOINT = "https://api.domain.com.au/v1/listings/"

## Maximum number of pages to paginate through
MAX_PAGES = 10
MAP_FILE = "index.html"

class house_hunter_domain:
    def __init__(self, client_id, client_secret, properties_fpath):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth = self.get_auth()
        LOG.info(f"Successfully retrieved token")
        self.id_queue = queue.Queue()
        ## Load the house properties json file
        try:
            self.house_properties = json.load(open(properties_fpath))
        except IndexError as e:
            LOG.info("Make sure to supply a house properties json file as a command line argument")
            raise e

    def get_auth(self):
        "Returns the Auth needed for the requests header"
        LOG.info("Attempting to obtain access token")
        response = requests.post(TOKEN_URL, data = {"client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type":"client_credentials",
            "scope":"api_listings_read",
            "Content-Type":"text/json"}) 
        try:
            return {"Authorization":"Bearer " f"""{response.json()["access_token"]}"""}
        except KeyError as e:
            LOG.info(f"There was an error when obtaining your access token {respsonse.text}")
            raise e
        
    def get_listing_ids(self):
        "Puts all the rental ids in a queue for get_listing_info() to consume from"
        for page_number in range(1, MAX_PAGES+1):
            self.house_properties["page"] = page_number
            response = requests.post(RESIDENTIAL_ENDPOINT, headers = self.auth, json = self.house_properties)
            try:
                for obj in response.json():
                    self.id_queue.put(obj["listing"]["id"])
            except ValueError as e:
                LOG.error(f"There was an issue retrieving the listing ids \n {response.headers}")
                raise e

    def get_listing_info(self):
        lats, lons, urls, prices = [], [], [], []
        "Grabs rental ids from the id_queue and gets the rental info"
        while not self.id_queue.empty():
            data = requests.get(f"{LISTINGS_ENDPOINT}{self.id_queue.get()}", headers= self.auth).json()
            lat.append(data["geoLocation"]["latitude"])
            lon.append(data["geoLocation"]["longitude"])
            price.append(data["priceDetails"]["displayPrice"])
            url.append(data["seoUrl"])
        
        LOG.info("Finished retrieving listings")
        return lats, lons, urls, prices

def plot_rentals(lats, lons, urls):
    "Plots the lat/lons on a map along with displaying domain urls"
    m = folium.Map([max(lats), max(lons)])
    LOG.info(f"Adding {len(urls)} set(s) of geo points to map")
    for url, lat, lon in zip(urls, lats, lons):
        folium.Marker([lat, lon],
         popup=url).add_to(m)
    m.save(MAP_FILE)
    webbrowser.open("file://" + os.path.realpath(MAP_FILE))
    LOG.info(f"Cleaning up file {MAP_NAME}")
    os.remove(MAP_FILE)


def run(client_id, client_secret, properties_fpath):
    test = house_hunter_domain(client_id, client_secret, properties_fpath)
    LOG.info("Attempting to obtain rental ids")
    test.get_listing_ids()
    ## Grab all properties we want to plot
    lats, lons, urls, prices = test.get_listing_info()
    plot_rentals(lats, lons, urls)

if __name__ == "__main__":
    parser = ArgumentParser(description="Takes rental search parameters and returns plots map")
    parser.add_argument("--properties", action="store", help="The search parameters", type=str, dest="properties_fpath", required=True)
    args = parser.parse_args()

    run(os.getenv("CLIENTID"), os.getenv("CLIENTSECRET"), args.properties_fpath)