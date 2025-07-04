import json
import pathlib
from datetime import datetime
from typing import Dict, List, Any, Optional

import yaml
from dateutil import parser as dtparser
from jsonschema import validate as _validate
from jsonschema.exceptions import ValidationError

# Reuse existing helper functions for README generation
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))  # add repo root to path
from generate_mermaid import generate_mermaid_gantt, write_to_readme

RAW_PATH = pathlib.Path("data/events_raw_wikidata.json")
OVERRIDES_PATH = pathlib.Path("data/overrides.yaml")
OUTPUT_PATH = pathlib.Path("data/events.json")
SCHEMA_PATH = pathlib.Path("schemas/event.schema.json")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _date_to_str(value: Optional[str]) -> Optional[str]:
    """Convert an ISO datetime string (possibly with TZ) to YYYY-MM-DD.
    Return None if parsing fails or year/month/day missing.
    """
    if not value:
        return None
    try:
        dt = dtparser.parse(value)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        return None


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


# ----------------------------------------------------------------------------
# Transformation
# ----------------------------------------------------------------------------


def transform(binding: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform one SPARQL binding into our schema.

    Returns None if mandatory fields (title/date) are missing.
    """
    def val(key: str) -> Optional[str]:
        return binding.get(key, {}).get("value")

    title = val("itemLabel")
    if not title:
        return None

    # Prefer start time; else point in time
    start_date_raw = val("start") or val("point")
    start_date = _date_to_str(start_date_raw)
    if not start_date:
        return None

    end_date = _date_to_str(val("end"))
    description = val("itemDescription") or ""

    item_url = val("item")
    sources = [
        {
            "judul": title,
            "url": item_url,
            "tipe": "wikidata",
            "diakses": _today(),
        }
    ] if item_url else []

    event: Dict[str, Any] = {
        "judul": title,
        "tanggal_mulai": start_date,
        "deskripsi": description,
        "lokasi": ["Indonesia"],  # placeholder, can be improved later
        "tokoh": [],
        "sumber": sources,
    }

    if end_date and end_date != start_date:
        event["tanggal_selesai"] = end_date

    return event


# ----------------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------------


def load_overrides() -> Dict[str, Any]:
    if OVERRIDES_PATH.exists():
        with OVERRIDES_PATH.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    return {}


def apply_overrides(events: List[Dict[str, Any]], overrides: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply per-event overrides keyed by title."""
    if not overrides:
        return events
    mapping = {e["judul"]: e for e in events}
    for title, patch in overrides.items():
        if title not in mapping:
            mapping[title] = patch  # new event entirely
        else:
            mapping[title].update(patch)
    return list(mapping.values())


def validate(events: List[Dict[str, Any]]) -> None:
    with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)

    for idx, ev in enumerate(events, 1):
        try:
            _validate(instance=ev, schema=schema)
        except ValidationError as err:
            print(json.dumps(ev, ensure_ascii=False, indent=2))
            raise RuntimeError(
                f"Validation error in event {idx} ({ev.get('judul')}): {err.message}"
            ) from err


def main() -> None:
    if not RAW_PATH.exists():
        raise SystemExit("Raw data not found. Run tools/fetch_wikidata.py first.")

    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    bindings = raw.get("results", {}).get("bindings", [])

    events: List[Dict[str, Any]] = []
    for b in bindings:
        ev = transform(b)
        if ev:
            events.append(ev)

    overrides = load_overrides()
    events = apply_overrides(events, overrides)

    # Sort chronologically by start date
    events.sort(key=lambda x: x["tanggal_mulai"])

    validate(events)

    # Write unified dataset
    OUTPUT_PATH.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(events)} events to {OUTPUT_PATH.relative_to(pathlib.Path.cwd())}")

    # Regenerate README
    mermaid_chart = generate_mermaid_gantt(events)
    write_to_readme(mermaid_chart)
    print("README.md regenerated.")


if __name__ == "__main__":
    main()