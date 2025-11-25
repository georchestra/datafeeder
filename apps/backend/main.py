from fastapi import FastAPI
from data_manipulation import hello

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": hello()}
