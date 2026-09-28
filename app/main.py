from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.game import router as game_router
from app.core.config import settings

base_dir = Path(__file__).resolve().parent

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

templates = Jinja2Templates(directory=str(base_dir / "templates"))

app.include_router(game_router)


@app.get("/", response_class=HTMLResponse)
def index_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "freeling_active": settings.is_freeling_available(),
        },
    )

