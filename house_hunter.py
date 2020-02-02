#!/usr/bin/env python3
from argparse import ArgumentParser
import json
import logging
import os
from pprint import pformat
import queue
import requests
import webbrowser


import folium

"""This script takes a json schema of house features/properties and searches the website Domain.com for properties
and plots the geopoints on a map useing folium.

This requires the user to set their domain api "CLIENTID" and "CLIENTSECRET" keys as bash ENV VARS

An example of the json parameters can be found here 
https://developer.domain.com.au/docs/apis/pkg_agents_listings/references/listings_detailedresidentialsearch"""

LOG = logging.getLogger("house_hunter")
logging.basicConfig(level = logging.INFO)

## Endpoints
TOKEN_URL = "https://auth.domain.com.au/v1/connect/token"
RESIDENTIAL_ENDPOINT = "https://api.domain.com.au/v1/listings/residential/_search"
LISTINGS_ENDPOINT = "https://api.domain.com.au/v1/listings/"

## Maximum number of pages to paginate through
MAX_PAGES = 10

## Map Settings
GRAPH_FILENAME = "index.html"
BBOX_MAX_LAT = -37.8092
BBOX_MAX_LON = 145.0605
MIN_ZOOM = 12

class house_hunter_domain:
    class MissingPropertiesFile(Exception): pass
    class JSONReadError(Exception): pass


    def __init__(self, client_id, client_secret, properties_fpath):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth = self.get_auth()
        LOG.info(f"Successfully retrieved token")
        self.id_queue = queue.Queue()
        ## Load the house properties json file
        try:
            self.house_properties = json.load(open(properties_fpath))
        except FileNotFoundError:
            raise self.MissingPropertiesFile("Make sure to supply a house properties json file as a command line argument --properties fpath")

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
        except KeyError:
            raise self.JSONReadError(f"There was an error when obtaining your access token {pformat(respsonse.text)}")
        
    def consume_listing_ids(self):
        "Puts all the rental ids in a queue for graph() to consume from"
        LOG.info(f"Searching domain for properties with the following features \n  {pformat(self.house_properties)}")
        for page_number in range(1, MAX_PAGES+1):
            self.house_properties["page"] = page_number
            response = requests.post(RESIDENTIAL_ENDPOINT, headers = self.auth, json = self.house_properties)
            try:
                for obj in response.json():
                    self.id_queue.put(obj["listing"]["id"])
            except ValueError:
                raise self.JSONReadError(f"There was an issue retrieving the listing ids \n {pformat(response.headers)}")

    def consume_and_create_graph(self):
        ## Setup the graph
        m = folium.Map([BBOX_MAX_LAT, BBOX_MAX_LON], min_zoom=MIN_ZOOM)
        "Grabs rental ids from the id_queue and gets the rental info"
        ## As we consume from the queue we add the datapoints to the graph
        while not self.id_queue.empty():
            data = requests.get(f"{LISTINGS_ENDPOINT}{self.id_queue.get()}", headers= self.auth).json()
            add_point_to_graph(m, data["geoLocation"]["latitude"], data["geoLocation"]["longitude"], data["seoUrl"])
        return m


def add_point_to_graph(graph, lat, lon, popup):
        "Adds a single point to a given folium graph"
        folium.Marker([lat, lon], popup=popup).add_to(graph)
        graph.save(GRAPH_FILENAME) 

def view_graph(graph_name):
        webbrowser.open("file://" + os.path.realpath(graph_name))
        #LOG.info(f"Cleaning up file {graph_name}")
        #os.remove(graph_name)


def run(client_id, client_secret, properties_fpath):
    test = house_hunter_domain(client_id, client_secret, properties_fpath)
    LOG.info("Attempting to obtain rental ids")
    test.consume_listing_ids()
    ## Get the map object
    graph = test.consume_and_create_graph()
    if graph:
        view_graph(GRAPH_FILENAME)


if __name__ == "__main__":
    parser = ArgumentParser(description="Takes rental search parameters and returns plots map")
    parser.add_argument("--properties", action="store", help="The search parameters", type=str, dest="properties_fpath", required=True)
    args = parser.parse_args()

    run(os.getenv("CLIENTID"), os.getenv("CLIENTSECRET"), args.properties_fpath)
