import json
import logging
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO,
					format='%(asctime)s - %(levelname)s - %(message)s')


def load_config() -> dict:
	"""Load the configuration from config.json"""
	with open('config.json', 'r') as configFile:
		return json.load(configFile)


def send_discord_embed(items: list, total):
	"""Send an embed to Discord containing bought items information."""
	webhook_url = config.get("discord_webhook")

	# If webhook_url is None or empty, return early
	if not webhook_url:
		logging.warning("Discord webhook URL not found in config. Skipping sending message to Discord.")
		return

	# Construct the embed
	embeds = [{
		"title": "Items Bought",
		"description": "\n".join([f"Item: {item['name']} - Price: {item['price']:.2f} €" for item in items]),
		"color": 10233776, # Corresponding to RGB(156,39,176) or #9C27B0
		"footer": {
			"text": f"Total: {total:.2f} €"
		}
	}]
	
	payload = {
		"content": "New items have been bought!",
		"embeds": embeds,
		"username": "SkinbaronBot_v2 by Louis_45"
	}

	headers = {
		'Content-Type': 'application/json',
	}

	response = requests.post(webhook_url, json=payload, headers=headers)

	# Log an error if the request failed
	if response.status_code != 204:
		logging.error("Failed to send message to Discord. Status Code: %s", response.status_code)


def account_get_balance() -> float:
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
	balance = float(response_json["balance"])
	logging.info("Balance: %s €", balance)
	return balance


def offers_search(appid: int = 0,
				  search_item: str = "string",
				  min_search = 0,
				  max_search = 0,
				  tradelocked: bool = True,
				  after_saleid: str = "string",
				  items_per_page: int = 0) -> list:
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
	logging.info("Returned %s offers", len(offers))
	return offers


def offers_buyitems(buy_offer_ids: list, total) -> list:
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
	# Check for generalErrors in the response and log them
	if "generalErrors" in response_json:
		for error in response_json["generalErrors"]:
			logging.info("Received Error when trying to buy items: %s", error)
		return []
	items = response_json["items"]
	logging.info("Bought %s items", len(items))

	# Send a message to the Discord webhook
	send_discord_embed(items, total)
	return items


def buy_offers_search(enabled: bool = True,
					  appid: int = 0,
					  search_item: str = "string",
					  min_search = 0,
					  max_search = 0,
					  tradelocked: bool = True,
					  after_saleid: str = "string",
					  items_per_page: int = 0,
					  max_buy = 0,
					  max_buy_total = 0) -> None:
	"""Buy offers on SkinBaron"""
	if not enabled:
		return
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
			logging.info("Buying offer: %s - %s €", offer["market_name"],
						 offer["price"])
			buy_offer_ids.append(offer["id"])
			total += offer["price"]
		else:
			logging.info("Offer too expensive: %s - %s €",
						 offer["market_name"], offer["price"])
	if total > 0:
		if total > max_buy_total:
			logging.info("Total too expensive: %s €", total)
		else:
			offers_buyitems(buy_offer_ids, total)
	else:
		logging.info("No offers bought")

if __name__ == "__main__":
	config = load_config()
	apikey = config["apikey"]
	iteration = 1

	while True:
		logging.info("Iteration: %s", iteration)
		account_get_balance()
		for buying in config["buying"]:
			buy_offers_search(**buying)
		time.sleep(config["interval"])
		iteration += 1
