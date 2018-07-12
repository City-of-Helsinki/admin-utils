#######################################################################
# publish_layers.py: script to publish multiple layers in Geoserver
#
# This script for publish all unpublished layers for given
# workspaces. Useful for database-backed datastores.
#
# Usage: Create a config.json along these lines:
'''
{
  "geoserver": {
    "host": "geoserver.hel.fi",
    "prefix": "/geoserver/rest",
    "auth": "Basic xxxxxxxxxxxxxxxxxxxxxxxxxx==",
  },
  "workspaces": [
    "ltj-virka",
    "ltj-avoin",
    "ltj-dev"
  ],
  "name_title_map": {
    "arvo_kaapakohteet": "Valuable conks",
    "arvo_liito_orava": "Valuable flying squirrels",
  }
}
'''
# You can generate the auth header using any of the multiple generators
# on the web (like: https://www.blitter.se/utils/basic-authentication-header-generator/)
# It is just a base64 encoded concatenation of username and password
#
# workspaces is the list of workspaces to scan for unpublished layers
#
# name_title_map is used to create titles for layers, it can be left
# empty if descriptive titles are not needed

import json
import copy
import requests

# Mostly for documentation, except for the "enabled"
layer_template = {
    "title": "{}",
    "nativeName": "{}",
    "name": "{}",
    "enabled": True,
}

def make_layer(name, title, nativeName=None):
    layer = copy.deepcopy(layer_template)

    # nativeName is the name of the database table/view
    # for database backed stores
    if not nativeName:
        nativeName = name

    layer['nativeName'] = nativeName
    layer['name'] = name
    layer['title'] = title

    return json.dumps({"featureType": layer})

def api_request(path, type="GET", params=None, data=None):
    url = "https://{}{}{}".format(config['geoserver']['host'], config['geoserver']['prefix'], path)

    headers = {
        'Accept': "application/json",
        'Content-Type': "application/json",
        'Authorization': config['geoserver']['auth'],
    }

    if type.lower() == "get":
        try:
            response = requests.request("GET", url, headers=headers, params=params)
            parsed_response = json.loads(response.text)        
            return parsed_response
        except json.decoder.JSONDecodeError as e:
            raise Exception("Response (code {}) was not JSON: {}".format(response.status_code, response.text))
    elif type.lower() == "post":
        response = requests.request("POST", url, headers=headers, data=data)
        
        return(response)
    else:
        raise ValueError("Invalid request type")

def publish_featuretype(workspace, store, definition_json):
    path = "/workspaces/{}/datastores/{}/featuretypes".format(workspace, store)

    response = api_request(path, type="post", data=definition_json)

    return response

def get_stores_for_workspace(workspace):
    path = "/workspaces/{}/datastores".format(workspace)
    
    response = api_request(path)

    return response['dataStores']['dataStore']

def get_unassigned_layers(workspace, store):
    path = "/workspaces/{}/datastores/{}/featuretypes".format(workspace, store)
    
    params = {"list": "available"}
    
    response = api_request(path, params=params)

    if "string" in response['list']:
        return response['list']['string']
    else:
        return []

def load_config():
    return json.load(open("config.json"))


def map_title(layername):
    if layername in config['name_title_map']:
        return config['name_title_map'][layername]
    else:
        return layername

config = load_config()

print("Checking stores for workspaces: {}".format(", ".join(config['workspaces'])))
print("----------------------------------")
for workspace in config['workspaces']:
    try:
        stores = get_stores_for_workspace(workspace)
    except:
        print("No stores found for workspace {}".format(workspace))
        continue
    for store in stores:
        unassigned_layers = get_unassigned_layers(workspace, store['name'])
        print("Store {} in {} has {} unassigned layers".format(store['name'], workspace, len(unassigned_layers)))
        
        if unassigned_layers:
            print("Publishing them all now...")
        
        for layer in unassigned_layers:
            print("{}...".format(layer), end='', flush=True)
            response = publish_featuretype(workspace, store['name'], make_layer(layer,map_title(layer)))
            if (response.status_code == 201):
                print("OK", flush=True)
            else:
                print("FAIL", flush=True)
