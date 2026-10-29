from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.output_parsers import StrOutputParser

from backend.config import get_llm
from backend.embeddings import safe_str
from backend.vector_store import vector_store, retriever, format_docs
from backend.tools import web_search_tool, is_conversational_query, is_explicit_web_search
from backend.prompts import gen_prompt, conv_prompt, grader_prompt

class RAGState(TypedDict):
    question: str
    context: str
    answer: str
    source: str
    docs_metadata: list
    model_name: Optional[str]
    thread_id: Optional[str]
    chat_history: Optional[str]

def conversation_node(state: RAGState) -> dict:
    """Handles greetings and small talk conversationally without searching external tools."""
    model_name = state.get("model_name") or "gemini-2.5-flash"
    chat_hist = state.get("chat_history") or "No prior conversational context."
    try:
        llm_inst = get_llm(model_name)
        chain = conv_prompt | llm_inst | StrOutputParser()
        reply = chain.invoke({"chat_history": chat_hist, "question": state["question"]})
    except Exception as e:
        print(f"  [Conversation model {model_name} failed: {e}] Falling back to gemini-2.5-flash")
        fallback_llm = get_llm("gemini-2.5-flash")
        reply = (conv_prompt | fallback_llm | StrOutputParser()).invoke({"chat_history": chat_hist, "question": state["question"]})

    return {
        "answer": reply.strip(),
        "source": "Assistant",
        "context": "",
        "docs_metadata": []
    }

def no_docs_node(state: RAGState) -> dict:
    """Informs the user when they ask about documents but none are indexed yet."""
    return {
        "answer": "You haven't uploaded or indexed any documents yet.\n\nPlease click '+ Add Docs' or the paperclip button in the chatbox below to upload a PDF, text file, or YouTube video transcript for private RAG retrieval.",
        "source": "System Guidance",
        "context": "",
        "docs_metadata": []
    }

def retrieve_node(state: RAGState) -> dict:
    docs = retriever.invoke(state["question"])
    doc_items = [
        {
            "content": safe_str(d.page_content),
            "source": d.metadata.get("source", "Indexed Document"),
            "doc_id": d.metadata.get("doc_id", "unknown")
        }
        for d in docs
    ]
    return {
        "context": format_docs(docs),
        "source": "Document Search",
        "docs_metadata": doc_items
    }

def web_search_node(state: RAGState) -> dict:
    question = state["question"]
    search_results = ""
    try:
        search_results = web_search_tool.invoke(question)
        if not search_results or "No good DuckDuckGo Search Result was found" in search_results:
            stopwords = {"who", "what", "where", "when", "why", "how", "is", "are", "was", "were", "the", "a", "an", "and", "or", "in", "on", "of", "to", "for"}
            refined = " ".join([w for w in question.replace("?", "").replace("'", "").replace('"', '').split() if w.lower() not in stopwords])
            if refined.strip():
                search_results = web_search_tool.invoke(refined)
    except Exception as e:
        print(f"  [DuckDuckGo warning: {e}]")
        search_results = "No search results available (Network offline or rate limited)."

    doc_items = [
        {
            "content": search_results,
            "source": "Web Search",
            "doc_id": "web-search"
        }
    ]
    return {
        "context": search_results,
        "source": "Web Search",
        "docs_metadata": doc_items
    }

def generate_node(state: RAGState) -> dict:
    model_name = state.get("model_name") or "gemini-2.5-flash"
    chat_hist = state.get("chat_history") or "No prior conversational context."
    try:
        llm_inst = get_llm(model_name)
        chain = gen_prompt | llm_inst | StrOutputParser()
        answer = chain.invoke({
            "chat_history": chat_hist,
            "context": state["context"],
            "question": state["question"]
        })
    except Exception as e:
        print(f"  [Generation model {model_name} failed: {e}] Falling back to gemini-2.5-flash")
        fallback_llm = get_llm("gemini-2.5-flash")
        fallback_chain = gen_prompt | fallback_llm | StrOutputParser()
        answer = fallback_chain.invoke({
            "chat_history": chat_hist,
            "context": state["context"],
            "question": state["question"]
        })
    return {"answer": answer}

# Router from START: decides whether to converse, query local RAG, or search the web
def route_start(state: RAGState) -> str:
    question = state["question"].strip()
    doc_count = len(vector_store.index_to_docstore_id)
    
    # 1. Check for conversational greetings / pleasantries
    if is_conversational_query(question):
        print("  -> [LangGraph Router] Detected greeting. Routing to conversation_node.")
        return "conversation"
        
    # 2. Check for explicit web search requests
    if is_explicit_web_search(question):
        print("  -> [LangGraph Router] User requested explicit web search. Routing to web_search.")
        return "web_search"

    # 3. If documents are loaded, query the vector store
    if doc_count > 0:
        print("  -> [LangGraph Router] Documents exist in vector store. Routing to retrieve.")
        return "retrieve"
        
    # 4. If no documents exist and user asks about 'document' or 'file'
    doc_keywords = ["document", "file", "pdf", "transcript", "notes", "uploaded", "article", "doc"]
    if any(k in question.lower().split() for k in doc_keywords):
        print("  -> [LangGraph Router] User asked about documents but none are indexed. Routing to no_docs.")
        return "no_docs"
        
    # 5. Otherwise, general coding, reasoning or conversation -> direct conversation/assistant
    print("  -> [LangGraph Router] General query. Routing to conversation.")
    return "conversation"

# Router after retrieve: ensures local documents are used for answers
def decide_to_generate(state: RAGState) -> str:
    question = state.get("question", "")
    if is_explicit_web_search(question):
        return "web_search"
    doc_count = len(vector_store.index_to_docstore_id)
    if doc_count > 0:
        return "generate"
    context = state.get("context", "").strip()
    if not context:
        return "web_search"
    return "generate"

# Build StateGraph
workflow = StateGraph(RAGState)
workflow.add_node("conversation", conversation_node)
workflow.add_node("no_docs", no_docs_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("generate", generate_node)

workflow.add_conditional_edges(
    START,
    route_start,
    {
        "conversation": "conversation",
        "no_docs": "no_docs",
        "retrieve": "retrieve",
        "web_search": "web_search"
    }
)

workflow.add_edge("conversation", END)
workflow.add_edge("no_docs", END)

workflow.add_conditional_edges(
    "retrieve",
    decide_to_generate,
    {
        "generate": "generate",
        "web_search": "web_search"
    }
)
workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", END)

rag_app = workflow.compile()

