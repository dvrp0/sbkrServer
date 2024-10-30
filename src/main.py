import json, re, requests
from const import CARD_USAGE_LEAGUES, CARD_USAGE_URL, ON_DEMAND_ISR_URL
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from database import Database
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utilities import repeat_at
from pytz import timezone
from typing import Optional
from utility import get_cards, search_card

db = Database()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    db.close()

app = FastAPI(lifespan=lifespan)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("kitty_card_ids.json", "r") as k:
    ids = json.load(k)
ids_reversed = {value: key for key, value in ids.items()}
usage_caches = {}

@app.get("/cards")
def get_card(name: Optional[str] = None, id: Optional[str] = None, stringify: Optional[bool] = False):
    if not name and not id:
        return {"result": get_cards()}
    else:
        return {"result": search_card(stringify, name, id)}

@app.get("/usages")
def get_card_usages(league: Optional[str] = None, target_date: Optional[str] = None):
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d")) if not target_date else target_date

    if date in usage_caches.keys():
        return {"result": usage_caches[date] if not league else usage_caches[date][league]}
    else:
        usages = db.get_card_usages(date)

        for usage in usages.values():
            for tier, value in usage.items():
                usage[tier] = {
                    "neutral": [x for x in value if ids_reversed[x][0] == "N"],
                    "swarm": [x for x in value if ids_reversed[x][0] == "S"],
                    "winter": [x for x in value if ids_reversed[x][0] == "W"],
                    "shadowfen": [x for x in value if ids_reversed[x][0] == "F"],
                    "ironclad": [x for x in value if ids_reversed[x][0] == "I"]
                }

        usage_caches[date] = usages

    return {"result": usages if not league else usages[league]}

@app.get("/usage-ranks")
def get_card_usage_ranks(league: Optional[str] = None, target_date: Optional[str] = None):
    kingdoms = ["neutral", "swarm", "winter", "shadowfen", "ironclad"]

    result = {x: [] for x in CARD_USAGE_LEAGUES} if not league else {league: []}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d") if not target_date else target_date)
    usages = get_card_usages(league, date)["result"]

    for key in result.keys():
        ranks = {x: [] for x in kingdoms}

        for tier, value in (usages[key].items() if not league else usages.items()):
            for kingdom in kingdoms:
                ranks[kingdom] = [f"{x}|{tier}|{kingdom}" for x in value[kingdom]] + ranks[kingdom]

        for kingdom, cards in ranks.items():
            for card in cards:
                id, tier, kingdom = card.split("|")
                result[key].append({
                    "id": id,
                    "kingdom": kingdom,
                    "tier": tier,
                    "rank": ranks[kingdom].index(card) + 1
                })

    return result if not league else result[league]

@app.get("/usage-changes")
def get_card_usage_changes(league: Optional[str] = None, target_date: Optional[str] = None):
    kingdoms = ["neutral", "swarm", "winter", "shadowfen", "ironclad"]

    result = {x: {} for x in CARD_USAGE_LEAGUES} if not league else {league: {}}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d") if not target_date else target_date)
    now = get_card_usages(league, date)["result"]
    ago = get_card_usages(league, subtract_a_day(date))["result"]

    if now == ago: #아직 업데이트되지 않았을 때
        ago = get_card_usages(league, subtract_a_day(subtract_a_day(date)))["result"]

    for key in result.keys():
        now_list = {x: [] for x in kingdoms}
        ago_list = {x: [] for x in kingdoms}

        for now_value in (now[key].values() if not league else now.values()):
            for kingdom in kingdoms:
                now_list[kingdom][:0] = now_value[kingdom]

        for ago_value in (ago[key].values() if not league else ago.values()):
            for kingdom in kingdoms:
                ago_list[kingdom][:0] = ago_value[kingdom]

        for kingdom, cards in now_list.items():
            for card in cards:
                if card not in ago_list[kingdom]:
                    shift = "new"
                else:
                    temp = ago_list[kingdom].index(card) - now_list[kingdom].index(card)
                    now_tier = get_tier(now[key] if not league else now, card)
                    ago_tier = get_tier(ago[key] if not league else ago, card)

                    if now_tier < ago_tier: #하위 티어로 내려갔을 때
                        temp -= 1
                    elif now_tier > ago_tier: #상위 티어로 올라갔을 때
                        temp += 1
                
                    shift = str(temp)

                result[key][card] = shift

    return {"result": result if not league else result[league]}

@app.get("/ranged-usages")
def get_ranged_card_usages(id: str, league: Optional[str] = None, dates: Optional[int] = 7, is_average: bool = False):
    result = {x: [] for x in CARD_USAGE_LEAGUES} if not league else {league: []}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))

    for _ in range(dates):
        all_ranks = get_card_usage_ranks(league, date)

        for key in result.keys():
            ranks = all_ranks[key] if not league else all_ranks
            target = [x for x in ranks if x["id"] == id]

            result[key].append({
                "date": date[4:],
                "tier": None if len(target) == 0 else target[0]["tier"],
                "rank": None if len(target) == 0 else target[0]["rank"]
            })

        date = subtract_a_day(date)

    if is_average:
        values = list(result.values()) if not league else [result[league]]
        ranks = [[0 if x["rank"] is None else x["rank"] for x in value] for value in values]
        averages = [round(sum(rank) / len(rank), 2) if sum(rank) > 0 else None for rank in ranks]

        if not league:
            for i, average in enumerate(averages):
                result[CARD_USAGE_LEAGUES[i]] = average
        else:
            result[league] = averages[0]

    return result if not league else result[league]

@app.get("/ranged-usage-changes")
def get_ranged_card_usage_changes(id: str, league: Optional[str] = None, dates: Optional[int] = 7):
    result = {x: {} for x in CARD_USAGE_LEAGUES} if not league else {league: {}}
    date = validate_date(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"))

    for _ in range(dates):
        all_changes = get_card_usage_changes(league, date)["result"]

        for key in result.keys():
            changes = all_changes[key] if not league else all_changes
            result[key][date[4:]] = "-" if id not in changes.keys() else changes[id]

        date = subtract_a_day(date)

    return {"result": result if not league else result[league]}

@app.get("/test/get-cached-usages")
def get_cached_usages():
    return {"result": usage_caches}

@repeat_at(cron="0 * * * *")
def save_card_usages():
    print("Saving card usages")

    global usage_caches
    result = {x: {} for x in CARD_USAGE_LEAGUES}

    for league in CARD_USAGE_LEAGUES:
        response = requests.get(f"{CARD_USAGE_URL}{league}")
        regex = re.search('"tiers":.+?(?=,"breadcrumbs")', response.text)
        datas = json.loads(f"{{{regex.group()}}}")

        for tier in datas["tiers"]:
            result[league][tier["name"]] = [ids[x] for x in tier["cards"]]

    usage_caches = {}
    db.save_card_usages(datetime.now(timezone("Asia/Seoul")).strftime("%Y%m%d"), result)
    requests.post(ON_DEMAND_ISR_URL)

def validate_date(date: str):
    db.cursor.execute("SELECT COUNT(1) FROM card_usages WHERE date=%s", (date,))

    return date if db.cursor.fetchone()[0] > 0 else subtract_a_day(date)

def subtract_a_day(date: str):
    return (datetime.strptime(date, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")

def get_tier(source: dict, target: str):
    for tier, kingdom in source.items():
        for cards in kingdom.values():
            if target in cards:
                return tier

    return None