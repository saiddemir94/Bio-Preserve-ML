import csv
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from features.feature_extraction import valid_amino_acids

DATA_DIR = BASE_DIR / "data"
RAW_OUTPUT_PATH = DATA_DIR / "raw" / "dbaasp_targeted_peptides.csv"
FOOD_CONTEXT_PATH = DATA_DIR / "food_context.json"
DBAASP_BASE_URL = "https://dbaasp.dbaasp.niaidprod.net"
REQUEST_DELAY_SECONDS = 0.03
MAX_SEARCH_ROWS_PER_TARGET = 160
SYNTHESIS_TYPE = "Ribosomal"
COMPLEXITY = "Monomer"
ACTIVE_MIC_THRESHOLD = 25.0
INACTIVE_MIC_THRESHOLD = 100.0
TARGET_ALIASES = {
    "E. coli": "Escherichia coli",
    "Salmonella": "Salmonella enterica",
}


def read_json(url):
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def dbaasp_get(path, params=None):
    query = f"?{urlencode(params or {}, doseq=True)}" if params else ""
    return read_json(f"{DBAASP_BASE_URL}{path}{query}")


def canonical_target_name(target_name):
    return TARGET_ALIASES.get(target_name, target_name)


def load_target_pathogens():
    with FOOD_CONTEXT_PATH.open(encoding="utf-8") as file:
        context = json.load(file)

    return [canonical_target_name(target) for target in context.get("target_pathogens", [])]


def is_canonical_sequence(sequence):
    normalized = sequence.strip().upper()
    return bool(normalized) and set(normalized).issubset(valid_amino_acids)


def clean_text(value):
    return "" if value is None else str(value).strip()


def extract_name(value):
    if isinstance(value, dict):
        return clean_text(value.get("name"))
    return clean_text(value)


def infer_label(activity, measure_name):
    if activity is None:
        return None

    if measure_name.upper() != "MIC":
        return None

    if activity <= ACTIVE_MIC_THRESHOLD:
        return 1

    if activity > INACTIVE_MIC_THRESHOLD:
        return 0

    return None


def collect_activity_records(peptide, target_query):
    sequence = clean_text(peptide.get("sequence")).upper()
    if not is_canonical_sequence(sequence):
        return []

    if peptide.get("sequenceLength", len(sequence)) > 30:
        return []

    if extract_name(peptide.get("complexity")).lower() != "monomer":
        return []

    records = []

    for activity_row in peptide.get("targetActivities") or []:
        target_species = extract_name(activity_row.get("targetSpecies"))
        if target_query.lower() not in target_species.lower():
            continue

        activity = activity_row.get("activity")
        measure_name = extract_name(activity_row.get("activityMeasureGroup"))
        label = infer_label(activity, measure_name)
        if label is None:
            continue

        records.append(
            {
                "dbaasp_id": clean_text(peptide.get("dbaaspId")),
                "name": clean_text(peptide.get("name")),
                "sequence": sequence,
                "target_organism": target_species,
                "mic_value": activity,
                "mic_unit": extract_name(activity_row.get("unit")),
                "label": label,
                "synthesis_type": extract_name(peptide.get("synthesisType")),
                "complexity": extract_name(peptide.get("complexity")),
            }
        )

    return records


def fetch_target_records(target_query):
    search_result = dbaasp_get(
        "/peptides",
        {
            "targetSpecies.value": target_query,
            "synthesisType.value": SYNTHESIS_TYPE,
            "complexity.value": COMPLEXITY,
            "limit": MAX_SEARCH_ROWS_PER_TARGET,
            "offset": 0,
        },
    )
    records = []

    for item in search_result.get("data", []):
        peptide_id = item["id"]
        peptide = dbaasp_get(f"/peptides/{peptide_id}")
        records.extend(collect_activity_records(peptide, target_query))
        time.sleep(REQUEST_DELAY_SECONDS)

    return records


def deduplicate_records(records):
    best_records = {}

    for record in records:
        sequence = record["sequence"]
        current = best_records.get(sequence)
        if current is None:
            best_records[sequence] = record
            continue

        current_rank = (current["label"], -float(current["mic_value"]))
        next_rank = (record["label"], -float(record["mic_value"]))
        if next_rank > current_rank:
            best_records[sequence] = record

    return sorted(best_records.values(), key=lambda item: (item["label"], item["mic_value"]))


def write_records(records):
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dbaasp_id",
        "name",
        "sequence",
        "target_organism",
        "mic_value",
        "mic_unit",
        "label",
        "synthesis_type",
        "complexity",
    ]

    with RAW_OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main():
    all_records = []
    for target in load_target_pathogens():
        target_records = fetch_target_records(target)
        print(f"{target}: {len(target_records)} usable activity records")
        all_records.extend(target_records)

    unique_records = deduplicate_records(all_records)
    write_records(unique_records)

    positives = sum(1 for record in unique_records if record["label"] == 1)
    negatives = sum(1 for record in unique_records if record["label"] == 0)
    print(f"Saved: {RAW_OUTPUT_PATH}")
    print(f"Unique sequences: {len(unique_records)}")
    print(f"Positive labels: {positives}")
    print(f"Negative labels: {negatives}")


if __name__ == "__main__":
    main()
