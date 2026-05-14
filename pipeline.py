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
PATHOGEN_RULES = {
    "Listeria monocytogenes": {
        "min_charge": 3,
        "hydrophobicity_range": (0.40, 0.65),
        "note": "Gram-pozitif hedef patojen profili.",
    },
    "Salmonella": {
        "min_charge": 4,
        "hydrophobicity_range": (0.35, 0.60),
        "note": "Gram-negatif hedef patojen profili.",
    },
    "E. coli": {
        "min_charge": 4,
        "hydrophobicity_range": (0.35, 0.60),
        "note": "Gram-negatif hedef patojen profili.",
    },
}


def available_foods():
    return [food_matrix["product"] for food_matrix in FOOD_CONTEXT["food_matrices"]]


def available_pathogens():
    return FOOD_CONTEXT.get("target_pathogens", list(PATHOGEN_RULES))


def find_food_matrix(selected_food):
    if not selected_food:
        return None

    normalized_food = selected_food.strip().lower()
    for food_matrix in FOOD_CONTEXT["food_matrices"]:
        if food_matrix["product"].lower() == normalized_food:
            return food_matrix

    valid_foods = ", ".join(available_foods())
    raise ValueError(f"Unknown food matrix '{selected_food}'. Valid options: {valid_foods}")


def validate_pathogen(target_pathogen):
    if not target_pathogen:
        return None

    normalized_pathogen = target_pathogen.strip().lower()
    for pathogen in available_pathogens():
        if pathogen.lower() == normalized_pathogen:
            return pathogen

    valid_pathogens = ", ".join(available_pathogens())
    raise ValueError(f"Unknown target pathogen '{target_pathogen}'. Valid options: {valid_pathogens}")


def passes_biological_rules(features):
    reasons = []

    if not RULES["length_range"][0] <= features["length"] <= RULES["length_range"][1]:
        reasons.append("Uzunluk hedef aralığının dışında.")

    if not RULES["charge_range"][0] <= features["net_charge"] <= RULES["charge_range"][1]:
        reasons.append("Net yük hedef aralığının dışında.")

    if not (
        RULES["hydrophobicity_range"][0]
        <= features["hydrophobic_ratio"]
        <= RULES["hydrophobicity_range"][1]
    ):
        reasons.append("Hidrofobisite oranı hedef aralığının dışında.")

    if features["key_amino_acid_ratio"] < 0.25:
        reasons.append("Anahtar amino asit içeriği istenen eşiğin altında.")

    return len(reasons) == 0, reasons


def check_pathogen_compatibility(features, target_pathogen):
    pathogen = validate_pathogen(target_pathogen)
    if not pathogen:
        return True, "Hedef patojen seçilmedi."

    rules = PATHOGEN_RULES.get(pathogen)
    if not rules:
        return True, f"{pathogen} için tanımlı patojen kuralı bulunamadı."

    reasons = []
    if features["net_charge"] < rules["min_charge"]:
        reasons.append(f"{pathogen} için net yük düşük.")

    min_hydrophobicity, max_hydrophobicity = rules["hydrophobicity_range"]
    if not min_hydrophobicity <= features["hydrophobic_ratio"] <= max_hydrophobicity:
        reasons.append(f"Hidrofobisite {pathogen} için tercih edilen aralığın dışında.")

    if reasons:
        return False, "; ".join(reasons)

    return True, rules["note"]


def check_food_compatibility(features, selected_food=None):
    suitable_foods = []
    rejected_foods = []
    food_matrices = [find_food_matrix(selected_food)] if selected_food else FOOD_CONTEXT["food_matrices"]

    for food_matrix in food_matrices:
        reasons = []

        if food_matrix["salt_ratio"] > 2 and features["net_charge"] < 4:
            reasons.append("Yüksek tuzlu ortam için yük yetersiz.")

        if food_matrix["pH"] < 5 and features["length"] > 22:
            reasons.append("Dizi asidik ortam için çok uzun.")

        if food_matrix["fat_content"] == "high" and not (
            0.35 <= features["hydrophobic_ratio"] <= 0.60
        ):
            reasons.append("Hidrofobisite yüksek yağlı matris için uygun değil.")

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


