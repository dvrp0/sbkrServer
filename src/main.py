import json, re, requests
from action import Action
from const import CARD_USAGE_LEAGUES, CARD_USAGE_URL, DETA_KEY, ON_DEMAND_ISR_URL
from datetime import datetime, timedelta
from deta import Deta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from itertools import chain
from pytz import timezone
from typing import Optional
from utility import get_cards, search_card

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Deta(DETA_KEY).Base("card-usages")

with open("kitty_card_ids.json", "r") as k:
    ids = json.load(k)

ids_reversed = {value: key for key, value in ids.items()}

@app.get("/cards/")
def get_card(name: Optional[str] = None, id: Optional[str] = None, stringify: Optional[bool] = False):
    if not name and not id:
        return {"result": get_cards()}
    else:
        return {"result": search_card(stringify, name, id)}

@app.get("/usages")
def get_card_usage(league: Optional[str] = None):
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))
    usage = db.get(date)["usages"]

    return {"result": usage if not league else usage[league]}

@app.get("/usage-changes")
def get_card_usage_changes(league: Optional[str] = None, target_date: Optional[str] = None):
    result = {}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d") if not target_date else target_date)
    now = db.get(date)
    ago = db.get(subtract_a_day(date))
    two_ago = db.get(subtract_a_day(subtract_a_day(date)))

    for key in now["usages"].keys():
        result[key] = {}
        now_list = list(chain.from_iterable(list(now["usages"][key].values())[::-1]))
        ago_list = list(chain.from_iterable(list(ago["usages"][key].values())[::-1]))

        if now_list == ago_list: #아직 업데이트되지 않았을 때
            ago_list = list(chain.from_iterable(list(two_ago["usages"][key].values())[::-1]))

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

@app.get("/ranged-card-usage-changes")
def get_ranged_card_usage_changes(league: str, card: str, dates: Optional[int] = 7):
    result = {}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))

    for _ in range(dates):
        changes = get_card_usage_changes(target_date=date)["result"][league]

        if card not in changes.keys():
            shift = "-"
        else:
            shift = changes[card]

        result[date[4:]] = shift
        date = subtract_a_day(date)

    return {"result": result}

@app.post("/__space/v0/actions")
def post_actions(action: Action):
    if action.event.id == "save_card_usage":
        save_card_usages()

def save_card_usages():
    result = {}

    for league in CARD_USAGE_LEAGUES:
        result[league] = {}

        response = requests.get(f"{CARD_USAGE_URL}{league}")
        regex = re.search('"tiers":.+?(?=,"breadcrumbs")', response.text)
        datas = json.loads(f"{{{regex.group()}}}")

        for tier in datas["tiers"]:
            result[league][tier["name"]] = [ids[x] for x in tier["cards"]]
                
    db.put(data={"usages": result}, key=datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))
    requests.post(ON_DEMAND_ISR_URL)

def validate_date(date: str):
    check = db.get(date)

    return date if check else subtract_a_day(date)

def subtract_a_day(date: str):
    return (datetime.strptime(date, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")

def get_tier(source: dict, target: str):
    for key, value in source.items():
        if target in value:
            return key

    return None