import requests

import Services.loggingService as loggingService
from Services.remoteService import RemoteSkin
from Services.messageBrocker import MessageBrocker

HARDCODED_COLLECTION_API_URL = "https://hsd-online.net/api/skinsCollections/5"
browser_collection_URL = "https://hsd-online.net/collections/[collection_id]"


class SubscribedCollection:
    def __init__(self, collectionURL: str, active: bool = True):
        self.collectionURL = collectionURL
        self.browser_URL = collectionURL
        self.active = active

        self.id = None
        self.name = None
        self.description = None
        self.creator_name = None
        self.skins: list[RemoteSkin] = []
        self.size_in_b_unrestricted = 0
        self.size_in_b_restricted_only = 0

        try:
            self.loadDataFromURL()
        except requests.ConnectionError as e:
            MessageBrocker.emitConsoleMessage("Cannot load subscription, server is not responding")
            raise e
        except Exception as e:
            raise e

    def loadDataFromURL(self):
        response = requests.get(self.collectionURL)
        if response.status_code == 200:
            raw_json_data = response.json()

            self.id = raw_json_data["id"]
            self.name = raw_json_data["name"]
            self.descrption = raw_json_data["description"]
            self.creator_name = raw_json_data["creator_name"]
            self.size_in_b_unrestricted = raw_json_data["size_in_b_unrestricted"]
            self.size_in_b_restricted_only = raw_json_data["size_in_b_restricted_only"]
            self.browser_URL = browser_collection_URL.replace("[collection_id]", str(self.id))

            for skin_json in raw_json_data.get("skins", []):
                self.skins.append(RemoteSkin(skin_json))
        elif response.status_code == 404:
            loggingService.error(f"Cannot find (404) subscription for URL {self.collectionURL}")
            self.name = "!! Dead link - to be removed !!"
        else:
            raise Exception(f"Cannot get collection data from URL {self.collectionURL}")


subscription_list: list[SubscribedCollection] = []


def getAllSubcriptions() -> list[SubscribedCollection]:
    if len(subscription_list) == 0:
        subscription_list.append(SubscribedCollection(HARDCODED_COLLECTION_API_URL))

    return subscription_list
