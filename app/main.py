
from fastapi import FastAPI

from app.api.routes.health import router as health_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Keitaro Campaign Manager",
        description="Campaign management application",
        version="0.1.0",
    )

    application.include_router(
        health_router,
        prefix="/api",
    )

    return application


app = create_app()
