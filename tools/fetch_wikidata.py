import json
import pathlib
import requests
from datetime import datetime

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
RAW_OUTPUT = pathlib.Path("data/events_raw_wikidata.json")

QUERY = """
SELECT ?item ?itemLabel ?itemDescription ?start ?end ?point ?coord WHERE {
  ?item wdt:P31/wdt:P279* wd:Q1190554 .     # instance of (subclass of) event
  ?item (wdt:P17|wdt:P276) wd:Q252 .        # country (P17) or location (P276) = Indonesia (Q252)
  OPTIONAL { ?item wdt:P580 ?start. }        # start time
  OPTIONAL { ?item wdt:P582 ?end. }          # end time
  OPTIONAL { ?item wdt:P585 ?point. }        # point in time
  OPTIONAL { ?item wdt:P625 ?coord. }        # coordinates
  SERVICE wikibase:label { bd:serviceParam wikibase:language "id,en". }
}
"""


def fetch() -> dict:
    """Run the SPARQL query and return the JSON response."""
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "sejarah-indonesia-bot/0.1 (+https://github.com/your-name/sejarah-indonesia)",
    }
    print("Fetching data from Wikidata…")
    response = requests.get(SPARQL_ENDPOINT, params={"query": QUERY}, headers=headers, timeout=60)
    response.raise_for_status()
    print(f"Fetched {len(response.content)} bytes from Wikidata")
    return response.json()


def save_raw(data: dict, path: pathlib.Path = RAW_OUTPUT) -> None:
    """Save raw data to JSON file with indentation and UTF-8 characters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"Raw data written to {path}")


def main() -> None:
    data = fetch()
    save_raw(data)
    print("Done! Run tools/build_dataset.py to transform the raw dump.")


if __name__ == "__main__":
    main()