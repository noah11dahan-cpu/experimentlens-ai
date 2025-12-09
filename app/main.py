from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import pandas as pd
from io import StringIO

app = FastAPI()

# Tell FastAPI where the templates live
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Show the upload form.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload", response_class=HTMLResponse)
async def upload_experiment(
    request: Request,
    experiment_name: str = Form(...),
    hypothesis: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Handle the CSV upload, compute basic stats, and show results.
    """
    # Read the uploaded file into memory
    content = await file.read()
    text = content.decode("utf-8")

    # Load into a pandas DataFrame
    # Expect columns: user_id, variant, converted
    df = pd.read_csv(StringIO(text))

    # Basic validation
    required_columns = {"user_id", "variant", "converted"}
    if not required_columns.issubset(df.columns):
        error_message = (
            f"CSV must contain columns: {', '.join(required_columns)}. "
            f"Found: {', '.join(df.columns)}"
        )
        return HTMLResponse(error_message, status_code=400)

    # Group by variant and compute stats
    grouped = df.groupby("variant")["converted"].agg(["count", "sum"])
    grouped["conversion_rate"] = grouped["sum"] / grouped["count"]

    # Convert to a list of dicts for the template
    variants = []
    for variant_name, row in grouped.iterrows():
        variants.append(
            {
                "variant_name": variant_name,
                "users": int(row["count"]),
                "conversions": int(row["sum"]),
                "conversion_rate": round(row["conversion_rate"] * 100, 2),
            }
        )

    context = {
        "request": request,
        "experiment_name": experiment_name,
        "hypothesis": hypothesis,
        "variants": variants,
    }

    return templates.TemplateResponse("experiment_detail.html", context)

