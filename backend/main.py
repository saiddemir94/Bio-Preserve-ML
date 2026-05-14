import os
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pipeline import (
    DEFAULT_INPUT_PATH,
    OUTPUT_DIR,
    available_foods,
    available_pathogens,
    process_sequences_dataframe,
    save_report,
)


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
UPLOAD_DIR = OUTPUT_DIR / "uploads"
ALLOWED_EXTENSIONS = {".csv"}
DEFAULT_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def get_allowed_origins():
    configured_origins = os.getenv("FRONTEND_ORIGINS", "")
    extra_origins = [
        origin.strip() for origin in configured_origins.split(",") if origin.strip()
    ]
    return DEFAULT_ALLOWED_ORIGINS + extra_origins

app = FastAPI(
    title="BioPreserve API",
    description="Upload peptide CSV files and run the BioPreserve screening pipeline.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_summary(result_frame):
    approved_count = int((result_frame["final_status"] == "Approved").sum())
    rejected_count = int((result_frame["final_status"] == "Rejected").sum())
    average_probability = (
        float(result_frame["ml_probability"].mean()) if not result_frame.empty else 0.0
    )

    return {
        "totalSequences": len(result_frame),
        "approvedCount": approved_count,
        "rejectedCount": rejected_count,
        "averageProbability": round(average_probability, 4),
    }


def ensure_csv_upload(file):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only CSV uploads are supported.")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/options")
def get_options():
    return {
        "foods": available_foods(),
        "pathogens": available_pathogens(),
    }


@app.get("/api/run-pipeline")
def run_pipeline_system(
    selected_food: str = "",
    target_pathogen: str = "",
):
    report_path = OUTPUT_DIR / f"{uuid4().hex}_candidate_report.csv"

    try:
        input_frame = pd.read_csv(DEFAULT_INPUT_PATH)
        result_frame = process_sequences_dataframe(
            input_frame,
            selected_food=selected_food,
            target_pathogen=target_pathogen,
        )
        save_report(result_frame, report_path)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "summary": build_summary(result_frame),
        "results": result_frame.to_dict(orient="records"),
        "downloadUrl": f"/api/reports/{report_path.name}",
    }


@app.post("/api/run-pipeline")
async def run_pipeline_upload(
    sequence_file: UploadFile = File(...),
    selected_food: str = Form(""),
    target_pathogen: str = Form(""),
):
    ensure_csv_upload(sequence_file)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_id = uuid4().hex
    upload_path = UPLOAD_DIR / f"{upload_id}_input.csv"
    report_path = OUTPUT_DIR / f"{upload_id}_candidate_report.csv"

    try:
        content = await sequence_file.read()
        upload_path.write_bytes(content)

        input_frame = pd.read_csv(upload_path)
        result_frame = process_sequences_dataframe(
            input_frame,
            selected_food=selected_food,
            target_pathogen=target_pathogen,
        )
        save_report(result_frame, report_path)
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pipeline could not be completed. "
                f"{error}. Ensure the CSV includes a sequence column and the model is up to date."
            ),
        ) from error

    return {
        "summary": build_summary(result_frame),
        "results": result_frame.to_dict(orient="records"),
        "downloadUrl": f"/api/reports/{report_path.name}",
    }


@app.get("/api/reports/{filename}")
def download_report(filename: str):
    report_path = OUTPUT_DIR / filename

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Requested report file could not be found.")

    return FileResponse(report_path, filename=filename, media_type="text/csv")


if FRONTEND_DIST_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST_DIR / "assets"),
        name="frontend-assets",
    )

    @app.get("/", include_in_schema=False)
    def serve_root():
        return FileResponse(FRONTEND_DIST_DIR / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        requested_path = FRONTEND_DIST_DIR / full_path

        if requested_path.is_file():
            return FileResponse(requested_path)

        return FileResponse(FRONTEND_DIST_DIR / "index.html")
