import importlib.metadata

from data_manipulation import hello
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.main import api_router

BACKEND_VERSION = importlib.metadata.version("datakern-backend")

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:4201"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.get("/", tags=["Health"])
def read_root():
    return {"Hello": hello()}


@app.get("/version", tags=["Health"])
def read_version():
    return {"version": BACKEND_VERSION}
