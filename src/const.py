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

DATABASE_URL = os.environ["DATABASE_URL"]

CLOUDFLARE_DEPLOY_URL = os.environ["CLOUDFLARE_DEPLOY_URL"]
ON_DEMAND_ISR_URL = os.environ["ON_DEMAND_ISR_URL"]

KITTY_QUERY_IDS = "https://5hlpazgd.api.sanity.io/v2021-10-21/data/query/production?query=*%5B_type%3D%3D%22card%22%5D%7B%22id%22%3Aid.current%2C%22sid%22%3Asid.current%7D"
KITTY_QUERY_CARDS = "https://5hlpazgd.api.sanity.io/v2021-10-21/data/query/production?query=*%5B_type%3D%3D%22card%22%5D+%7B%0A++...%2C%0A++%22id%22%3A+id.current%2C%0A++%22sid%22%3A+sid.current%2C%0A++%22image%22%3A+image.asset-%3Eurl%0A%7D"