from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path

router = APIRouter(prefix="/docs-help", tags=["documentation"])

# Create templates directory if it doesn't exist
templates_dir = Path(__file__).parents[2] / "templates"
os.makedirs(templates_dir, exist_ok=True)

# Create Jinja2 templates
templates = Jinja2Templates(directory=str(templates_dir))

@router.get("/", response_class=HTMLResponse)
async def docs_overview(request: Request):
    """
    Render a documentation overview page.
    """
    return templates.TemplateResponse(
        "api_docs.html",
        {"request": request, "title": "Beauty Salon Booking API - Documentation"}
    )

@router.get("/webhooks", response_class=HTMLResponse)
async def webhooks_docs(request: Request):
    """
    Render webhooks documentation page.
    """
    return templates.TemplateResponse(
        "webhooks_docs.html",
        {"request": request, "title": "Webhooks Documentation"}
    )

@router.get("/integration", response_class=HTMLResponse)
async def integration_docs(request: Request):
    """
    Render integration documentation page.
    """
    return templates.TemplateResponse(
        "integration_docs.html",
        {"request": request, "title": "Integration Guide"}
    )