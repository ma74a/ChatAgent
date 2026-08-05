from langchain_community.document_loaders import (
    PyMuPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


Path("chroma_db").mkdir(exist_ok=True)
Path("uploads").mkdir(exist_ok=True)

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

vectorstore = Chroma(
    collection_name="agentic_chatbot_docs",
    embedding_function=embeddings,
    persist_directory="chroma_db"
)

def load_documents(file_path: str) -> List[Document]:
    """function to load the docs depends on it extension"""
    extension = Path(file_path).suffix.lower()
    if extension == ".pdf":
        loader = PyMuPDFLoader(file_path)
    elif extension == ".docx":
        loader = Docx2txtLoader(file_path)
    elif extension == ".csv":
        loader = CSVLoader(file_path)
    elif extension in [".txt", ".md", ".py"]:
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {extension}")

    return loader.load()




def add_docs_to_chroma(file_path: str, thread_id: str):
    """function to split the docs and store it into vector database"""
    documents = load_documents(file_path=file_path)

    if not documents:
        raise ValueError("No text could be extracted from this file.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(documents)


    # since PyMuPDFLoader gives you all the info you want
    docs = [
        Document(
            page_content=chunk.page_content,
            metadata={
                "thread_id": thread_id,
                "source": Path(file_path).name,
                "page_number": chunk.metadata["page"]+1
            }
        )
        for chunk in chunks
    ]
    # for chunk in chunks:
    #     chunk.metadata["thread_id"] = thread_id
    #     chunk.metadata["source"] = Path(file_path).name


    vectorstore.add_documents(documents=docs)

    return {
        "filename": Path(file_path).name,
        "chunks": len(docs)
    }


def retrieve_documents(query: str, thread_id: str, top_k: int=4):
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": top_k,
            "filter": {
                "thread_id": thread_id
            }
        }
    )
    retreived_res = retriever.invoke(query)
    results = []
    for i, docs in enumerate(retreived_res, start=1):
        source = docs.metadata["source"]
        page_number = docs.metadata["page_number"]
        page_content = docs.page_content
        results.append(
            f"source[{i}]: {source}\npage_number: {page_number}\npage_content: {page_content}"
        )

    return  "\n\n".join(results)
