"""Unit tests for Knowledge Base RAG and Vector Retrieval Layer."""

from src.agent.prompts.system_prompt import get_system_prompt
from src.agent.rag.retriever import KnowledgeBaseRetriever, KnowledgeChunk


def test_retriever_initialization_and_chunking():
    """Verify retriever parses FAQ markdown into structured chunks."""
    retriever = KnowledgeBaseRetriever()
    assert len(retriever.chunks) >= 20
    
    first_chunk = retriever.chunks[0]
    assert isinstance(first_chunk, KnowledgeChunk)
    assert first_chunk.title
    assert first_chunk.content


def test_retriever_similarity_search_returns():
    """Verify retriever surfaces return policy chunks for return queries."""
    retriever = KnowledgeBaseRetriever(top_k=3)
    results = retriever.retrieve("What is the return window and how do I get a refund?")
    
    assert len(results) == 3
    combined_text = " ".join(r.content.lower() for r in results)
    assert "return" in combined_text or "refund" in combined_text
    assert results[0].score > 0.0


def test_retriever_similarity_search_shipping():
    """Verify retriever surfaces shipping and tracking chunks."""
    retriever = KnowledgeBaseRetriever(top_k=3)
    results = retriever.retrieve("How long does shipping take and can I track my package?")
    
    assert len(results) == 3
    combined_text = " ".join(r.content.lower() for r in results)
    assert "shipping" in combined_text or "track" in combined_text or "delivery" in combined_text


def test_dynamic_system_prompt_generation():
    """Verify get_system_prompt correctly incorporates retrieved chunks."""
    sample_chunks = [
        KnowledgeChunk(chunk_id="c1", title="Test Return Policy", content="You have 30 days to return.", score=0.9),
        KnowledgeChunk(chunk_id="c2", title="Test Shipping Info", content="Shipping takes 1-2 days.", score=0.8),
    ]
    prompt = get_system_prompt(retrieved_chunks=sample_chunks)
    
    assert "### Test Return Policy" in prompt
    assert "You have 30 days to return." in prompt
    assert "### Test Shipping Info" in prompt
    assert "RETRIEVED KNOWLEDGE BASE CONTEXT" in prompt
