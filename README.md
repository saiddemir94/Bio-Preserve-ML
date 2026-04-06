# Bio-Preserve-ML

BioPreserve is a peptide screening project for natural preservative discovery. The stack uses:

- `FastAPI` for upload and report APIs
- `React + Vite` for the web interface
- a shared Python pipeline for biological rules, AMP scoring, and food compatibility analysis
- a lightweight AMP dataset ingestion layer for future database growth

## Quick local usage

First setup:

1. Run `setup.bat`

Daily usage:

1. Run `start-backend.bat`
2. Run `start-frontend.bat`
3. Open `http://localhost:5173`

## Requirements

- Python `3.12`
- Node.js and `npm`

## CSV format

Upload a CSV file with a `sequence` column.

```csv
sequence
KWKLFKKIGAVLKVL
LLKKLLKKLLKK
RWKRLKRLKRLK
```

## AMP dataset growth workflow

Raw database exports should be placed under `data/raw/`.

Supported source prefixes:

- `dbaasp_*.csv`
- `dramp_*.csv`
- `custom_*.csv`

Sample raw file already included:

- `data/raw/custom_sample_amp_data.csv`

To rebuild the training dataset and retrain the model:

1. Run `rebuild-amp-dataset.bat`

Or manually:

```powershell
& ".\.venv\Scripts\python.exe" data_ingestion\build_amp_dataset.py
& ".\.venv\Scripts\python.exe" ml\train_model.py
```

This produces:

- `data/amp_master_dataset.csv`: normalized master AMP table with metadata
- `data/amp_dataset.csv`: compact training table used by the current model

## Project layout

- `pipeline.py`: reusable peptide screening pipeline
- `backend/main.py`: FastAPI application
- `frontend/`: React client
- `features/feature_extraction.py`: peptide feature extraction
- `data_ingestion/build_amp_dataset.py`: raw AMP export normalization
- `ml/train_model.py`: model training script
- `data/`: sample datasets and configuration files
- `outputs/`: generated upload files and candidate reports

## API endpoints

- `GET /api/health`
- `POST /api/run-pipeline`
- `GET /api/reports/{filename}`
