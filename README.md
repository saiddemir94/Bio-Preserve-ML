# Bio-Preserve-ML

BioPreserve is a machine-learning-assisted peptide screening tool for natural food preservative discovery. It evaluates antimicrobial peptide (AMP) candidates using biophysical feature extraction and a trained Random Forest classifier, with optional food matrix and target pathogen filtering.

## Quick start

**First-time setup:**

```
setup.bat
```

**Daily usage:**

```
start-backend.bat
```

Then open `http://localhost:8000`.

> The frontend is served directly from the backend — no separate frontend server needed.

## How it works

1. Select a **data source**: use the built-in system peptide pool (DBAASP-based) or upload your own CSV.
2. Select an **analysis mode**: general screening, food-focused, pathogen-focused, or combined.
3. Click **Taramayı başlat** — results appear in a filterable table.
4. Download the candidate report as CSV.

## CSV upload format

If using your own file, it must have a `sequence` column:

```csv
sequence
KWKLFKKIGAVLKVL
LLKKLLKKLLKK
RWKRLKRLKRLK
```

## Requirements

- Python 3.12
- Node.js and npm (only needed for development / rebuilding the frontend)

## Project layout

```
pipeline.py                         — peptide screening pipeline
backend/main.py                     — FastAPI application (serves API + frontend)
frontend/                           — React client (Vite)
features/feature_extraction.py      — biophysical feature computation
data_ingestion/build_amp_dataset.py — raw AMP export normalization
ml/train_model.py                   — model training script
data/                               — peptide pool, datasets, and rule configs
outputs/                            — generated reports
```

## Model

- Algorithm: Random Forest (120 trees, max depth 7)
- Features: peptide length, net charge, hydrophobic ratio, key amino acid ratio
- Training set: ~9,200 sequences from DBAASP and DRAMP databases
- Accuracy: ~70% on held-out test split

## Retraining the model

```bash
# 1. Add raw exports to data/raw/ (dbaasp_export.csv, dramp_export.csv, etc.)
python -m data_ingestion.build_amp_dataset

# 2. Train
python -m ml.train_model
```

## Deployment

The app is configured for single-service deployment on Render. The backend builds and serves the frontend from `frontend/dist`.
