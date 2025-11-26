from data_manipulation import hello
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": hello()}
