import asyncio
import time
from typing import List, Dict, Any, Callable, Awaitable
# Import other components...

class BenchmarkRunner:
    def __init__(
        self,
        agent,
        evaluator,
        judge,
        max_concurrency: int = 5,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.4,
        pass_threshold: float = 3.0
    ):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge
        self.max_concurrency = max(1, max_concurrency)
        self.max_retries = max(1, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.pass_threshold = pass_threshold

    async def _run_with_retry(self, fn: Callable[[], Awaitable[Any]], stage_name: str) -> Any:
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await fn()
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(self.retry_backoff_seconds * attempt)

        raise RuntimeError(f"{stage_name} failed after {self.max_retries} attempts: {last_error}") from last_error

    async def run_single_test(self, test_case: Dict, case_index: int | None = None) -> Dict:
        case_start = time.perf_counter()
        question = test_case.get("question", "")
        expected_answer = test_case.get("expected_answer", "")

        response: Dict[str, Any] = {}
        ragas_scores: Dict[str, Any] = {"faithfulness": 0.0, "relevancy": 0.0, "retrieval": {"hit_rate": 0.0, "mrr": 0.0}}
        judge_result: Dict[str, Any] = {}
        errors: List[str] = []

        # 1) Agent query
        try:
            response = await self._run_with_retry(lambda: self.agent.query(question), stage_name="agent.query")
        except Exception as exc:
            errors.append(str(exc))
            total_latency = time.perf_counter() - case_start
            return {
                "case_id": test_case.get("id", case_index),
                "test_case": question,
                "agent_response": "",
                "latency": total_latency,
                "ragas": ragas_scores,
                "judge": judge_result,
                "errors": errors,
                "status": "error"
            }

        total_latency = time.perf_counter() - case_start

        # 2) Eval metrics
        try:
            ragas_scores = await self._run_with_retry(
                lambda: self.evaluator.score(test_case, response),
                stage_name="evaluator.score"
            )
        except Exception as exc:
            errors.append(str(exc))

        # 3) Multi-judge
        try:
            judge_result = await self._run_with_retry(
                lambda: self.judge.evaluate_multi_judge(question, response.get("answer", ""), expected_answer),
                stage_name="judge.evaluate_multi_judge"
            )
        except Exception as exc:
            errors.append(str(exc))

        final_score = float(judge_result.get("final_score", 0.0)) if judge_result else 0.0
        status = "error" if not judge_result else ("fail" if final_score < self.pass_threshold else "pass")

        return {
            "case_id": test_case.get("id", case_index),
            "test_case": question,
            "agent_response": response.get("answer", ""),
            "latency": total_latency,
            "ragas": ragas_scores,
            "judge": judge_result,
            "errors": errors,
            "status": status
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> List[Dict]:
        """
        Chạy async toàn bộ dataset với semaphore để giới hạn đồng thời.
        batch_size được giữ để tương thích ngược, nhưng ưu tiên max_concurrency.
        """
        if not dataset:
            return []

        concurrency = max(1, min(self.max_concurrency, batch_size))
        semaphore = asyncio.Semaphore(concurrency)

        async def _run_with_semaphore(idx: int, case: Dict) -> Dict:
            async with semaphore:
                return await self.run_single_test(case, case_index=idx)

        tasks = [asyncio.create_task(_run_with_semaphore(idx, case)) for idx, case in enumerate(dataset)]
        return await asyncio.gather(*tasks)
