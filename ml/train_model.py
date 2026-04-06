from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "amp_dataset.csv"
MODEL_PATH = BASE_DIR / "ml" / "model.pkl"
FEATURE_COLUMNS = [
    "length",
    "net_charge",
    "hydrophobic_ratio",
    "key_amino_acid_ratio",
]


def load_training_data():
    df = pd.read_csv(DATA_PATH)

    missing_columns = [column for column in FEATURE_COLUMNS + ["label"] if column not in df.columns]
    if missing_columns:
        missing_text = ", ".join(missing_columns)
        raise ValueError(f"Training dataset is missing required columns: {missing_text}")

    return df


def train_model():
    df = load_training_data()

    x = df[FEATURE_COLUMNS]
    y = df["label"]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=120,
        max_depth=7,
        min_samples_leaf=1,
        random_state=42,
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    joblib.dump(model, MODEL_PATH)

    print("Model basariyla kaydedildi.")
    print(f"Training rows: {len(df)}")
    print(f"Positive labels: {int((y == 1).sum())}")
    print(f"Negative labels: {int((y == 0).sum())}")
    print(f"Test accuracy: {accuracy:.3f}")
    print("\nClassification report:\n")
    print(classification_report(y_test, predictions, digits=3))


if __name__ == "__main__":
    train_model()
