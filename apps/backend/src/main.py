import importlib.metadata
import os

from data_manipulation import hello
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from src.api.main import api_router
from geonetwork import GnApi
from src.core.georchestraconfig import GeorchestraConfig

DEBUG=False
if os.getenv("DEBUG"):
    value=os.getenv("DEBUG")
    if "false" == value.lower():
        DEBUG=False
    elif "true" == value.lower():
        DEBUG=True

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

# Load georchestra properties and merge with settings
geor_config = GeorchestraConfig()

@app.get("/", tags=["Health"])
def read_root():
    return {"Hello": hello()}


@app.get("/version", tags=["Health"])
def read_version():
    return {"version": BACKEND_VERSION}

@app.get("/geonetwork", tags=["Health"])
def read_geonetwork():
    gnapi = GnApi(api_url="http://gateway:8080/geonetwork/srv/api", credentials=None, verifytls=False)
    return {"Hello": gnapi._get_version().json()}

if DEBUG:
    @app.get("/config", tags=["Health"], response_class=HTMLResponse)
    def read_config():
        print(geor_config.get("domainname","default"))
        return geor_config.tostr()
