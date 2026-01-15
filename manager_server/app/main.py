import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import alarms, config, users, routes, devices

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Alarm Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alarms.router)
app.include_router(config.router)
app.include_router(users.router)
app.include_router(routes.router)
app.include_router(devices.router)


@app.get("/health")
def health():
    return {"status": "ok"}
