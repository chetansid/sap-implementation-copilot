from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional
from ingest import ingest_file, list_ingested_files
from agent import run_agent
import os
import shutil
from dotenv import load_dotenv

load_dotenv(override=False)

app = FastAPI(title="SAP Implementation Copilot")

os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)


class QuestionRequest(BaseModel):
    question: str
    history: list = []


class LogRequest(BaseModel):
    log_content: str


@app.get("/")
def root():
    return {"message": "SAP Implementation Copilot is running"}


@app.post("/ask")
def ask(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        answer = run_agent(request.question, request.history)
        return {"question": request.question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "note"
):
    valid_types = ["ricefw", "note", "log", "design"]
    if doc_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"doc_type must be one of: {valid_types}"
        )

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    chunks = ingest_file(file_path, doc_type)

    return {
        "message": f"Successfully ingested {file.filename}",
        "doc_type": doc_type,
        "chunks_created": chunks
    }


@app.post("/analyze-log")
def analyze_log(request: LogRequest):
    if not request.log_content.strip():
        raise HTTPException(status_code=400, detail="Log content cannot be empty")
    try:
        answer = run_agent(
            f"Analyze this SAP system log:\n\n{request.log_content}",
            []
        )
        return {"analysis": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
def get_documents():
    try:
        files = list_ingested_files()
        return {"documents": files, "total": len(files)}
    except Exception as e:
        return {"documents": [], "total": 0}


@app.get("/ui")
def ui(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")