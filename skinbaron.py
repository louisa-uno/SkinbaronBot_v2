import json
import logging
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def load_config():
	"""Load the configuration from config.json"""
	with open('config.json', 'r') as configFile:
		return json.load(configFile)


def account_get_balance():
	"""Get the balance from SkinBaron"""
	# Set up the API URL and payload
	url = "https://api.skinbaron.de/GetBalance"
	payload = json.dumps({"apikey": apikey})
	headers = {
	    'Content-Type': 'application/json',
	    'x-requested-with': 'XMLHttpRequest'
	}

	# Send the request to the API
	response = requests.request("POST", url, headers=headers, data=payload)
	response_json = response.json()
	balance = response_json["balance"]
	logging.info("Balance: {} €".format(balance))
	return balance


def offers_search(appid=0,
                  search_item="string",
                  min_search=0,
                  max_search=0,
                  tradelocked=True,
                  after_saleid="string",
                  items_per_page=0):
	"""Search for offers on SkinBaron"""
	# Set up the API URL and payload
	url = "https://api.skinbaron.de/SearchOffers"
	payload = json.dumps({
	    "apikey": apikey,
	    "appid": appid,
	    "search_item": search_item,
	    "min": min_search,
	    "max": max_search,
	    "tradelocked": tradelocked,
	    "after_saleid": after_saleid,
	    "items_per_page": items_per_page
	})
	headers = {
	    'Content-Type': 'application/json',
	    'x-requested-with': 'XMLHttpRequest'
	}

	# Send the request to the API
	response = requests.request("POST", url, headers=headers, data=payload)
	response_json = response.json()
	offers = response_json["sales"]
	logging.info("Returned {} offers".format(len(offers)))
	return offers


def offers_buyitems(buy_offer_ids, total):
	"""Buy items on SkinBaron"""
	# Set up the API URL and payload
	url = "https://api.skinbaron.de/BuyItems"
	payload = json.dumps({
	    "apikey": apikey,
	    "total": total,
	    "toInventory": True,
	    "saleids": buy_offer_ids
	})
	headers = {
	    'Content-Type': 'application/json',
	    'x-requested-with': 'XMLHttpRequest'
	}

	# Send the request to the API
	response = requests.request("POST", url, headers=headers, data=payload)
	response_json = response.json()
	logging.info("Bought {} items".format(len(response_json["items"])))
	return response_json["items"]


def buy_offers_search(enabled=True,
                      appid=0,
                      search_item="string",
                      min_search=0,
                      max_search=0,
                      tradelocked=True,
                      after_saleid="string",
                      items_per_page=0,
                      max_buy=0,
                      max_buy_total=0):
	if not enabled: return
	offers = offers_search(appid=appid,
	                       search_item=search_item,
	                       min_search=min_search,
	                       max_search=max_search,
	                       tradelocked=tradelocked,
	                       after_saleid=after_saleid,
	                       items_per_page=items_per_page)
	buy_offer_ids = []
	total = 0
	for offer in offers:
		if offer["price"] <= max_buy:
			logging.info("Buying offer: {} - {}€".format(
			    offer["market_name"], offer["price"]))
			buy_offer_ids.append(offer["id"])
			total += offer["price"]
		else:
			logging.info("Offer too expensive: {} - {}€".format(
			    offer["market_name"], offer["price"]))
	if total > 0:
		if total > max_buy_total:
			logging.info("Total too expensive: {}€".format(total))
		else:
			offers_buyitems(buy_offer_ids, total)
	else:
		logging.info("No offers bought")


config = load_config()
apikey = config["apikey"]
iteration = 1

while True:
	logging.info("Iteration: {}".format(iteration))
	account_get_balance()
	for buying in config["buying"]:
		buy_offers_search(**buying)
	time.sleep(config["interval"])
	iteration += 1
