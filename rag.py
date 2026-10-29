import warnings
warnings.filterwarnings("ignore")

import os
from typing import TypedDict
from dotenv import load_dotenv

# LangChain Libraries
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun

# LangGraph Libraries
from langgraph.graph import StateGraph, START, END

# Load environment variables
load_dotenv()
os.environ.pop("GEMINI_API_KEY", None)

# ==========================================
# 1) INDEXING: Document / Data Preparation
# ==========================================
# Sample corpus for indexing (can be replaced with any text source or document loader)
raw_text = """
Retrieval-Augmented Generation (RAG) is an architectural pattern that enhances Large Language Models (LLMs)
by grounding their responses in external, authoritative knowledge bases.

In a standard RAG pipeline, the workflow consists of multiple stages:
1. Indexing & Ingestion: Unstructured data (such as articles, documents, or transcripts) is collected and prepared.
2. Text Splitting / Chunking: The raw text is divided into smaller, manageable chunks using techniques like 
   Recursive Character Text Splitting. Chunking preserves semantic context while respecting token limits.
3. Embedding Generation: Each text chunk is converted into high-dimensional numerical vectors using an embedding model 
   such as Google Generative AI Embeddings.
4. Vector Store: Embeddings and their corresponding text chunks are stored and indexed in a vector database such as FAISS 
   (Facebook AI Similarity Search) to enable lightning-fast similarity searching.
5. Retrieval: When a user poses a question, the vector store retrieves the top-k most semantically relevant chunks.
6. Context Assembly: The retrieved document chunks are joined together to form a coherent context string.
7. Generation via LLM: The context and user query are injected into a structured PromptTemplate, which is then fed into 
   an LLM (like Google's Gemini 2.5 Flash) to generate accurate, context-grounded answers.
8. Orchestration via LangGraph: Modern agentic pipelines use LangGraph to orchestrate stateful nodes (retrieve, generate) 
   with fine-grained control over execution flow, conditional routing, and iterative reflection.
"""

print("[1/5] Indexing text data...")

# ==========================================
# 2) TEXT SPLITTING: Recursive Chunking
# ==========================================
print("[2/5] Splitting text into chunks using RecursiveCharacterTextSplitter...")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""]
)
chunks = splitter.split_text(raw_text)
print(f"       Generated {len(chunks)} text chunks.")

# ==========================================
# 3) EMBEDDINGS & VECTOR STORE (FAISS)
# ==========================================
print("[3/5] Generating embeddings and building FAISS vector store...")
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
vector_store = FAISS.from_texts(chunks, embeddings)
print("       FAISS vector store ready.")

# ==========================================
# 4) RETRIEVER & DOCUMENT JOINING
# ==========================================
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}
)

def format_docs(docs):
    """Joins retrieved document chunks into a single string."""
    return "\n\n".join(doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in docs)

# DuckDuckGo Search Tool Setup
web_search_tool = DuckDuckGoSearchRun()

# LLM & Prompt Setup
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.2
)

prompt = PromptTemplate(
    template="""You are a knowledgeable and helpful AI assistant.
Answer the question based on the provided context below.
Provide a clear, well-structured, and concise explanation.

Context:
{context}

Question:
{question}

Answer:""",
    input_variables=["context", "question"]
)

# Document Relevance Grader (Checks if retrieved docs contain the answer)
grader_prompt = PromptTemplate(
    template="""You are a strict evaluator assessing whether the retrieved context contains relevant information to answer the question.

Context:
{context}

Question:
{question}

Does the context provide relevant information to answer the question?
Reply with ONLY 'yes' or 'no'.""",
    input_variables=["context", "question"]
)
doc_grader = grader_prompt | llm | StrOutputParser()
generation_chain = prompt | llm | StrOutputParser()

# ==========================================
# 5) LANGGRAPH STATE & WORKFLOW
# ==========================================
# Define state schema
class RAGState(TypedDict):
    question: str
    context: str
    answer: str
    source: str

# Define Graph Nodes
def retrieve(state: RAGState) -> dict:
    """Retrieve node: queries vector store and updates context."""
    print("  -> [LangGraph Node: retrieve] Searching vector store...")
    docs = retriever.invoke(state["question"])
    return {
        "context": format_docs(docs),
        "source": "Local Vector Store (FAISS)"
    }

def web_search(state: RAGState) -> dict:
    """Web search node: queries DuckDuckGo when vector store is insufficient."""
    question = state["question"]
    print(f"  -> [LangGraph Node: web_search] Querying DuckDuckGo for: '{question}'...")
    search_results = web_search_tool.invoke(question)
    
    # If conversational sentence returns empty snippet, refine query keywords
    if not search_results or "No good DuckDuckGo Search Result was found" in search_results:
        stopwords = {"who", "what", "where", "when", "why", "how", "is", "are", "was", "were", "the", "a", "an", "and", "or", "in", "on", "of", "to", "for"}
        refined = " ".join([w for w in question.replace("?", "").replace("'", "").replace('"', '').split() if w.lower() not in stopwords])
        print(f"     Refining query for search engine: '{refined}'...")
        search_results = web_search_tool.invoke(refined)

    return {
        "context": search_results,
        "source": "DuckDuckGo Web Search"
    }

def decide_to_generate(state: RAGState) -> str:
    """Conditional Edge: evaluates if local context is sufficient or if web search is needed."""
    print("  -> [LangGraph Router: evaluate] Checking if local context is relevant...")
    grade = doc_grader.invoke({
        "context": state["context"],
        "question": state["question"]
    }).strip().lower()
    
    if "yes" in grade:
        print("     [Decision] Context is relevant. Proceeding directly to generate.")
        return "generate"
    else:
        print("     [Decision] Context is insufficient. Routing to DuckDuckGo search...")
        return "web_search"

def generate(state: RAGState) -> dict:
    """Generate node: synthesizes answer using context and question."""
    print(f"  -> [LangGraph Node: generate] Synthesizing answer using {state.get('source', 'context')}...")
    answer = generation_chain.invoke({
        "context": state["context"],
        "question": state["question"]
    })
    return {"answer": answer}

# Build StateGraph
workflow = StateGraph(RAGState)

# Add nodes to graph
workflow.add_node("retrieve", retrieve)
workflow.add_node("web_search", web_search)
workflow.add_node("generate", generate)

# Define edges: START -> retrieve -> [conditional] -> generate / web_search -> generate -> END
workflow.add_edge(START, "retrieve")
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

# Compile graph
rag_app = workflow.compile()
print("[4/5] LangGraph workflow compiled successfully.")

# ==========================================
# 6) TEST LANGGRAPH & PRINT OUTPUT
# ==========================================
def run_query(query: str):
    print("\n" + "="*60)
    print(f"User Query: {query}")
    print("="*60)
    initial_state: RAGState = {
        "question": query,
        "context": "",
        "answer": "",
        "source": ""
    }
    result = rag_app.invoke(initial_state)
    print(f"\nSource Used: {result.get('source')}")
    print("\nFinal Answer:")
    print(result["answer"])
    print("="*60)

if __name__ == "__main__":
    print("\n[5/5] Testing LangGraph RAG App with DuckDuckGo fallback...\n")
    
    # Test 1: Question answered in local document -> Uses Local FAISS Vector Store
    run_query("What are the stages of a RAG pipeline and why is FAISS used?")
    
    # Test 2: Question outside local document -> Triggers DuckDuckGo Search Tool
    run_query("Who won the 2024 ICC Men's T20 World Cup and who was the runner-up?")
