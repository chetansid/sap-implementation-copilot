from database import init_db
from memory import save_message, get_history, save_project_context, get_project_context, clear_history, get_session_summary
import uuid
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

# Initialize database tables on startup
init_db()

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

class ProjectContextRequest(BaseModel):
    session_id: str
    project_name: str
    client_name: str
    notes: str = ""


@app.post("/ask")
def ask(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    session_id = request.history[0].get("session_id", str(uuid.uuid4())) \
        if request.history else str(uuid.uuid4())

    try:
        # Get history from PostgreSQL
        history = get_history(session_id)

        # Get project context
        project_ctx = get_project_context(session_id)
        context_prefix = ""
        if project_ctx:
            context_prefix = f"Project: {project_ctx.get('project_name', '')} | Client: {project_ctx.get('client_name', '')}\n"

        # Run agent with history
        full_question = context_prefix + request.question if context_prefix else request.question
        answer = run_agent(full_question, history)

        # Save to PostgreSQL
        save_message(session_id, "user", request.question)
        save_message(session_id, "assistant", answer)

        return {
            "question": request.question,
            "answer": answer,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask-stream")
async def ask_stream(request: QuestionRequest):
    session_id = request.history[0].get("session_id") \
        if request.history else str(uuid.uuid4())

    async def generate():
        try:
            import asyncio
            from agent import run_agent

            # Get persistent history
            history = get_history(session_id)

            # Get project context
            project_ctx = get_project_context(session_id)
            context_prefix = ""
            if project_ctx:
                context_prefix = f"Project context — Project: {project_ctx.get('project_name', '')} | Client: {project_ctx.get('client_name', '')}\n"

            full_question = context_prefix + request.question if context_prefix else request.question

            # Send session ID first
            yield f"data: [SESSION:{session_id}]\n\n"

            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None,
                lambda: run_agent(full_question, history)
            )

            # Save to PostgreSQL
            save_message(session_id, "user", request.question)
            save_message(session_id, "assistant", answer)
            print(f"✅ Saved messages for session: {session_id}")

            # Stream word by word
            words = answer.split(' ')
            for i, word in enumerate(words):
                yield f"data: {word} \n\n"
                await asyncio.sleep(0.02)

            yield "data: [DONE]\n\n"

        except Exception as e:
            print(f"❌ Streaming error: {str(e)}")  # ADD THIS
            yield f"data: Error: {str(e)}\n\n"
            traceback.print_exc() 
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.post("/session/context")
def set_project_context(request: ProjectContextRequest):
    save_project_context(
        request.session_id,
        request.project_name,
        request.client_name,
        request.notes
    )
    return {"message": "Project context saved"}


@app.get("/session/{session_id}/history")
def get_session_history(session_id: str):
    history = get_history(session_id, limit=50)
    summary = get_session_summary(session_id)
    return {"session_id": session_id, "history": history, "summary": summary}


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    clear_history(session_id)
    return {"message": f"Session {session_id} cleared"}


@app.get("/session/new")
def new_session():
    return {"session_id": str(uuid.uuid4())}