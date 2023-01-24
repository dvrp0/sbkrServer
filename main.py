import json, os, re, requests
from datetime import datetime
from deta import App, Deta
from fastapi import FastAPI
from itertools import chain
from pytz import timezone
from typing import Optional

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
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))
    usage = db.get(date)

    return {"result": usage["usages"]}

@app.get("/usage-changes/")
async def get_card_usage_changes(target_date: Optional[str] = None):
    result = {}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d") if not target_date else target_date)
    now = db.get(date)
    ago = db.get(subtract_a_day(date))

    for league in now["usages"].keys():
        result[league] = {}
        now_list = list(chain.from_iterable(list(now["usages"][league].values())[::-1]))
        ago_list = list(chain.from_iterable(list(ago["usages"][league].values())[::-1]))

        for i, card in enumerate(now_list):
            if card not in ago_list:
                shift = "new"
            else:
                temp = ago_list.index(card) - i
                now_tier = get_tier(now["usages"][league], card)
                ago_tier = get_tier(ago["usages"][league], card)

                if now_tier < ago_tier: #하위 티어로 내려갔을 때
                    temp -= 1
                elif now_tier > ago_tier: #상위 티어로 올라갔을 때
                    temp += 1
                
                shift = str(temp)

            result[league][card] = shift

    return {"result": result}

@app.get("/average-card-usage-changes/")
async def get_average_card_usage_changes(league: str, card: str):
    result = {}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))

    for i in range(7):
        changes = (await get_card_usage_changes(date))["result"][league]

        if card not in changes.keys():
            shift = "-"
        else:
            shift = changes[card]

        result[date[4:]] = shift
        date = subtract_a_day(date)

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

def validate_date(date: str):
    check = db.get(date)

    return date if check else subtract_a_day(date)

def subtract_a_day(date: str):
    return str(int(date) - 1)

def get_tier(source: dict, target: str):
    for key, value in source.items():
        if target in value:
            return key

    return None