import os
from dotenv import load_dotenv
import requests
load_dotenv()
BOOKMAKERS = "Bet365,Superbet"
API_KEY = os.getenv("ODDS_API_KEY")
# checkout https://docs.odds-api.io/ to api docs

#i think this is upcoming events
# events = requests.get(
#     "https://api.odds-api.io/v3/events",
#     params={"apiKey": API_KEY, "sport": "basketball", "league": "usa-nba","limit":"10000"}
# ).json()

historical_events_month_1 = events = requests.get(
    "https://api.odds-api.io/v3/events",
    params={"apiKey": API_KEY, "sport": "basketball", "league": "usa-nba","limit":"10000"}
).json()

# odds = requests.get(
#     "https://api.odds-api.io/v3/odds",
#     params={
#         "apiKey": API_KEY,
#         "eventId": events["id"],
#         "bookmakers": BOOKMAKERS
#     }
# ).json()


print(f"Found {len(events)} nba events")
print(events)
# print(f"Odds: {odds}")