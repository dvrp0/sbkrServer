import json, os, re, requests
from datetime import datetime
from deta import App, Deta
from fastapi import FastAPI
from itertools import chain
from pytz import timezone

app = App(FastAPI())
db = Deta(os.environ["PROJECT_KEY"]).Base("card-usages")

CARD_USAGE_LEAGUES = ["starters", "iron", "bronze", "silver", "gold", "platinum", "diamond", "heroes"]
CARD_USAGE_URL = "https://stormbound-kitty.com/tier-list/"

with open("cards.json", "r", encoding="utf-8") as c:
    cards = json.load(c)

with open("kitty_card_ids.json", "r") as k:
    ids = json.load(k)

with open("translations.json", "r", encoding="utf-8") as t:
    translations = json.load(t)

@app.get("/cards/")
async def get_card(name: str):
    result = None

    for key, value in cards.items():
        splitted = key.split()

        if name in splitted or name == "".join(splitted) or name in value["aliases"]:
            result = value["text"]

    return {"result": result}

@app.get("/usages/")
async def get_card_usage():
    date = datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d")
    usage = db.get(date)

    if not usage:
        usage = db.get(subtract_a_day(date))

    return {"result": usage["usages"]}

@app.get("/usage-changes/")
async def get_card_usage_changes():
    result = {}
    date = datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d")
    now = db.get(date)
    ago = db.get(subtract_a_day(date))

    if not now:
        date = subtract_a_day(date)
        now = db.get(date)
        ago = db.get(subtract_a_day(date))

    for league in now["usages"].keys():
        result[league] = {}
        now_flattened = list(chain.from_iterable(list(now["usages"][league].values())[::-1]))
        ago_flattened = list(chain.from_iterable(list(ago["usages"][league].values())[::-1]))

        for i, card in enumerate(now_flattened):
            if card not in ago_flattened:
                shift = "new"
            else:
                shift = str(ago_flattened.index(card) - i)

            result[league][card] = shift

    return {"result": result}

@app.get("/translations/")
async def get_translations():
    return {"result": translations}

@app.lib.cron()
def save_card_usages(event):
    result = {}

    for league in CARD_USAGE_LEAGUES:
        result[league] = {}

        response = requests.get(f"{CARD_USAGE_URL}{league}")
        regex = re.search('"tiers":.+?(?=,"breadcrumbs")', response.text)
        datas = json.loads(f"{{{regex.group()}}}")

        for tier in datas["tiers"]:
            result[league][tier["name"]] = [ids[x] for x in tier["cards"]]
                
    db.put(data={"usages": result}, key=datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))

def subtract_a_day(date: str):
    return str(int(date) - 1)