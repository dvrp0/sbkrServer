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
        now_sub = now["usages"][league]
        ago_sub = ago["usages"][league]

        for sub in list(now_sub.values())[::-1]:
            for card in sub:
                now_index = get_index(now_sub, card)
                ago_index = get_index(ago_sub, card)

                if now_index is None:
                    shift = "new"
                elif now_index[0] == ago_index[0]:
                    shift = str(ago_index[1] - now_index[1])
                elif now_index[0] < ago_index[0]: #하위 티어로 내려갔을 때
                    shift = str(-(len(ago_sub[ago_index[0]]) - ago_index[1] + now_index[1]))
                elif now_index[0] > ago_index[0]: #상위 티어로 올라갔을 때
                    shift = str(len(ago_sub[ago_index[0]]) - ago_index[1] + now_index[1])

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

def get_index(target_list: dict, target: str):
    for key, value in target_list.items():
        if target in value:
            return (key, value.index(target))

    return None