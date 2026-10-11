from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ingest import get_vectorstore
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def search_documents(query: str, doc_type: str = None) -> str:
    """Search across uploaded documents."""
    vectorstore = get_vectorstore()

    if doc_type:
        results = vectorstore.similarity_search(
            query, k=5,
            filter={"doc_type": doc_type}
        )
    else:
        results = vectorstore.similarity_search(query, k=5)

    if not results:
        return "No relevant documents found."

    context = "\n\n".join([
        f"[{doc.metadata.get('source_file', 'unknown')} — page {doc.metadata.get('page', '?') + 1}]\n{doc.page_content}"
        for doc in results
    ])
    return context


def generate_technical_design(spec_content: str) -> str:
    """Generate technical design from RICEFW functional spec."""
    prompt = ChatPromptTemplate.from_template("""
    You are a senior SAP technical architect. Based on the functional specification below,
    generate a detailed technical design document.

    Include:
    1. Technical approach and solution overview
    2. Data mappings (source → target fields)
    3. Function modules or BAPIs to be used
    4. Error handling approach
    5. ABAP pseudocode for the main logic
    6. Transport and testing considerations

    Functional Specification:
    {spec}

    Technical Design:
    """)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"spec": spec_content})


def generate_basis_script(requirement: str) -> str:
    """Generate BASIS admin scripts from a plain English requirement."""
    prompt = ChatPromptTemplate.from_template("""
    You are an expert SAP BASIS administrator with 15 years of experience.
    Generate a practical SAP BASIS script or step-by-step procedure for the following requirement.

    Include:
    1. Transaction codes to use
    2. Step by step procedure
    3. ABAP report or script if applicable
    4. What to check before and after
    5. Common pitfalls to avoid

    Requirement: {requirement}

    BASIS Script/Procedure:
    """)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"requirement": requirement})


def analyze_sap_log(log_content: str) -> str:
    """Analyze SAP system logs and suggest optimizations."""
    prompt = ChatPromptTemplate.from_template("""
    You are an expert SAP BASIS administrator. Analyze the SAP system log below.

    Provide:
    1. Summary of what the log shows
    2. Critical issues identified (if any)
    3. Performance bottlenecks or warnings
    4. Root cause analysis for any errors
    5. Specific optimization recommendations
    6. Suggested next steps with transaction codes

    SAP Log:
    {log}

    Analysis:
    """)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"log": log_content})


def summarize_notes(query: str) -> str:
    """Summarize implementation notes and extract open items."""
    context = search_documents(query, doc_type="note")

    if context == "No relevant documents found.":
        return "No implementation notes found. Please upload notes first."

    prompt = ChatPromptTemplate.from_template("""
    You are an SAP implementation consultant. Based on the implementation notes below,
    provide a structured summary for the query: "{query}"

    Include:
    1. Key decisions made
    2. Open items and pending actions
    3. Dependencies identified
    4. Risks or issues flagged
    5. Next steps

    Notes:
    {context}

    Summary:
    """)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"query": query, "context": context})