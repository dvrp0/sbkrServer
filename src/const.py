import os

CARD_SEPARATOR = " · "
CARD_TYPES = {
    "u": "유닛",
    "s": "주문",
    "b": "건물"
}
CARD_PAGE_URL = "https://sbkr.pages.dev/cards/"

CARD_USAGE_LEAGUES = ["starters", "iron", "bronze", "silver", "gold", "platinum", "diamond", "heroes"]
CARD_USAGE_URL = "https://stormbound-kitty.com/tier-list/"

CLOUDFLARE_DEPLOY_URL = os.environ["CLOUDFLARE_DEPLOY_URL"]

ON_DEMAND_ISR_URL = os.environ["ON_DEMAND_ISR_URL"]

DETA_KEY = os.environ["DETA_KEY"]