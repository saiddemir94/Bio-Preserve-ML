import json
from pathlib import Path

import joblib
import pandas as pd

from features.feature_extraction import extract_features


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ML_DIR = BASE_DIR / "ml"
OUTPUT_DIR = BASE_DIR / "outputs"
DEFAULT_INPUT_PATH = DATA_DIR / "database_peptides.csv"
DEFAULT_OUTPUT_PATH = OUTPUT_DIR / "candidate_report.csv"


def load_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


RULES = load_json(DATA_DIR / "biological_rules.json")
FOOD_CONTEXT = load_json(DATA_DIR / "food_context.json")
MODEL = joblib.load(ML_DIR / "model.pkl")
DEFAULT_FEATURE_COLUMNS = [
    "length",
    "net_charge",
    "hydrophobic_ratio",
    "key_amino_acid_ratio",
]


def passes_biological_rules(features):
    reasons = []

    if not RULES["length_range"][0] <= features["length"] <= RULES["length_range"][1]:
        reasons.append("Length is outside the target range.")

    if not RULES["charge_range"][0] <= features["net_charge"] <= RULES["charge_range"][1]:
        reasons.append("Net charge is outside the target range.")

    if not (
        RULES["hydrophobicity_range"][0]
        <= features["hydrophobic_ratio"]
        <= RULES["hydrophobicity_range"][1]
    ):
        reasons.append("Hydrophobicity ratio is outside the target range.")

    if features["key_amino_acid_ratio"] < 0.25:
        reasons.append("Key amino acid content is below the desired threshold.")

    return len(reasons) == 0, reasons


def check_food_compatibility(features):
    suitable_foods = []
    rejected_foods = []

    for food_matrix in FOOD_CONTEXT["food_matrices"]:
        reasons = []

        if food_matrix["salt_ratio"] > 2 and features["net_charge"] < 4:
            reasons.append("Insufficient charge for a high-salt environment.")

        if food_matrix["pH"] < 5 and features["length"] > 22:
            reasons.append("Sequence is too long for an acidic environment.")

        if food_matrix["fat_content"] == "high" and not (
            0.35 <= features["hydrophobic_ratio"] <= 0.60
        ):
            reasons.append("Hydrophobicity is not ideal for a high-fat matrix.")

        if reasons:
            rejected_foods.append(
                {"product": food_matrix["product"], "reasons": "; ".join(reasons)}
            )
        else:
            suitable_foods.append(food_matrix["product"])

    return suitable_foods, rejected_foods


def predict_candidate(features):
    feature_row = {
        "length": features["length"],
        "net_charge": features["net_charge"],
        "hydrophobic_ratio": features["hydrophobic_ratio"],
        "key_amino_acid_ratio": features["key_amino_acid_ratio"],
    }
    model_feature_columns = list(
        getattr(MODEL, "feature_names_in_", DEFAULT_FEATURE_COLUMNS[:3])
    )
    feature_frame = pd.DataFrame(
        [{column: feature_row[column] for column in model_feature_columns}]
    )
    predicted_label = int(MODEL.predict(feature_frame)[0])
    probability = float(MODEL.predict_proba(feature_frame)[0][1])
    return predicted_label, probability


