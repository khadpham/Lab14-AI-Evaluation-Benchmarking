import asyncio
import json
from pathlib import Path

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.runner import BenchmarkRunner
from main import ExpertEvaluator


def load_dataset(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset file: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def run() -> None:
    ds_path = Path("data/golden_set.jsonl")
    dataset = load_dataset(ds_path)

    judge = LLMJudge(
        gemini_model="gemini-2.5-flash",
        groq_model="qwen/qwen3-32b",
        max_retries=3,
        retry_backoff_seconds=0.8,
    )

    runner = BenchmarkRunner(
        agent=MainAgent(),
        evaluator=ExpertEvaluator(top_k=3),
        judge=judge,
        max_concurrency=3,
        max_retries=2,
        retry_backoff_seconds=0.5,
        pass_threshold=3.0,
    )

    results = await runner.run_all(dataset, batch_size=3)

    gemini_model = "gemini-2.5-flash"
    groq_model = "qwen/qwen3-32b"

    fallback_cases = [
        r for r in results if r.get("judge", {}).get("resolution_method") == "single_judge_fallback"
    ]
    error_cases = [r for r in results if r.get("status") == "error"]
    cases_with_gemini = [
        r for r in results if gemini_model in r.get("judge", {}).get("individual_scores", {})
    ]
    cases_with_both = [
        r
        for r in results
        if all(m in r.get("judge", {}).get("individual_scores", {}) for m in (gemini_model, groq_model))
    ]

    total = len(results)
    summary = {
        "dataset_file": str(ds_path),
        "total_cases": total,
        "error_cases": len(error_cases),
        "fallback_cases": len(fallback_cases),
        "cases_with_gemini_score": len(cases_with_gemini),
        "cases_with_both_judges": len(cases_with_both),
        "avg_final_score": round(
            sum(r.get("judge", {}).get("final_score", 0.0) for r in results) / total, 3
        )
        if total
        else 0.0,
        "avg_agreement_rate": round(
            sum(r.get("judge", {}).get("agreement_rate", 0.0) for r in results) / total, 3
        )
        if total
        else 0.0,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if fallback_cases or len(cases_with_gemini) != total or len(cases_with_both) != total or error_cases:
        raise RuntimeError(
            "STRICT_CHECK_FAILED: fallback or missing Gemini/both-judge coverage detected."
        )

    sample = results[0]["judge"]
    print("SAMPLE_GEMINI_REASONING:", sample["reasoning"].get(gemini_model, "N/A"))
    print("STRICT_CHECK_PASSED")


if __name__ == "__main__":
    asyncio.run(run())
