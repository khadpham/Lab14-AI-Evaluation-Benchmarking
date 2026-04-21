from typing import List, Dict, Any

class RetrievalEvaluator:
    def __init__(self, top_k: int = 3):
        self.top_k = top_k

    @staticmethod
    def _normalize_ids(ids: Any) -> List[str]:
        if ids is None:
            return []
        if isinstance(ids, str):
            return [ids]
        if isinstance(ids, list):
            return [str(x) for x in ids if x is not None]
        return []

    def evaluate_case(self, expected_ids: Any, retrieved_ids: Any) -> Dict[str, float]:
        expected = self._normalize_ids(expected_ids)
        retrieved = self._normalize_ids(retrieved_ids)

        if not expected:
            return {"hit_rate": 0.0, "mrr": 0.0}

        hit_rate = self.calculate_hit_rate(expected, retrieved, top_k=self.top_k)
        mrr = self.calculate_mrr(expected, retrieved)
        return {"hit_rate": hit_rate, "mrr": mrr}

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        """
        Hit Rate@k: có ít nhất 1 tài liệu kỳ vọng xuất hiện trong top-k.
        """
        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """
        Mean Reciprocal Rank cho 1 query.
        """
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        """
        Chạy eval retrieval cho toàn bộ bộ dữ liệu.
        Mỗi phần tử dataset có thể chứa:
        - expected_retrieval_ids
        - retrieved_ids
        """
        if not dataset:
            return {"avg_hit_rate": 0.0, "avg_mrr": 0.0, "total_cases": 0}

        hit_rates: List[float] = []
        mrr_scores: List[float] = []

        for case in dataset:
            metrics = self.evaluate_case(
                expected_ids=case.get("expected_retrieval_ids", []),
                retrieved_ids=case.get("retrieved_ids", [])
            )
            hit_rates.append(metrics["hit_rate"])
            mrr_scores.append(metrics["mrr"])

        total = len(dataset)
        return {
            "avg_hit_rate": sum(hit_rates) / total,
            "avg_mrr": sum(mrr_scores) / total,
            "total_cases": total
        }
