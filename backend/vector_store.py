import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from backend.embeddings import embeddings, safe_str

# Document registry starts completely empty
indexed_documents: list[dict] = []

def create_empty_vector_store():
    # 384 is the native embedding dimension for BAAI/bge-small-en-v1.5
    index = faiss.IndexFlatL2(384)
    return FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={}
    )

vector_store = create_empty_vector_store()
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})

def clear_vector_store():
    global vector_store, retriever, indexed_documents
    vector_store = create_empty_vector_store()
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    indexed_documents.clear()

def format_docs(docs):
    return "\n\n".join(safe_str(getattr(doc, "page_content", doc)) for doc in docs)

