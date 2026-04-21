import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AsyncOpenAI

from agent.helpers import extract_answer_from_context, is_insufficient_answer, rerank_candidates, strip_think_block

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


INSUFFICIENT_ANSWER = "Tôi không có đủ dữ liệu trong tài liệu hiện có để trả lời câu hỏi này."


class MainAgent:
    """
    Dense retrieval agent with lightweight hybrid reranking and extractive-first answering.
    """

    def __init__(self):
        load_dotenv()

        self.name = "Dense-Retrieval-Optimized"
        self.repo_root = Path(__file__).resolve().parents[1]
        self.vector_db_path = Path(os.getenv("VECTOR_DB_PATH", str(self.repo_root / "data" / "vector_db" / "chroma_db")))
        self.collection_name = os.getenv("VECTOR_COLLECTION", "evaluation_docs")
        self.top_k_search = int(os.getenv("BASELINE_TOP_K_SEARCH", "10"))
        self.top_k_select = int(os.getenv("BASELINE_TOP_K_SELECT", "3"))
        self.answer_model = os.getenv("BASELINE_AGENT_MODEL", "qwen/qwen3-32b")
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "dangvantuan/vietnamese-embedding")

        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is required to run MainAgent.")
        if chromadb is None:
            raise ImportError("chromadb is required to run MainAgent.")

        try:
            self.embedder = SentenceTransformer(self.embedding_model_name)
            self.resolved_embedding_model = self.embedding_model_name
        except Exception:
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            self.resolved_embedding_model = "all-MiniLM-L6-v2"

        self.chroma_client = chromadb.PersistentClient(path=str(self.vector_db_path))
        self.collection = self.chroma_client.get_collection(self.collection_name)

        groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.llm_client = AsyncOpenAI(api_key=groq_api_key, base_url="https://api.groq.com/openai/v1") if groq_api_key else None

    def _retrieve_dense(self, question: str) -> Dict[str, Any]:
        query_embedding = self.embedder.encode(question).tolist()
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k_search,
            include=["documents", "metadatas", "distances"],
        )

    @staticmethod
    def _build_candidates(retrieved: Dict[str, Any]) -> List[Dict[str, Any]]:
        documents = (retrieved.get("documents") or [[]])[0]
        metadatas = (retrieved.get("metadatas") or [[]])[0]
        distances = (retrieved.get("distances") or [[]])[0]
        ids = (retrieved.get("ids") or [[]])[0]

        candidates: List[Dict[str, Any]] = []
        for document, metadata, distance, chunk_id in zip(documents, metadatas, distances, ids):
            normalized_metadata = dict(metadata or {})
            if chunk_id and "chunk_id" not in normalized_metadata:
                normalized_metadata["chunk_id"] = chunk_id
            candidates.append(
                {
                    "document": document,
                    "metadata": normalized_metadata,
                    "distance": distance,
                }
            )
        return candidates

    @staticmethod
    def _build_grounded_prompt(question: str, contexts: List[str], metadatas: List[Dict[str, Any]]) -> str:
        context_blocks = []
        for idx, (ctx, meta) in enumerate(zip(contexts, metadatas), start=1):
            source = meta.get("doc_source", meta.get("doc_id", "unknown"))
            section = meta.get("section_title", "")
            header = f"[{idx}] {source}" + (f" | {section}" if section else "")
            context_blocks.append(f"{header}\n{ctx}")

        context_text = "\n\n".join(context_blocks)
        return f"""
Answer only from the retrieved context below.
If context is insufficient, reply briefly that you do not have enough information in the available documents.
Do not include chain-of-thought or <think> tags.
Keep the answer concise, factual, and in the same language as the question.
Cite evidence using [1], [2], ... when possible.

Question: {question}

Context:
{context_text}

Answer:
""".strip()

    async def _generate_answer(self, question: str, contexts: List[str], metadatas: List[Dict[str, Any]]) -> str:
        extractive_answer = extract_answer_from_context(
            question,
            [{"document": ctx, "metadata": meta, "distance": 0.0} for ctx, meta in zip(contexts, metadatas)],
        )
        if extractive_answer:
            return extractive_answer

        if not self.llm_client:
            snippet = contexts[0].strip() if contexts else ""
            return snippet[:500] if snippet else INSUFFICIENT_ANSWER

        prompt = self._build_grounded_prompt(question, contexts, metadatas)
        response = await self.llm_client.chat.completions.create(
            model=self.answer_model,
            temperature=0.0,
            max_tokens=220,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a grounded enterprise support assistant. "
                        "Answer only with facts explicitly present in the provided context. "
                        "Never reveal chain-of-thought."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return strip_think_block((response.choices[0].message.content or "").strip())

    async def query(self, question: str) -> Dict[str, Any]:
        """
        Dense retrieval from ChromaDB with lexical reranking and extractive-first generation.
        """
        retrieved = await asyncio.to_thread(self._retrieve_dense, question)
        ranked_candidates = rerank_candidates(question, self._build_candidates(retrieved))
        selected_candidates = ranked_candidates[: self.top_k_select]
        docs = [candidate["document"] for candidate in selected_candidates]
        metas = [candidate["metadata"] for candidate in selected_candidates]

        if not docs:
            answer = INSUFFICIENT_ANSWER
            retrieved_ids_ordered: List[str] = []
            retrieved_chunk_ids_ordered: List[str] = []
        else:
            answer = strip_think_block(await self._generate_answer(question, docs, metas))
            retrieved_ids_ordered = []
            retrieved_chunk_ids_ordered = []
            for meta in metas:
                doc_id = str(meta.get("doc_id", "")).strip()
                chunk_id = str(meta.get("chunk_id", "")).strip()
                if doc_id and doc_id not in retrieved_ids_ordered:
                    retrieved_ids_ordered.append(doc_id)
                if chunk_id and chunk_id not in retrieved_chunk_ids_ordered:
                    retrieved_chunk_ids_ordered.append(chunk_id)

            if is_insufficient_answer(answer):
                extractive_answer = extract_answer_from_context(
                    question,
                    [{"document": ctx, "metadata": meta, "distance": 0.0} for ctx, meta in zip(docs, metas)],
                )
                if extractive_answer:
                    answer = extractive_answer

        sources = [meta.get("doc_source", meta.get("doc_id", "")) for meta in metas]

        return {
            "answer": answer,
            "contexts": docs,
            "retrieved_ids": retrieved_ids_ordered,
            "retrieved_chunk_ids": retrieved_chunk_ids_ordered,
            "metadata": {
                "model": self.answer_model,
                "retrieval_mode": "dense_hybrid_rerank",
                "sources": sources,
                "retrieved_ids": retrieved_ids_ordered,
                "retrieved_chunk_ids": retrieved_chunk_ids_ordered,
                "top_k_search": self.top_k_search,
                "top_k_select": self.top_k_select,
                "vector_db_path": str(self.vector_db_path),
                "collection": self.collection_name,
                "embedding_model": self.resolved_embedding_model,
            },
        }


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)

    asyncio.run(test())