def evaluate_sequence(sequence):
    cleaned_sequence = str(sequence).strip().upper()

    if not cleaned_sequence:
        return {
            "sequence": "",
            "length": 0,
            "net_charge": 0,
            "hydrophobic_ratio": 0.0,
            "key_amino_acid_ratio": 0.0,
            "passed_biological_rules": False,
            "rule_notes": "Sequence is empty.",
            "ml_prediction": 0,
            "ml_probability": 0.0,
            "compatible_foods": "",
            "food_notes": "Not evaluated.",
            "final_status": "Rejected",
        }

    try:
        features = extract_features(cleaned_sequence)
    except ValueError as error:
        return {
            "sequence": cleaned_sequence,
            "length": 0,
            "net_charge": 0,
            "hydrophobic_ratio": 0.0,
            "key_amino_acid_ratio": 0.0,
            "passed_biological_rules": False,
            "rule_notes": str(error),
            "ml_prediction": 0,
            "ml_probability": 0.0,
            "compatible_foods": "",
            "food_notes": "Not evaluated.",
            "final_status": "Rejected",
        }

    passed_rules, rule_reasons = passes_biological_rules(features)

    result = {
        "sequence": cleaned_sequence,
        "length": features["length"],
        "net_charge": features["net_charge"],
        "hydrophobic_ratio": round(features["hydrophobic_ratio"], 4),
        "key_amino_acid_ratio": round(features["key_amino_acid_ratio"], 4),
        "passed_biological_rules": passed_rules,
        "rule_notes": "Passed all biological filters."
        if passed_rules
        else "; ".join(rule_reasons),
        "ml_prediction": 0,
        "ml_probability": 0.0,
        "compatible_foods": "",
        "food_notes": "Not evaluated because biological filters failed.",
        "final_status": "Rejected",
    }

    if not passed_rules:
        return result

    predicted_label, probability = predict_candidate(features)
    result["ml_prediction"] = predicted_label
    result["ml_probability"] = round(probability, 4)

    if predicted_label != 1:
        result["food_notes"] = "Rejected by the machine learning model."
        return result

    suitable_foods, rejected_foods = check_food_compatibility(features)
    result["compatible_foods"] = ", ".join(suitable_foods)

    if suitable_foods:
        result["food_notes"] = (
            "Compatible with selected food matrices."
            if not rejected_foods
            else "Rejected foods: "
            + " | ".join(
                f"{item['product']}: {item['reasons']}" for item in rejected_foods
            )
        )
        result["final_status"] = "Approved"
    else:
        result["food_notes"] = "Failed food compatibility checks."

    return result


def process_sequences_dataframe(input_frame, sequence_column="sequence"):
    normalized_columns = {
        column: str(column).strip().replace("\ufeff", "") for column in input_frame.columns
    }
    input_frame = input_frame.rename(columns=normalized_columns)

    if sequence_column not in input_frame.columns:
        lower_map = {column.lower(): column for column in input_frame.columns}
        if sequence_column.lower() in lower_map:
            sequence_column = lower_map[sequence_column.lower()]

    if sequence_column not in input_frame.columns:
        raise ValueError(
            f"CSV file must contain a '{sequence_column}' column with peptide sequences."
        )

    results = [
        evaluate_sequence(sequence)
        for sequence in input_frame[sequence_column].fillna("")
    ]
    result_frame = pd.DataFrame(results).sort_values(
        by=["final_status", "ml_probability", "net_charge"],
        ascending=[False, False, False],
    )
    return result_frame


def save_report(result_frame, output_path=DEFAULT_OUTPUT_PATH):
    output_path = Path(output_path)
    output_path.parent.mkdir(exist_ok=True)
    result_frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def process_csv_file(input_path=DEFAULT_INPUT_PATH, output_path=DEFAULT_OUTPUT_PATH):
    input_frame = pd.read_csv(input_path)
    result_frame = process_sequences_dataframe(input_frame)
    saved_path = save_report(result_frame, output_path)
    return result_frame, saved_path


def print_summary(result_frame, output_path):
    approved = result_frame[result_frame["final_status"] == "Approved"]

    print("\nBioPreserve - AI candidate screening report\n")
    print(f"Total sequences evaluated: {len(result_frame)}")
    print(f"Approved candidates: {len(approved)}")
    print(f"Report file: {output_path}")

    if approved.empty:
        print("\nNo candidates passed all stages.")
        return

    print("\nTop approved candidates:\n")
    for _, row in approved.head(5).iterrows():
        print(f"Sequence: {row['sequence']}")
        print(f"ML probability: {row['ml_probability']:.2f}")
        print(f"Compatible foods: {row['compatible_foods']}")
        print()


def run_pipeline(input_path=DEFAULT_INPUT_PATH, output_path=DEFAULT_OUTPUT_PATH):
    result_frame, saved_path = process_csv_file(input_path, output_path)
    print_summary(result_frame, saved_path)
    return result_frame, saved_path


if __name__ == "__main__":
    run_pipeline()
