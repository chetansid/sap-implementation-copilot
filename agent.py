from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, List, Annotated
from tools import (
    search_documents,
    generate_technical_design,
    generate_basis_script,
    analyze_sap_log,
    summarize_notes
)
from dotenv import load_dotenv
import json

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class AgentState(TypedDict):
    messages: List
    question: str
    intent: str
    context: str
    answer: str


def detect_intent(state: AgentState) -> AgentState:
    """Decide which tool to use based on the question."""
    question = state["question"]

    prompt = f"""
    Classify this SAP consultant question into exactly one category:
    
    - SEARCH: searching for information in uploaded documents
    - TECHNICAL_DESIGN: generating technical design from a RICEFW spec
    - BASIS_SCRIPT: generating BASIS admin scripts or procedures
    - LOG_ANALYSIS: analyzing SAP system logs
    - SUMMARIZE: summarizing implementation notes or finding open items
    - GENERAL: general SAP question not requiring document search

    Question: {question}

    Respond with ONLY the category name, nothing else.
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    intent = response.content.strip().upper()

    valid_intents = ["SEARCH", "TECHNICAL_DESIGN", "BASIS_SCRIPT", "LOG_ANALYSIS", "SUMMARIZE", "GENERAL"]
    if intent not in valid_intents:
        intent = "SEARCH"

    return {**state, "intent": intent}


def execute_tool(state: AgentState) -> AgentState:
    """Execute the appropriate tool based on intent."""
    intent = state["intent"]
    question = state["question"]
    context = ""

    if intent == "SEARCH":
        context = search_documents(question)

    elif intent == "TECHNICAL_DESIGN":
        spec = search_documents(question, doc_type="ricefw")
        if spec == "No relevant documents found.":
            context = "No RICEFW specs found. Please upload a functional specification first."
        else:
            context = generate_technical_design(spec)

    elif intent == "BASIS_SCRIPT":
        context = generate_basis_script(question)

    elif intent == "LOG_ANALYSIS":
        # Extract log content from question
        context = analyze_sap_log(question)

    elif intent == "SUMMARIZE":
        context = summarize_notes(question)

    elif intent == "GENERAL":
        context = "Answering from general SAP knowledge."

    return {**state, "context": context}


def generate_answer(state: AgentState) -> AgentState:
    """Generate final answer based on context."""
    intent = state["intent"]
    question = state["question"]
    context = state["context"]
    messages = state["messages"]

    # For generated artifacts return directly
    if intent in ["TECHNICAL_DESIGN", "BASIS_SCRIPT", "LOG_ANALYSIS", "SUMMARIZE"]:
        return {**state, "answer": context}

    # For search and general — use LLM to formulate answer
    system = """You are an expert SAP implementation copilot assisting EY consultants.
    You help with RICEFW development, implementation notes, BASIS administration, and S/4HANA implementations.
    Be precise, practical, and reference specific SAP transaction codes where relevant."""

    prompt_messages = [SystemMessage(content=system)]
    prompt_messages.extend(messages[-4:])  # last 2 exchanges for context

    if context and context != "Answering from general SAP knowledge.":
        prompt_messages.append(HumanMessage(
            content=f"Context from documents:\n{context}\n\nQuestion: {question}"
        ))
    else:
        prompt_messages.append(HumanMessage(content=question))

    response = llm.invoke(prompt_messages)
    return {**state, "answer": response.content}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("detect_intent", detect_intent)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("generate_answer", generate_answer)

    graph.set_entry_point("detect_intent")
    graph.add_edge("detect_intent", "execute_tool")
    graph.add_edge("execute_tool", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


agent = build_graph()


def run_agent(question: str, history: list = []) -> str:
    state = {
        "messages": history,
        "question": question,
        "intent": "",
        "context": "",
        "answer": ""
    }
    result = agent.invoke(state)
    return result["answer"]