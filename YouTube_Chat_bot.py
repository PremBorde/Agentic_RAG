import warnings
warnings.filterwarnings("ignore")

import os
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate


from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser


load_dotenv()
os.environ.pop("GEMINI_API_KEY", None)

## 1) INDEXING 

video_id = "b2tjnxX8IHU"  # only the ID, not full URL

try:
    ytt = YouTubeTranscriptApi()
    # v1.0+ uses ytt.fetch(), older versions use get_transcript
    if hasattr(ytt, "fetch"):
        transcript_data = ytt.fetch(video_id, languages=["en"])
        transcript = " ".join(
            chunk.text if hasattr(chunk, "text") else chunk["text"]
            for chunk in transcript_data
        )
    else:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=["hi", "en"])
        transcript = " ".join(chunk["text"] for chunk in transcript_data)

    #print("Transcript loaded successfully!\n")
    # print(transcript)

except Exception as e:
    print(f"Error fetching transcript: {e}")


# 2) Spitting

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_text(transcript)

## 3) Embedding & Vector Store
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
vector_store = FAISS.from_texts(chunks, embeddings)

# print("Vector store created successfully!")
# print(vector_store.index_to_docstore_id)

# 4) Retrieval
retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})

# Join the documents
def format_docs(docs):
    return "\n\n".join(document.page_content for document in docs)

# 5) LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# 6) Prompt
prompt = PromptTemplate(
    template="""
      You are a helpful assistant.
      Answer ONLY from the provided transcript context.
      Keep your answer concise and strictly under 2 to 3 sentences.
      If the context is insufficient, just say you don't know.

      {context}
      Question: {question}
    """,
    input_variables=['context', 'question']
)

# 7) Chains
parallel_chain = RunnableParallel({
    'context': retriever | RunnableLambda(format_docs),
    'question': RunnablePassthrough()
})

parser = StrOutputParser()

# LCEL
main_chain = parallel_chain | prompt | llm | parser

# Testing the chain
result = main_chain.invoke('Can you summarize the video')
print(result)
