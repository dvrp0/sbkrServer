import json
from const import CARD_SEPARATOR, CARD_TYPES, CARD_PAGE_URL
from typing import Optional

def stringify_card(card: dict):
    stringified = []

    header = (f'{card["name"]}{CARD_SEPARATOR}{card["kingdomShort"]} {card["rarity"]} '
                f'{card["unitTypes"] if card["id"].startswith("u") else CARD_TYPES[card["id"][0]]}')
    stringified.append(header)

    stats = [f'{card["cost"]} 마나']
    if not card["id"].startswith("s"):
        stats.append(f'{CARD_SEPARATOR}{"/".join([str(x) for x in card["strengths"]])} 체력')
    if card["id"].startswith("u"):
        stats.append(f'{CARD_SEPARATOR}{card["movement"]} 이동')

    stringified.append("".join(stats))

    if card["description"]:
        description = card["description"].replace("*", "")

        for key, value in card["ability"].items():
            splitted = [str(x).split("|")[0] for x in value]
            joined = str(splitted[0]) if splitted.count(splitted[0]) == len(splitted) else "/".join(splitted)
            description = description.replace(f"{{{key}}}", joined)

        stringified.append(description)

    return "\n".join(stringified)

with open("cards.json", "r", encoding="utf-8") as f:
    cards = json.load(f)

    for i, card in enumerate(cards):
        descriptions = []

        for j in range(5):
            variables = list(card["ability"].keys())
            description = card["description"]

            for var in variables:
                value = str(card["ability"][var][j])
                description = description.replace(f"{{{var}}}", value.split("|")[1] if "|" in value else value).replace("**", "")

            descriptions.append(description)

        cards[i]["descriptions"] = descriptions
        cards[i]["stringified"] = stringify_card(cards[i])

def get_cards():
    return cards

def search_card(stringify: bool, name: Optional[str] = None, id: Optional[str] = None):
    for card in cards:
        if name:
            flag = name.replace(" ", "") in card["name"].replace(" ", "") or name.replace(" ", "") in [alias.replace(" ", "") for alias in card["aliases"]]
        elif id:
            flag = id == card["id"]

        if flag:
            return f"{card['stringified'].replace('신성한 바리', '✨DVRP🇰🇷')}\n{CARD_PAGE_URL}{card['id']}" if stringify else card