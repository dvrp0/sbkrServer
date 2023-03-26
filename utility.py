import json
from typing import Optional

with open("cards.json", "r", encoding="utf-8") as f:
    data = json.load(f)

STRINGIFY = True
SEPARATOR = " · "
TYPES = {
    "u": "유닛",
    "s": "주문",
    "b": "건물"
}

def search_card(stringify: bool, name: Optional[str] = None, id: Optional[str] = None):
    for card in data:
        if name:
            flag = name in card["name"] or name in card["aliases"]
        elif id:
            flag = id == card["id"]

        if flag:
            if stringify:
                stringified = []

                header = (f'{card["name"]}{SEPARATOR}{card["kingdomShort"]} {card["rarity"]} '
                          f'{card["unitTypes"] if card["id"].startswith("u") else TYPES[card["id"][0]]}')
                stringified.append(header)

                stats = [f'{card["cost"]} 마나']
                if not card["id"].startswith("s"):
                    stats.append(f'{SEPARATOR}{"/".join([str(x) for x in card["strengths"]])} 체력')
                if card["id"].startswith("u"):
                    stats.append(f'{SEPARATOR}{card["movement"]} 이동')

                stringified.append("".join(stats))

                if card["description"]:
                    description = card["description"].replace("*", "")

                    for key, value in card["ability"].items():
                        joined = str(value[0]) if value.count(value[0]) == len(value) else "/".join([str(x).split("|")[0] for x in value])
                        description = description.replace(f"{{{key}}}", joined)

                    stringified.append(description)

                return "\n".join(stringified)
            else:
                descriptions = []

                for i in range(5):
                    variables = list(card["ability"].keys())
                    description = card["description"]

                    for var in variables:
                        value = str(card["ability"][var][i])
                        description = description.replace(f"{{{var}}}", value.split("|")[1] if "|" in value else value)

                    descriptions.append(description)

                result = card
                result["descriptions"] = descriptions

                return result