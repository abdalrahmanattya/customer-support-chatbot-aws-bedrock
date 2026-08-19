"""Knowledge Base Retrieval and Vector Index Layer for Customer Support Chatbot."""

import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_FAQ_PATH = Path(__file__).parent.parent / "prompts" / "online_shop_faq.md"


class KnowledgeChunk(BaseModel):
    """A discrete knowledge chunk with metadata and relevance score."""
    chunk_id: str
    title: str
    content: str
    score: float = 0.0
    category: str = "general"


class KnowledgeBaseRetriever:
    """
    Retriever supporting both Amazon Bedrock Knowledge Base vector lookups
    and local chunked TF-IDF / vector similarity search.
    """

    def __init__(
        self,
        knowledge_base_id: str | None = None,
        boto_session: Any = None,
        region_name: str = "us-east-1",
        faq_path: Path | None = None,
        top_k: int = 3,
    ):
        self.knowledge_base_id = knowledge_base_id
        self.boto_session = boto_session
        self.region_name = region_name
        self.top_k = top_k
        self.faq_path = faq_path or DEFAULT_FAQ_PATH

        self.bedrock_agent_runtime = None
        if self.knowledge_base_id and self.boto_session:
            try:
                self.bedrock_agent_runtime = self.boto_session.client(
                    "bedrock-agent-runtime",
                    region_name=self.region_name
                )
            except Exception as exc:
                logger.warning("Could not initialize bedrock-agent-runtime client: %s", exc)

        # Build local vector index from FAQ file
        self.chunks: list[KnowledgeChunk] = []
        self._load_and_index_faq()

    def retrieve(self, query: str, top_k: int | None = None) -> list[KnowledgeChunk]:
        """
        Retrieve the top-K most relevant knowledge chunks for a query.
        Falls back to local vector matching if Bedrock KB is not configured.
        """
        k = top_k or self.top_k
        clean_query = query.strip()
        if not clean_query:
            return self.chunks[:k]

        # 1. Try Live Bedrock Knowledge Base Vector Search
        if self.knowledge_base_id and self.bedrock_agent_runtime:
            try:
                response = self.bedrock_agent_runtime.retrieve(
                    knowledgeBaseId=self.knowledge_base_id,
                    retrievalQuery={"text": clean_query},
                    retrievalConfiguration={
                        "vectorSearchConfiguration": {
                            "numberOfResults": k
                        }
                    }
                )
                results = response.get("retrievalResults", [])
                chunks = []
                for idx, r in enumerate(results):
                    content = r.get("content", {}).get("text", "")
                    score = r.get("score", 0.0)
                    chunks.append(
                        KnowledgeChunk(
                            chunk_id=f"bedrock_kb_{idx}",
                            title=f"Knowledge Result {idx + 1}",
                            content=content,
                            score=score
                        )
                    )
                if chunks:
                    return chunks
            except Exception as exc:
                logger.warning("Bedrock KB retrieve API call failed (%s), using local index", exc)

        # 2. Local TF-IDF Vector Similarity Search
        return self._local_vector_search(clean_query, top_k=k)

    def _load_and_index_faq(self) -> None:
        """Parse markdown FAQ document into discrete QA chunks."""
        if not self.faq_path.exists():
            return

        text = self.faq_path.read_text(encoding="utf-8")
        chunks = []
        current_category = "General"

        # Regex to split on each Question block: - **Q1: ...**
        qa_pattern = re.compile(r"-\s+\*\*(Q\d+:\s*([^*]+))\*\*\s*\n\s+-\s+\*\*Answer\*\*:\s*([^\n]+(?:\n(?!\s*-\s+\*\*Q\d+:|\s*##\s*)[^\n]+)*)", re.MULTILINE)
        
        # Track categories by scanning line by line
        lines = text.splitlines()
        category_map = {}
        curr_cat = "General"
        for line in lines:
            if line.startswith("## "):
                curr_cat = line.strip("# ").strip()
            q_match = re.match(r"-\s+\*\*(Q\d+):", line)
            if q_match:
                category_map[q_match.group(1)] = curr_cat

        for idx, match in enumerate(qa_pattern.finditer(text)):
            full_q_tag = match.group(1).strip()
            q_num_match = re.match(r"^(Q\d+)", full_q_tag)
            q_num = q_num_match.group(1) if q_num_match else f"Q{idx + 1}"
            
            q_title = full_q_tag
            ans_text = match.group(3).strip()
            category = category_map.get(q_num, current_category)

            chunk_content = f"**Question ({q_title})**: {ans_text}"

            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"faq_{q_num.lower()}",
                    title=f"{q_title} ({category})",
                    content=chunk_content,
                    category=category
                )
            )

        self.chunks = chunks

    def _tokenize(self, text: str) -> list[str]:
        """Simple word tokenizer for TF-IDF."""
        return re.findall(r"\b[a-z0-9]{2,}\b", text.lower())

    def _local_vector_search(self, query: str, top_k: int = 3) -> list[KnowledgeChunk]:
        """Compute TF-IDF cosine similarity scores over local chunks."""
        if not self.chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.chunks[:top_k]

        query_counts = Counter(query_tokens)

        # Compute document frequencies
        doc_count = len(self.chunks)
        doc_tokens_list = [self._tokenize(c.content) for c in self.chunks]
        
        scored_chunks = []
        for idx, chunk in enumerate(self.chunks):
            doc_tokens = doc_tokens_list[idx]
            if not doc_tokens:
                continue

            doc_counts = Counter(doc_tokens)
            
            # TF-IDF dot product
            score = 0.0
            for term, q_tf in query_counts.items():
                if term in doc_counts:
                    d_tf = doc_counts[term]
                    df = sum(1 for dt in doc_tokens_list if term in dt)
                    idf = math.log((doc_count + 1) / (df + 1)) + 1.0
                    score += (q_tf * idf) * (d_tf * idf)

            # Cosine normalization
            q_norm = math.sqrt(sum(v ** 2 for v in query_counts.values())) or 1.0
            d_norm = math.sqrt(sum(v ** 2 for v in doc_counts.values())) or 1.0
            cos_sim = score / (q_norm * d_norm)

            # Bonus for query terms matching chunk title / category
            title_lower = chunk.title.lower()
            category_lower = chunk.category.lower()
            for t in query_tokens:
                if t in title_lower or t in category_lower:
                    cos_sim += 0.2

            scored_chunk = chunk.model_copy(update={"score": round(cos_sim, 4)})
            scored_chunks.append(scored_chunk)

        scored_chunks.sort(key=lambda x: x.score, reverse=True)
        return scored_chunks[:top_k]
