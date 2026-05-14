"""
Veriyi eğitim/test olarak böler, modeli yeniden eğitir,
test dizilerini database_peptides.csv olarak kaydeder.
"""
import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ML_DIR = BASE_DIR / "ml"

FEATURE_COLUMNS = ["length", "net_charge", "hydrophobic_ratio", "key_amino_acid_ratio"]
TEST_SIZE = 0.20
RANDOM_STATE = 42

master = pd.read_csv(DATA_DIR / "amp_master_dataset.csv")

train_df, test_df = train_test_split(
    master,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=master["label"],
)

train_df[FEATURE_COLUMNS + ["label"]].to_csv(DATA_DIR / "amp_dataset.csv", index=False)

test_df[["sequence"]].to_csv(DATA_DIR / "database_peptides.csv", index=False)

x_train = train_df[FEATURE_COLUMNS]
y_train = train_df["label"]
x_test = test_df[FEATURE_COLUMNS]
y_test = test_df["label"]

model = RandomForestClassifier(
    n_estimators=120,
    max_depth=7,
    min_samples_leaf=1,
    random_state=RANDOM_STATE,
)
model.fit(x_train, y_train)

predictions = model.predict(x_test)
accuracy = accuracy_score(y_test, predictions)

joblib.dump(model, ML_DIR / "model.pkl")

print(f"Toplam veri:   {len(master):>6}")
print(f"Egitim seti:   {len(train_df):>6}  (%{len(train_df)/len(master)*100:.0f})")
print(f"Test seti:     {len(test_df):>6}  (%{len(test_df)/len(master)*100:.0f})")
print(f"Test dogrulugu: {accuracy:.4f}")
print()
print(classification_report(y_test, predictions, digits=4))
print(f"Test dizileri kaydedildi: {DATA_DIR / 'database_peptides.csv'}")
print(f"Model guncellendi:        {ML_DIR / 'model.pkl'}")
