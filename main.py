from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional
from ingest import ingest_file, list_ingested_files
from agent import run_agent
from fastapi.responses import StreamingResponse
import asyncio
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

@app.post("/ask-stream")
async def ask_stream(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    async def generate():
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage
            from tools import search_documents, generate_basis_script, analyze_sap_log, summarize_notes
            from agent import detect_intent, execute_tool

            # Detect intent first
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

            intent_prompt = f"""Classify this question into one category:
            SEARCH, TECHNICAL_DESIGN, BASIS_SCRIPT, LOG_ANALYSIS, SUMMARIZE, GENERAL
            Question: {request.question}
            Respond with ONLY the category name."""

            yield ": connected\n\n"
            
            intent_response = llm.invoke([HumanMessage(content=intent_prompt)])
            intent = intent_response.content.strip().upper()

            # Send intent tag first
            yield f"data: [INTENT:{intent}]\n\n"

            # Get context
            context = ""
            if intent == "SEARCH":
                context = search_documents(request.question)
            elif intent == "BASIS_SCRIPT":
                context = f"Generate BASIS script for: {request.question}"
            elif intent == "SUMMARIZE":
                context = summarize_notes(request.question)
            elif intent == "LOG_ANALYSIS":
                context = f"Analyze this log: {request.question}"

            # Stream the response
            system = """You are an expert SAP implementation copilot for EY consultants.
            Be precise, practical, and reference specific SAP transaction codes.
            Format your response clearly with numbered steps or sections where appropriate."""

            messages = [SystemMessage(content=system)]

            if context and context != "No relevant documents found.":
                messages.append(HumanMessage(
                    content=f"Context:\n{context}\n\nQuestion: {request.question}"
                ))
            else:
                messages.append(HumanMessage(content=request.question))

            streaming_llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                streaming=True
            )

            async for chunk in streaming_llm.astream(messages):
                if chunk.content:
                    yield f"data: {chunk.content}\n\n"
                    await asyncio.sleep(0)

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/upload-template")
async def upload_template(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    file_path = f"uploads/template_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract text from template
    from langchain_community.document_loaders import PyPDFLoader
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    template_text = "\n".join([d.page_content for d in docs[:3]])

    # Store template text
    with open("uploads/active_template.txt", "w") as f:
        f.write(template_text)

    return {"message": f"Template uploaded: {file.filename}"}


@app.post("/ask-with-template")
def ask_with_template(request: QuestionRequest):
    template_content = None
    template_path = "uploads/active_template.txt"

    if os.path.exists(template_path):
        with open(template_path, "r") as f:
            template_content = f.read()

    from tools import search_documents, generate_technical_design
    spec = search_documents(request.question, doc_type="ricefw")

    if spec == "No relevant documents found.":
        return {"answer": "No RICEFW specs found. Upload a functional spec first."}

    design = generate_technical_design(spec, template_content)
    return {"answer": design}

app.mount("/static", StaticFiles(directory="static"), name="static")