#!/usr/bin/env python3
from argparse import ArgumentParser
import json
import logging
import os
import queue
import requests
import threading

"""This script takes a json schema of house features/properties and searches the website Domain.com
It currently only prints the URLs to screen but I want to do more"""

LOG = logging.getLogger("house_hunter")
logging.basicConfig(level = logging.INFO)

## Endpoints
TOKEN_URL = "https://auth.domain.com.au/v1/connect/token"
RESIDENTIAL_ENDPOINT = "https://api.domain.com.au/v1/listings/residential/_search"
LISTINGS_ENDPOINT = "https://api.domain.com.au/v1/listings/"

## Maximum number of pages to paginate through
MAX_PAGES = 10

class house_hunter_domain:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth = self.get_auth()
        self.id_queue = queue.Queue()

    def get_auth(self):
        "Returns the Auth needed for the requests header"
        response = requests.post(TOKEN_URL, data = {"client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type":"client_credentials",
            "scope":"api_listings_read",
            "Content-Type":"text/json"}) 
        try:
            return {"Authorization":"Bearer " f"""{response.json()["access_token"]}"""}
        except KeyError:
            LOG.info("There was an error when getting your access token")
            LOG.info(f"{response.text}")
        
    def get_listing_ids(self):
        "Puts all the rental ids in a queue for get_listing_info() to consume from"
        for page_number in range(1, MAX_PAGES+1):
            house_properties["page"] = page_number
            response = requests.post(RESIDENTIAL_ENDPOINT, headers = self.auth, json = house_properties)
            for obj in response.json():
                self.id_queue.put(obj["listing"]["id"])

    def get_listing_info(self):
        "Grabs rental ids from the id_queue and gets the rental info"
        while not self.id_queue.empty():
            response = requests.get(f"{LISTINGS_ENDPOINT}{self.id_queue.get()}", headers= self.auth)
            print(response.json()["seoUrl"])

def load_house_properties():
    "Retuns the user provided house properties"
    try:
        prop = json.load(open(args.properties_fpath))
    except IndexError:
        LOG.warning("Make sure to supply a house properties json file as a command line argument")
    return prop


if __name__ == "__main__":
    parser = ArgumentParser(description='Takes rental search parameters and returns urls')
    parser.add_argument('--properties', action='store', help='The search parameters', type=str, dest='properties_fpath', required=True)
    args = parser.parse_args()

##TODO: Make this into a run method ?
    ## Get house properties
    house_properties = load_house_properties()
    test = house_hunter_domain(os.getenv("CLIENTID"), os.getenv("CLIENTSECRET"))
    ## We can get the listing info as soon as we have 1 id so use threading here
    LOG.info("Getting rental ids")
    ids = threading.Thread(target=test.get_listing_ids())
    ids.start()
    info = threading.Thread(target=test.get_listing_info)
    info.start()
    LOG.info("Finished retrieving listings")