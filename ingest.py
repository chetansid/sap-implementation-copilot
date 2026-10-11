from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
import os
import glob

load_dotenv()

CHROMA_DIR = "chroma_db"

def ingest_file(file_path: str, doc_type: str) -> int:
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Tag each chunk with document type and source
    for doc in documents:
        doc.metadata["doc_type"] = doc_type
        doc.metadata["source_file"] = os.path.basename(file_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )
    vectorstore.add_documents(chunks)

    return len(chunks)


def get_vectorstore():
    embeddings = OpenAIEmbeddings()
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )


def list_ingested_files() -> list:
    vectorstore = get_vectorstore()
    collection = vectorstore._collection
    results = collection.get(include=["metadatas"])
    files = {}
    for meta in results["metadatas"]:
        fname = meta.get("source_file", "unknown")
        dtype = meta.get("doc_type", "unknown")
        files[fname] = dtype
    return [{"file": k, "type": v} for k, v in files.items()]