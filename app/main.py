from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import io
from sqlalchemy.orm import Session

from .stats import load_experiment_csv, compute_conversion_stats
from .db import SessionLocal, engine
from . import models
from app.ai_client import generate_report
from app import models


app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

# Create DB tables on startup (simple approach, good enough for this project)
models.Base.metadata.create_all(bind=engine)


# Dependency that gives a DB session to routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request, db: Session = Depends(get_db)):
    """
    Render the main index page with the experiment form.
    """
    experiments = db.query(models.Experiment).all()
    return templates.TemplateResponse(request,
        "index.html",
        {"experiments": experiments},
    )


@app.post("/upload")
async def upload_experiment(
    request: Request,
    name: str = Form(...),
    hypothesis: str = Form(...),
    alpha : float = Form(0.05),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Receive the uploaded CSV, compute stats, save to DB, and redirect to detail page.
    """

    # Basic file type check (not bulletproof, but ok for now)
    if not file.filename.lower().endswith(".csv"):
        experiments = db.query(models.Experiment).all()
        return templates.TemplateResponse(request,
            "index.html",
            {
                "experiments": experiments,
                "error": "Please upload a .csv file.",
            },
            status_code=400,
        )

    try:
        # Read file contents into memory
        contents = await file.read()
        file_obj = io.BytesIO(contents)

        # Load into pandas and compute stats using your stats.py helpers
        df = load_experiment_csv(file_obj)
        stats_dict = compute_conversion_stats(df)
        # stats_dict looks like:
        # {
        #   "A": {"users": ..., "conversions": ..., "conversion_rate": ...},
        #   "B": {"users": ..., "conversions": ..., "conversion_rate": ..., "uplift": ..., "p_value": ...},
        # }

        # 1) Create Experiment row
        experiment = models.Experiment(
            name=name,
            hypothesis=hypothesis,
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)  # gives us experiment.id

        # 2) Create Variant rows
        for variant_name, v in stats_dict.items():
            variant = models.Variant(
                experiment_id=experiment.id,
                name=variant_name,
                users=v["users"],
                conversions=v["conversions"],
                conversion_rate=v["conversion_rate"],
                uplift=v.get("uplift"),      # may be missing for control
                p_value=v.get("p_value"),    # may be missing for control
            )
            db.add(variant)

        db.commit()

        # 3a) Build AI input from computed stats (no recomputation, just summary for the model)
        variants_for_ai = []
        for variant_name, v in stats_dict.items():
            variants_for_ai.append({
                "name": variant_name,
                "users": v.get("users"),
                "conversions": v.get("conversions"),
                "conversion_rate": v.get("conversion_rate"),
                "uplift": v.get("uplift"),
                "p_value": v.get("p_value"),
            })

        # 3b) Generate insight report and recommendation, then persist on the Experiment
        try:
            ai_out = generate_report(experiment, variants_for_ai)
            experiment.report_text = ai_out.get("report_text", "")
            experiment.recommendation = ai_out.get("recommendation", "more_data")
            db.add(experiment)
            db.commit()
            db.refresh(experiment)
        except Exception as ai_err:
            # Non-fatal: if AI fails, proceed without blocking the upload flow
            # (You can surface a soft warning in the UI later if you want.)
            print(f"AI generation failed: {ai_err}")

        # 3) Redirect to the detail page for this experiment
        return RedirectResponse(
            url=request.url_for("experiment_detail", experiment_id=experiment.id),
            status_code=303,
        )

    except Exception as e:
        # Simple error handling for now
        return templates.TemplateResponse(request,
            "index.html",
            {
                "experiments": experiments,
                "error": f"Something went wrong: {e}",
            },
            status_code=400,
        )
@app.get("/experiments", response_class=HTMLResponse)
def list_experiments(
    request: Request,
    db: Session = Depends(get_db),
):
    experiments = (
        db.query(models.Experiment)
        .order_by(models.Experiment.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(request,
        "experiments.html",
        {"request": request, "experiments": experiments},
    )


@app.get("/experiments/{experiment_id}", response_class=HTMLResponse)
def experiment_detail(
    experiment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    experiment = (
        db.query(models.Experiment)
        .filter(models.Experiment.id == experiment_id)
        .first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return templates.TemplateResponse(request,
        "experiment_detail.html",
        {
            "request": request,
            "experiment": experiment,
            "variants": experiment.variants,
        },
    )
@app.get("/experiments", response_class=HTMLResponse)
def list_experiments(
    request: Request,
    db: Session = Depends(get_db),
):
    experiments = (
        db.query(models.Experiment)
        .order_by(models.Experiment.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(request,
        "experiments.html",
        {
            "request": request,
            "experiments": experiments,
        },
    )
@app.get("/experiments/{experiment_id}", response_class=HTMLResponse)
def experiment_detail(
    experiment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    experiment = (
        db.query(models.Experiment)
        .filter(models.Experiment.id == experiment_id)
        .first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return templates.TemplateResponse(request,
        "experiment_detail.html",
        {
            "request": request,
            "experiment": experiment,
            "variants": experiment.variants,
        },
    )