def evaluate_sequence(sequence, selected_food=None, target_pathogen=None):
    cleaned_sequence = str(sequence).strip().upper()
    selected_food_name = selected_food or ""
    target_pathogen_name = target_pathogen or ""

    if not cleaned_sequence:
        return {
            "sequence": "",
            "target_food": selected_food_name,
            "target_pathogen": target_pathogen_name,
            "length": 0,
            "net_charge": 0,
            "hydrophobic_ratio": 0.0,
            "key_amino_acid_ratio": 0.0,
            "passed_biological_rules": False,
            "rule_notes": "Dizi boş.",
            "ml_prediction": 0,
            "ml_probability": 0.0,
            "compatible_foods": "",
            "food_notes": "Değerlendirilmedi.",
            "final_status": "Rejected",
        }

    try:
        features = extract_features(cleaned_sequence)
    except ValueError as error:
        return {
            "sequence": cleaned_sequence,
            "target_food": selected_food_name,
            "target_pathogen": target_pathogen_name,
            "length": 0,
            "net_charge": 0,
            "hydrophobic_ratio": 0.0,
            "key_amino_acid_ratio": 0.0,
            "passed_biological_rules": False,
            "rule_notes": str(error),
            "ml_prediction": 0,
            "ml_probability": 0.0,
            "compatible_foods": "",
            "food_notes": "Değerlendirilmedi.",
            "final_status": "Rejected",
        }

    passed_rules, rule_reasons = passes_biological_rules(features)

    result = {
        "sequence": cleaned_sequence,
        "target_food": selected_food_name,
        "target_pathogen": target_pathogen_name,
        "length": features["length"],
        "net_charge": features["net_charge"],
        "hydrophobic_ratio": round(features["hydrophobic_ratio"], 4),
        "key_amino_acid_ratio": round(features["key_amino_acid_ratio"], 4),
        "passed_biological_rules": passed_rules,
        "rule_notes": "Tüm biyolojik filtreler geçildi."
        if passed_rules
        else "; ".join(rule_reasons),
        "ml_prediction": 0,
        "ml_probability": 0.0,
        "compatible_foods": "",
        "food_notes": "Biyolojik filtreler geçilemediği için değerlendirilmedi.",
        "final_status": "Rejected",
    }

    if not passed_rules:
        return result

    predicted_label, probability = predict_candidate(features)
    result["ml_prediction"] = predicted_label
    result["ml_probability"] = round(probability, 4)

    if predicted_label != 1:
        result["food_notes"] = "Makine öğrenimi modeli tarafından elendi."
        return result

    pathogen_ok, pathogen_note = check_pathogen_compatibility(features, target_pathogen)
    if not pathogen_ok:
        result["food_notes"] = pathogen_note
        return result

    suitable_foods, rejected_foods = check_food_compatibility(features, selected_food)
    result["compatible_foods"] = ", ".join(suitable_foods)

    if suitable_foods:
        result["food_notes"] = (
            f"{pathogen_note} Seçilen gıda matrisiyle uyumlu."
            if not rejected_foods
            else "Uyumsuz gıdalar: "
            + " | ".join(
                f"{item['product']}: {item['reasons']}" for item in rejected_foods
            )
        )
        result["final_status"] = "Approved"
    else:
        result["food_notes"] = "Gıda uyumluluk kontrolleri başarısız."

    return result


def process_sequences_dataframe(
    input_frame,
    sequence_column="sequence",
    selected_food=None,
    target_pathogen=None,
):
    find_food_matrix(selected_food)
    validate_pathogen(target_pathogen)

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
        evaluate_sequence(sequence, selected_food=selected_food, target_pathogen=target_pathogen)
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
