from fastapi import FastAPI

app = FastAPI(title="SAP Implementation Copilot")

@app.get("/")
def root():
    return {"message": "SAP Implementation Copilot is running"}