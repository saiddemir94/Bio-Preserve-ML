from pathlib import Path

import pandas as pd

from features.feature_extraction import extract_features


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_PATH = BASE_DIR / "data" / "amp_dataset.csv"
MASTER_OUTPUT_PATH = BASE_DIR / "data" / "amp_master_dataset.csv"
MIC_ACTIVITY_THRESHOLD = 32.0

DRAMP_ID_MARKERS = {"dramp_id"}
ACTIVITY_SKIP_VALUES = {"", "unknown", "unkonw", "nan", "n/a", "not determined"}

SOURCE_CONFIGS = {
    "dbaasp": {
        "sep": ",",
        "sequence": ["sequence", "peptide_sequence", "seq"],
        "target": ["target", "target_organism", "activity_target", "species"],
        "mic": ["mic", "mic_value", "activity", "value"],
        "unit": ["unit", "mic_unit", "activity_unit"],
        "label": ["label", "active_label"],
    },
    "dramp": {
        "sep": ",",
        "sequence": ["sequence", "peptide_sequence", "seq"],
        "target": ["target", "target_organism", "activity_target", "species"],
        "mic": ["mic", "mic_value", "activity", "value"],
        "unit": ["unit", "mic_unit", "activity_unit"],
        "label": ["label", "active_label"],
    },
    "camp": {
        "sep": "\t",
        "sequence": ["seqence", "sequence", "seq"],
        "target": ["source_organism", "taxonomy"],
        "mic": [],
        "unit": [],
        "label": [],
    },
    "custom": {
        "sep": ",",
        "sequence": ["sequence", "peptide_sequence", "seq"],
        "target": ["target", "target_organism"],
        "mic": ["mic", "mic_value"],
        "unit": ["unit", "mic_unit"],
        "label": ["label", "active_label"],
    },
}


def normalize_columns(frame):
    renamed_columns = {}
    for column in frame.columns:
        clean_name = (
            str(column)
            .strip()
            .replace("﻿", "")
            .replace("\xef\xbb\xbf", "")
            .replace("ï»¿", "")
            .lower()
        )
        renamed_columns[column] = clean_name
    return frame.rename(columns=renamed_columns)


def resolve_column(frame, aliases, required=False):
    for alias in aliases:
        if alias in frame.columns:
            return alias
    if required:
        raise ValueError(f"Required columns not found. Expected one of: {aliases}")
    return None


def normalize_source_name(path):
    stem = path.stem.lower()
    for source_name in SOURCE_CONFIGS:
        if stem.startswith(source_name):
            return source_name
    return "custom"


def clean_numeric(value):
    if pd.isna(value):
        return None

    text = str(value).strip().replace(",", ".")
    filtered = "".join(character for character in text if character.isdigit() or character == ".")
    try:
        return float(filtered) if filtered else None
    except ValueError:
        return None


def infer_label(raw_label, mic_value, mic_unit):
    if raw_label is not None and str(raw_label).strip() != "":
        normalized_label = str(raw_label).strip().lower()
        if normalized_label in {"1", "true", "active", "yes", "amp"}:
            return 1
        if normalized_label in {"0", "false", "inactive", "no", "non-amp"}:
            return 0

    if mic_value is None:
        return None

    normalized_unit = (mic_unit or "").strip().lower()
    if normalized_unit in {"um", "micromolar", "ug/ml", "µm", "μm"}:
        return 1 if mic_value <= MIC_ACTIVITY_THRESHOLD else 0

    return 1 if mic_value <= MIC_ACTIVITY_THRESHOLD else 0


def infer_activity_label(row):
    activity = str(row.get("activity", "")).strip().lower()
    if activity in ACTIVITY_SKIP_VALUES:
        return None
    return 1 if "antibacterial" in activity else 0


def read_csv_with_fallback(path, sep=","):
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            frame = pd.read_csv(path, sep=sep, encoding=encoding)
            if frame.shape[1] > 1:
                return frame
            return pd.read_csv(path, sep=None, engine="python", encoding=encoding)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    return pd.read_csv(path, sep=None, engine="python", encoding="latin-1")


def process_source_file(path):
    path_source = normalize_source_name(path)
    config = SOURCE_CONFIGS[path_source]
    sep = config.get("sep", ",")

    frame = normalize_columns(read_csv_with_fallback(path, sep=sep))

    # Detect DRAMP format by column presence regardless of file name
    if DRAMP_ID_MARKERS & set(frame.columns):
        source_name = "dramp"
        config = SOURCE_CONFIGS["dramp"]
    else:
        source_name = path_source

    sequence_column = resolve_column(frame, config["sequence"], required=True)
    target_column = resolve_column(frame, config["target"])
    mic_column = resolve_column(frame, config.get("mic", []))
    unit_column = resolve_column(frame, config.get("unit", []))
    label_column = resolve_column(frame, config.get("label", []))

    records = []

    for _, row in frame.iterrows():
        sequence = str(row[sequence_column]).strip().upper() if pd.notna(row[sequence_column]) else ""
        if not sequence:
            continue

        try:
            features = extract_features(sequence)
        except ValueError:
            continue

        if source_name in ("camp", "dramp"):
            label = infer_activity_label(row)
        else:
            mic_value = clean_numeric(row[mic_column]) if mic_column else None
            mic_unit = str(row[unit_column]).strip() if unit_column and pd.notna(row[unit_column]) else ""
            raw_label = row[label_column] if label_column else None
            label = infer_label(raw_label, mic_value, mic_unit)

        if label is None:
            continue

        mic_value_out = clean_numeric(row[mic_column]) if mic_column else None
        mic_unit_out = str(row[unit_column]).strip() if unit_column and pd.notna(row[unit_column]) else ""

        records.append(
            {
                "source": source_name,
                "sequence": sequence,
                "target_organism": str(row[target_column]).strip() if target_column and pd.notna(row[target_column]) else "",
                "mic_value": mic_value_out,
                "mic_unit": mic_unit_out,
                "label": int(label),
                **features,
            }
        )

    return records


def deduplicate_records(frame):
    prioritized = frame.sort_values(
        by=["sequence", "label", "mic_value"],
        ascending=[True, False, True],
        na_position="last",
    )
    return prioritized.drop_duplicates(subset=["sequence"], keep="first").reset_index(drop=True)


def build_datasets():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(RAW_DIR.glob("*.csv"))

    if not raw_files:
        raise FileNotFoundError(
            "No raw CSV files were found in data/raw. "
            "Add exports such as dbaasp_export.csv or dramp_export.csv first."
        )

    records = []
    for path in raw_files:
        records.extend(process_source_file(path))

    if not records:
        raise ValueError("No usable AMP records were produced from the raw source files.")

    master_frame = deduplicate_records(pd.DataFrame(records))
    training_frame = master_frame[
        [
            "length",
            "net_charge",
            "hydrophobic_ratio",
            "key_amino_acid_ratio",
            "label",
        ]
    ].copy()

    master_frame.to_csv(MASTER_OUTPUT_PATH, index=False, encoding="utf-8-sig")
    training_frame.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"Master dataset saved to: {MASTER_OUTPUT_PATH}")
    print(f"Training dataset saved to: {OUTPUT_PATH}")
    print(f"Total unique sequences: {len(master_frame)}")
    print(f"Positive labels: {int((master_frame['label'] == 1).sum())}")
    print(f"Negative labels: {int((master_frame['label'] == 0).sum())}")


if __name__ == "__main__":
    build_datasets()
