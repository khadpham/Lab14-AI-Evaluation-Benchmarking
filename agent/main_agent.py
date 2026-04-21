import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List

import chromadb
from dotenv import load_dotenv
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

class MainAgent:
    """
    Baseline retrieval agent (Dense RAG) re-implemented theo hướng day08,
    nhưng dùng vector DB được tạo bởi data/ingest_docs.py trong repo hiện tại.
    """
    def __init__(self):
        load_dotenv()

        self.name = "Dense-Retrieval-Baseline"
        self.repo_root = Path(__file__).resolve().parents[1]
        self.vector_db_path = Path(os.getenv("VECTOR_DB_PATH", str(self.repo_root / "data" / "vector_db" / "chroma_db")))
        self.collection_name = os.getenv("VECTOR_COLLECTION", "evaluation_docs")
        self.top_k_search = int(os.getenv("BASELINE_TOP_K_SEARCH", "10"))
        self.top_k_select = int(os.getenv("BASELINE_TOP_K_SELECT", "3"))
        self.answer_model = os.getenv("BASELINE_AGENT_MODEL", "qwen/qwen3-32b")
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "dangvantuan/vietnamese-embedding")

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
            include=["documents", "metadatas", "distances"]
        )

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
If context is insufficient, reply that you do not have enough information in the available documents.
Keep answer concise and factual.
Cite evidence using [1], [2], ... where possible.
Respond in the same language as the question.

Question: {question}

Context:
{context_text}

Answer:
""".strip()

    async def _generate_answer(self, question: str, contexts: List[str], metadatas: List[Dict[str, Any]]) -> str:
        if not self.llm_client:
            snippet = contexts[0].strip() if contexts else ""
            if not snippet:
                return "Tôi không có đủ dữ liệu trong tài liệu hiện có để trả lời câu hỏi này."
            return snippet[:500]

        prompt = self._build_grounded_prompt(question, contexts, metadatas)
        response = await self.llm_client.chat.completions.create(
            model=self.answer_model,
            temperature=0.0,
            max_tokens=350,
            messages=[
                {"role": "system", "content": "You are a grounded enterprise support assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()

    async def query(self, question: str) -> Dict:
        """
        Dense retrieval từ ChromaDB + grounded generation.
        """
        retrieved = await asyncio.to_thread(self._retrieve_dense, question)
        docs = (retrieved.get("documents") or [[]])[0][: self.top_k_select]
        metas = (retrieved.get("metadatas") or [[]])[0][: self.top_k_select]

        if not docs:
            answer = "Tôi không có đủ dữ liệu trong tài liệu hiện có để trả lời câu hỏi này."
            retrieved_ids_ordered: List[str] = []
        else:
            answer = await self._generate_answer(question, docs, metas)
            retrieved_ids_ordered = []
            for meta in metas:
                doc_id = str(meta.get("doc_id", "")).strip()
                if doc_id and doc_id not in retrieved_ids_ordered:
                    retrieved_ids_ordered.append(doc_id)

        sources = [meta.get("doc_source", meta.get("doc_id", "")) for meta in metas]

        return {
            "answer": answer,
            "contexts": docs,
            "retrieved_ids": retrieved_ids_ordered,
            "metadata": {
                "model": self.answer_model,
                "retrieval_mode": "dense",
                "sources": sources,
                "retrieved_ids": retrieved_ids_ordered,
                "top_k_search": self.top_k_search,
                "top_k_select": self.top_k_select,
                "vector_db_path": str(self.vector_db_path),
                "collection": self.collection_name,
                "embedding_model": self.resolved_embedding_model,
            }
        }

if __name__ == "__main__":
    agent = MainAgent()
    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)
    asyncio.run(test())
