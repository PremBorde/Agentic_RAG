import json as _json
from typing import AsyncGenerator

from backend.config import get_llm
from backend.embeddings import safe_str
from backend.vector_store import vector_store, retriever, format_docs
from backend.tools import is_conversational_query, is_explicit_web_search, is_followup_query, web_search_tool
from backend.prompts import conv_prompt, gen_prompt
from backend.memory import get_thread_context_str, get_last_user_query, record_thread_turn

async def stream_chat_events(
    question: str, 
    model_name: str, 
    thread_id: str
) -> AsyncGenerator[str, None]:
    """Generates Server-Sent Events (SSE) for streaming chat responses."""
    chat_hist = get_thread_context_str(thread_id)
    doc_count = len(vector_store.index_to_docstore_id)
    source = "Unknown"
    docs_meta = []
    context = ""
    answer_parts: list[str] = []

    try:
        yield 'data: {"type":"stage","stage":"thinking"}\n\n'
        llm = get_llm(model_name)

        # ── ROUTE ────────────────────────────────────────────────────
        # 1. Greetings, small talk & assistant capabilities (e.g. "Hello! What can you do?")
        if is_conversational_query(question):
            source = "Assistant"
            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'
            prompt_val = conv_prompt.invoke({"chat_history": chat_hist, "question": question})
            async for chunk in llm.astream(prompt_val):
                token = safe_str(chunk.content)
                if token:
                    answer_parts.append(token)
                    yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # 2. User asked about documents, but none are indexed yet
        elif doc_count == 0 and any(
            k in question.lower().split()
            for k in ["document", "file", "pdf", "transcript", "notes", "uploaded", "article", "doc", "docs"]
        ):
            source = "System Guidance"
            msg = ("You haven't uploaded or indexed any documents yet.\n\n"
                   "Please click '+ Add Docs' or the paperclip button to upload a PDF, "
                   "text file, or YouTube transcript.")
            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'
            yield f"data: {_json.dumps({'type':'token','text':msg})}\n\n"
            answer_parts.append(msg)

        # 3. Explicit Web Search requested by user (e.g. "search the web for...")
        elif is_explicit_web_search(question):
            yield 'data: {"type":"stage","stage":"searching"}\n\n'
            print(f"  -> [Web Search] Executing live web query for: {question}")
            try:
                context = web_search_tool.invoke(question)
                source = "Web Search"
                docs_meta = [{
                    "content": context,
                    "source": "Web Search",
                    "doc_id": "web-search"
                }]
            except Exception:
                context = "No search results available."
                source = "Web Search"

            yield f"data: {_json.dumps({'type':'meta','source':source,'retrieved_docs':docs_meta})}\n\n"
            yield 'data: {"type":"stage","stage":"generating"}\n\n'

            prompt_val = gen_prompt.invoke({
                "chat_history": chat_hist,
                "context": context,
                "question": question
            })
            try:
                async for chunk in llm.astream(prompt_val):
                    token = safe_str(chunk.content)
                    if token:
                        answer_parts.append(token)
                        yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"
            except Exception as stream_err:
                err_text = str(stream_err)
                if ("429" in err_text or "RESOURCE_EXHAUSTED" in err_text) and context:
                    fallback_msg = (
                        "### 🌐 Live Web Search Results\n\n"
                        f"{context}\n\n"
                        "> *Note: Live web results were retrieved via Web Search. Full LLM synthesis was skipped because Google Gemini free-tier quota was reached for this minute.*"
                    )
                    answer_parts.append(fallback_msg)
                    yield f"data: {_json.dumps({'type':'token','text':fallback_msg})}\n\n"
                else:
                    raise stream_err

        # 4. Local Vector Store (FAISS) RAG - Documents are indexed!
        elif doc_count > 0:
            yield 'data: {"type":"stage","stage":"searching"}\n\n'
            last_q = get_last_user_query(thread_id)
            if last_q and is_followup_query(question):
                search_query = f"{last_q} {question}".strip()
            else:
                search_query = question

            print(f"  -> [Document Search] Querying FAISS vector index for: {search_query}")
            docs = retriever.invoke(search_query)
            if not docs and last_q:
                docs = retriever.invoke(last_q)

            docs_meta = [
                {"content": safe_str(d.page_content),
                 "source":  d.metadata.get("source", "Indexed Document"),
                 "doc_id":  d.metadata.get("doc_id", "unknown")}
                for d in docs
            ]
            context = format_docs(docs)
            source = "Document Search"

            yield f"data: {_json.dumps({'type':'meta','source':source,'retrieved_docs':docs_meta})}\n\n"
            yield 'data: {"type":"stage","stage":"generating"}\n\n'

            prompt_val = gen_prompt.invoke({
                "chat_history": chat_hist,
                "context": context,
                "question": question
            })
            async for chunk in llm.astream(prompt_val):
                token = safe_str(chunk.content)
                if token:
                    answer_parts.append(token)
                    yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # 5. General Assistant / Conversational / Coding / QA when zero documents are indexed
        else:
            source = "Assistant"
            yield f'data: {_json.dumps({"type":"meta","source":source,"retrieved_docs":[]})}\n\n'
            yield 'data: {"type":"stage","stage":"generating"}\n\n'
            prompt_val = conv_prompt.invoke({
                "chat_history": chat_hist,
                "question": question
            })
            async for chunk in llm.astream(prompt_val):
                token = safe_str(chunk.content)
                if token:
                    answer_parts.append(token)
                    yield f"data: {_json.dumps({'type':'token','text':token})}\n\n"

        # ── DONE ─────────────────────────────────────────────────────
        yield 'data: {"type":"stage","stage":"success"}\n\n'
        yield 'data: {"type":"done"}\n\n'

        full_answer = "".join(safe_str(p) for p in answer_parts)
        if thread_id:
            record_thread_turn(thread_id, "user", question)
            record_thread_turn(thread_id, "assistant", full_answer)

    except Exception as exc:
        err = str(exc)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            msg = ("Google Gemini Free Tier quota reached. "
                   "Please select a different model in the dropdown.")
        else:
            msg = f"Error: {err}"
        yield 'data: {"type":"stage","stage":"error"}\n\n'
        yield f"data: {_json.dumps({'type':'error','text':msg})}\n\n"
