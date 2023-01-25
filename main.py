import json, os, re, requests
from datetime import datetime
from deta import App, Deta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from itertools import chain
from pytz import timezone
from typing import Optional

fast = FastAPI()

origins = ["*"]
fast.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app = App(fast)
db = Deta(os.environ["PROJECT_KEY"]).Base("card-usages")

CARD_USAGE_LEAGUES = ["starters", "iron", "bronze", "silver", "gold", "platinum", "diamond", "heroes"]
CARD_USAGE_URL = "https://stormbound-kitty.com/tier-list/"
CLOUDFLARE_DEPLOY_URL = os.environ["CLOUDFLARE_DEPLOY_URL"]

with open("cards.json", "r", encoding="utf-8") as c:
    cards = json.load(c)

with open("kitty_card_ids.json", "r") as k:
    ids = json.load(k)

ids_reversed = {value: key for key, value in ids.items()}

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

@app.get("/usages")
async def get_card_usage(league: Optional[str] = None):
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))
    usage = db.get(date)["usages"]

    return {"result": usage if not league else usage[league]}

@app.get("/usage-changes")
async def get_card_usage_changes(league: Optional[str] = None, target_date: Optional[str] = None):
    result = {}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d") if not target_date else target_date)
    now = db.get(date)
    ago = db.get(subtract_a_day(date))

    for key in now["usages"].keys():
        result[key] = {}
        now_list = list(chain.from_iterable(list(now["usages"][key].values())[::-1]))
        ago_list = list(chain.from_iterable(list(ago["usages"][key].values())[::-1]))

        for card in now_list:
            if card not in ago_list:
                shift = "new"
            else:
                now_factionized = [x for x in now_list if ids_reversed[x][0] == ids_reversed[card][0]]
                ago_factionized = [x for x in ago_list if ids_reversed[x][0] == ids_reversed[card][0]]

                temp = ago_factionized.index(card) - now_factionized.index(card)
                now_tier = get_tier(now["usages"][key], card)
                ago_tier = get_tier(ago["usages"][key], card)

                if now_tier < ago_tier: #하위 티어로 내려갔을 때
                    temp -= 1
                elif now_tier > ago_tier: #상위 티어로 올라갔을 때
                    temp += 1
                
                shift = str(temp)

            result[key][card] = shift

    return {"result": result if not league else result[league]}

@app.get("/average-card-usage-changes")
async def get_average_card_usage_changes(league: str, card: str):
    result = {}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))

    for i in range(7):
        changes = (await get_card_usage_changes(target_date=date))["result"][league]

        if card not in changes.keys():
            shift = "-"
        else:
            shift = changes[card]

        result[date[4:]] = shift
        date = subtract_a_day(date)

    return {"result": result}

@app.get("/translations")
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
    requests.post(CLOUDFLARE_DEPLOY_URL)

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