import json
import logging
import requests
import time
import re


# Configure logging
logging.basicConfig(level=logging.INFO,
					format='%(asctime)s - %(levelname)s - %(message)s')


def matches_pattern(value, pattern):
	return bool(re.search(pattern, str(value)))


def send_discord_embed(items: list, total):
	"""Send an embed to Discord containing bought items information."""
	# If webhook_url is None or empty, return early
	if not config.discord_webhook:
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

	response = requests.post(config.discord_webhook, json=payload, headers=headers)

	# Log an error if the request failed
	if response.status_code != 204:
		logging.error("Failed to send message to Discord. Status Code: %s", response.status_code)


def offers_buyitems(buy_offer_ids: list, total) -> list:
	"""Buy items on SkinBaron"""
	# Set up the API URL and payload
	url = "https://api.skinbaron.de/BuyItems"
	payload = json.dumps({
		"apikey": config.apikey,
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


class Offer:
	def __init__(self, api_offer):
		self.id = api_offer["id"]
		self.price = api_offer["price"]
		self.img = api_offer["img"]
		self.market_name = api_offer["market_name"]
		self.sbinspect = api_offer["sbinspect"]
		try:
			self.inspect = api_offer["inspect"]
		except KeyError:
			self.inspect = None
		self.app_id = api_offer["appid"]
	def __str__(self):
		return f"{self.market_name} - {self.price} €"


class Search:
	def __init__(self, searchConfig):
		self.json = searchConfig
		
		def get_and_pop(key, default):
			return self.json.pop(key, default)
		
		self.enabled = get_and_pop("enabled", False)
		self.appid = get_and_pop("appid", 0)
		self.search_item = get_and_pop("search_item", "string")
		self.min_search = get_and_pop("min_search", 0)
		self.max_search = get_and_pop("max_search", 0)
		self.tradelocked = get_and_pop("tradelocked", True)
		self.after_saleid = get_and_pop("after_saleid", "string")
		self.items_per_page = get_and_pop("items_per_page", 0)
		self.max_buy = get_and_pop("max_buy", 0)
		self.max_buy_total = get_and_pop("max_buy_total", 0)
		self.positive_regex = get_and_pop("positive_regex", None)
		self.negative_regex = get_and_pop("negative_regex", None)
		
		if self.json:
			print("Some config parameters couldn't get processed. Exiting...")
			exit()
			
	def offers_search(self) -> list:
		"""Search for offers on SkinBaron"""
		# Set up the API URL and payload
		url = "https://api.skinbaron.de/SearchOffers"
		payload = json.dumps({
			"apikey": config.apikey,
			"appid": self.appid,
			"search_item": self.search_item,
			"min": self.min_search,
			"max": self.max_search,
			"tradelocked": self.tradelocked,
			"after_saleid": self.after_saleid,
			"items_per_page": self.items_per_page
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
   
	def buy_offers(self) -> None:
		"""Buy offers on SkinBaron"""
		if not self.enabled:
			return
		offers = self.offers_search()
		buy_offer_ids = []
		total = 0
		for offer in offers:
			offer = Offer(offer)
			if offer.price <= self.max_buy:
				if self.positive_regex:
					if not matches_pattern(offer.market_name, self.positive_regex):
						logging.info("Offer does not match positive regex: " + str(offer))
						continue
				if self.negative_regex:
					if matches_pattern(offer.market_name, self.negative_regex):
						logging.info("Offer matches negative regex: " + str(offer))
						continue
				logging.info("Buying offer: " + str(offer))
				buy_offer_ids.append(offer.id)
				total += offer.price
			else:
				logging.info("Offer too expensive: " + str(offer))
		if total > 0:
			if total > self.max_buy_total:
				logging.info("Total too expensive: %s €", total)
			else:
				offers_buyitems(buy_offer_ids, total)
		else:
			logging.info("No offers bought")


class Config:
	def __init__(self):

		def load_file() -> dict:
			"""Load the configuration from config.json"""
			with open('config.json', 'r') as configFile:
				return json.load(configFile)

		self.json = load_file()
		self.apikey = self.json["apikey"]
		try:
			self.discord_webhook = self.json["discord_webhook"]
		except KeyError:
			self.discord_webhook = None
			logging.warning("No Discord webhook in the config. Continuing without it.")
		if not self.discord_webhook.startswith("https://discord.com/api/webhooks/"):
			self.discord_webhook = None
			logging.warning("Discord Webhook in config is invalid. Continuing without it.")
		self.interval = self.json["interval"]
		self.searches = []
		for searchConfig in self.json["buying"]:
			self.searches.append(Search(searchConfig))
	
	def print_balance(self) -> float:
		"""Get the balance from SkinBaron"""
		# Set up the API URL and payload
		url = "https://api.skinbaron.de/GetBalance"
		payload = json.dumps({"apikey": self.apikey})
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


if __name__ == "__main__":
	config = Config()
	iteration = 1
	while True:
		logging.info("Iteration: %s", iteration)
		config.print_balance()
		for search in config.searches:
			search.buy_offers()
		time.sleep(config.interval)
		iteration += 1