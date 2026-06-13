import json
import os
from collections import Counter
from datetime import datetime, timezone

from stock_data import VALID_SECTORS, normalize_sector


METADATA_FILE = "data/stock_metadata.json"
OUTPUT_FILE = "data/metadata_health.json"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_industries():
    metadata = load_json(METADATA_FILE)
    missing_sector = []
    invalid_sector = []
    normalized_changes = []
    schema_warnings = []
    sector_counts = Counter()

    for symbol, record in sorted(metadata.items()):
        raw_sector = record.get("sector")
        normalized = normalize_sector(raw_sector)

        if not raw_sector:
            missing_sector.append(symbol)
        elif normalized not in VALID_SECTORS:
            invalid_sector.append({
                "symbol": symbol,
                "sector": raw_sector,
                "normalized": normalized,
            })
        else:
            sector_counts[normalized] += 1

        if raw_sector and raw_sector != normalized:
            normalized_changes.append({
                "symbol": symbol,
                "from": raw_sector,
                "to": normalized,
            })

        if "name" not in record and "company_name" in record:
            schema_warnings.append({
                "symbol": symbol,
                "issue": "uses company_name instead of name",
            })
        if "listingDate" not in record and "listing_date" in record:
            schema_warnings.append({
                "symbol": symbol,
                "issue": "uses listing_date instead of listingDate",
            })

    status = "ok"
    if missing_sector or invalid_sector:
        status = "error"
    elif schema_warnings:
        status = "warning"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": METADATA_FILE,
        "status": status,
        "symbol_count": len(metadata),
        "sector_counts": dict(sorted(sector_counts.items())),
        "missing_sector": missing_sector,
        "invalid_sector": invalid_sector,
        "normalized_changes": normalized_changes,
        "schema_warnings": schema_warnings,
        "valid_sectors": sorted(VALID_SECTORS),
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(f"Industry metadata status: {status}")
    print(f"Symbols: {len(metadata)}")
    print(f"Missing sectors: {len(missing_sector)}")
    print(f"Invalid sectors: {len(invalid_sector)}")
    print(f"Normalized labels: {len(normalized_changes)}")
    print(f"Schema warnings: {len(schema_warnings)}")

    return result


if __name__ == "__main__":
    health = validate_industries()
    raise SystemExit(1 if health["status"] == "error" else 0)
