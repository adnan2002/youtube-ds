from fastapi import FastAPI


app = FastAPI(title="YouTube DS Backend")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello from FastAPI backend"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)

