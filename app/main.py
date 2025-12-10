from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import io

from app.stats import load_experiment_csv, compute_conversion_stats

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """
    Render the main index page with the experiment form.
    """
    return templates.TemplateResponse(
        "index.html",
        {"request": request},
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload_experiment(
    request: Request,
    name: str = Form(...),
    hypothesis: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Receive the uploaded CSV, compute stats, and show a simple results page.
    """

    # Basic file type check (not bulletproof, but ok for now)
    if not file.filename.lower().endswith(".csv"):
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "name": name,
                "hypothesis": hypothesis,
                "error": "Please upload a .csv file.",
                "stats": None,
            },
            status_code=400,
        )

    try:
        # Read file contents into memory
        contents = await file.read()
        file_obj = io.BytesIO(contents)

        # Load into pandas and compute stats
        df = load_experiment_csv(file_obj)
        stats = compute_conversion_stats(df)

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "name": name,
                "hypothesis": hypothesis,
                "stats": stats,
                "error": None,
            },
        )
    except Exception as e:
        # For now, show a simple error on the page
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "name": name,
                "hypothesis": hypothesis,
                "stats": None,
                "error": f"Something went wrong: {e}",
            },
            status_code=400,
        )
