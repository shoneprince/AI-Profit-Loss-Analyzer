"""
Vector Store Module

Builds, saves, and loads a FAISS vector store using
Google Generative AI Embeddings for the P&L documents.
"""

import os
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import EMBEDDING_MODEL, RETRIEVER_TOP_K, VECTORSTORE_DIR


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Create the local HuggingFace embedding model instance."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def build_vectorstore(documents: list[Document]) -> FAISS:
    """
    Create a FAISS vector store from a list of LangChain Documents.

    Args:
        documents: List of Document objects (from the chunker).

    Returns:
        A FAISS vector store instance.
    """
    if not documents:
        raise ValueError("No documents provided to build the vector store.")

    print(f"[VectorStore] Embedding {len(documents)} documents …")
    embeddings = _get_embeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    print("[VectorStore] FAISS index built successfully.")
    return vectorstore


def get_retriever(vectorstore: FAISS, k: int = RETRIEVER_TOP_K):
    """
    Wrap the vector store in a retriever.

    Args:
        vectorstore: FAISS vector store.
        k:           Number of top results to retrieve.

    Returns:
        A LangChain retriever object.
    """
    return vectorstore.as_retriever(search_kwargs={"k": k})


def save_vectorstore(vectorstore: FAISS, path: str = VECTORSTORE_DIR) -> None:
    """
    Persist the FAISS vector store to disk.

    Args:
        vectorstore: FAISS vector store to save.
        path:        Directory to save to.
    """
    os.makedirs(path, exist_ok=True)
    vectorstore.save_local(path)
    print(f"[VectorStore] Saved to {path}")


def load_vectorstore(path: str = VECTORSTORE_DIR) -> FAISS:
    """
    Load a previously saved FAISS vector store from disk.

    Args:
        path: Directory containing the saved index.

    Returns:
        A FAISS vector store instance.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No saved vector store at: {path}")

    embeddings = _get_embeddings()
    vectorstore = FAISS.load_local(
        path, embeddings, allow_dangerous_deserialization=True,
    )
    print(f"[VectorStore] Loaded from {path}")
    return vectorstore
