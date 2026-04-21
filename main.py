import asyncio
import json
import os
import re
import time
from engine.runner import BenchmarkRunner
from engine.retrieval_eval import RetrievalEvaluator
from engine.dataset_utils import load_jsonl_records
from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge

class ExpertEvaluator:
    def __init__(self, top_k: int = 3):
        self.retrieval_eval = RetrievalEvaluator(top_k=top_k)

    @staticmethod
    def _tokenize(text: str):
        if not text:
            return set()
        return set(re.findall(r"\w+", text.lower()))

    def _lexical_overlap_score(self, pred: str, gold: str) -> float:
        pred_tokens = self._tokenize(pred)
        gold_tokens = self._tokenize(gold)
        if not pred_tokens or not gold_tokens:
            return 0.0

        overlap = len(pred_tokens & gold_tokens)
        precision = overlap / len(pred_tokens)
        recall = overlap / len(gold_tokens)
        if precision + recall == 0:
            return 0.0
        return (2 * precision * recall) / (precision + recall)

    async def score(self, case, resp):
        retrieved_ids = (
            resp.get("retrieved_chunk_ids")
            or resp.get("metadata", {}).get("retrieved_chunk_ids")
            or resp.get("retrieved_ids")
            or resp.get("metadata", {}).get("retrieved_ids")
            or resp.get("metadata", {}).get("sources")
            or []
        )
        expected_ids = (
            case.get("ground_truth_chunk_ids")
            or case.get("expected_retrieval_ids")
            or case.get("ground_truth_doc_ids")
            or []
        )

        retrieval = self.retrieval_eval.evaluate_case(expected_ids, retrieved_ids)

        overlap = self._lexical_overlap_score(resp.get("answer", ""), case.get("expected_answer", ""))
        faithfulness = round(min(1.0, overlap + 0.1), 3)
        relevancy = round(overlap, 3)

        return {
            "faithfulness": faithfulness,
            "relevancy": relevancy,
            "retrieval": retrieval
        }

async def run_benchmark_with_results(agent_version: str):
    print(f"[BENCHMARK] Khoi dong Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("[ERROR] Thieu data/golden_set.jsonl. Hay chay 'python data/synthetic_gen.py' truoc.")
        return None, None

    dataset = load_jsonl_records("data/golden_set.jsonl")

    if not dataset:
        print("[ERROR] File data/golden_set.jsonl rong. Hay tao it nhat 1 test case.")
        return None, None

    gemini_model = os.getenv("LLM_JUDGE_GEMINI_MODEL", "gemini-2.5-flash")
    groq_model = os.getenv("LLM_JUDGE_GROQ_MODEL", "qwen/qwen3-32b")
    max_concurrency = int(os.getenv("BENCHMARK_MAX_CONCURRENCY", "5"))
    max_retries = int(os.getenv("BENCHMARK_MAX_RETRIES", "2"))

    runner = BenchmarkRunner(
        agent=MainAgent(),
        evaluator=ExpertEvaluator(top_k=3),
        judge=LLMJudge(gemini_model=gemini_model, groq_model=groq_model),
        max_concurrency=max_concurrency,
        max_retries=max_retries,
        retry_backoff_seconds=0.5,
        pass_threshold=3.0
    )
    results = await runner.run_all(dataset, batch_size=max_concurrency)

    total = len(results)
    valid_results = [r for r in results if r.get("judge")]
    passed = [r for r in results if r.get("status") == "pass"]
    errors = [r for r in results if r.get("status") == "error"]

    avg_score = (sum(r["judge"].get("final_score", 0) for r in valid_results) / len(valid_results)) if valid_results else 0.0
    avg_hit_rate = (sum(r["ragas"]["retrieval"].get("hit_rate", 0) for r in results) / total) if total else 0.0
    avg_mrr = (sum(r["ragas"]["retrieval"].get("mrr", 0) for r in results) / total) if total else 0.0
    avg_agreement = (sum(r["judge"].get("agreement_rate", 0) for r in valid_results) / len(valid_results)) if valid_results else 0.0
    avg_latency = (sum(r.get("latency", 0) for r in results) / total) if total else 0.0
    conflict_rate = (
        sum(1 for r in valid_results if r["judge"].get("conflict_detected")) / len(valid_results)
    ) if valid_results else 0.0

    summary = {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "judge_models": {
                "gemini": gemini_model,
                "groq": groq_model
            },
            "runner": {
                "max_concurrency": max_concurrency,
                "max_retries": max_retries
            }
        },
        "metrics": {
            "avg_score": avg_score,
            "hit_rate": avg_hit_rate,
            "mrr": avg_mrr,
            "agreement_rate": avg_agreement,
            "conflict_rate": conflict_rate,
            "avg_latency_sec": avg_latency,
            "pass_rate": (len(passed) / total) if total else 0.0,
            "error_rate": (len(errors) / total) if total else 0.0
        }
    }
    return results, summary

async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary

async def main():
    v1_summary = await run_benchmark("Agent_V1_Base")
    
    # Giả lập V2 có cải tiến (để test logic)
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")
    
    if not v1_summary or not v2_summary:
        print("[ERROR] Khong the chay Benchmark. Kiem tra lai data/golden_set.jsonl.")
        return

    print("\n[KET QUA SO SANH - REGRESSION]")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    print(f"V1 Score: {v1_summary['metrics']['avg_score']}")
    print(f"V2 Score: {v2_summary['metrics']['avg_score']}")
    print(f"Delta: {'+' if delta >= 0 else ''}{delta:.2f}")

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if delta > 0:
        print("[APPROVE] Quyet dinh: Chap nhan ban cap nhat")
    else:
        print("[BLOCK] Quyet dinh: Tu choi release")

if __name__ == "__main__":
    asyncio.run(main())
