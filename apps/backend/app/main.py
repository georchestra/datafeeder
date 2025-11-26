import importlib.metadata

from data_manipulation import hello
from fastapi import FastAPI

BACKEND_VERSION = importlib.metadata.version("datakern-backend")

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": hello()}


@app.get("/version")
def read_version():
    return {"version": BACKEND_VERSION}
