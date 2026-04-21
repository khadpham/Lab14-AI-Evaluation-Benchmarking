import re
from typing import Any, Dict, List


STOPWORDS = {
    "ai",
    "cho",
    "co",
    "có",
    "cua",
    "của",
    "duoc",
    "được",
    "gi",
    "gì",
    "hay",
    "hãy",
    "khi",
    "khong",
    "không",
    "la",
    "là",
    "lam",
    "làm",
    "mot",
    "một",
    "nao",
    "nào",
    "neu",
    "nếu",
    "nhu",
    "như",
    "phai",
    "phải",
    "sao",
    "sau",
    "the",
    "thể",
    "thi",
    "thì",
    "toi",
    "tôi",
    "tu",
    "từ",
    "va",
    "và",
    "ve",
    "về",
    "voi",
    "với",
}

INSUFFICIENT_PATTERNS = (
    "không có đủ thông tin",
    "không tìm thấy thông tin",
    "không có thông tin",
    "không đủ dữ liệu",
)


def tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return {
        token
        for token in re.findall(r"\w+", text.lower())
        if len(token) > 1 and token not in STOPWORDS
    }


def strip_think_block(text: str) -> str:
    if not text:
        return ""

    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*|\s*```$", "", cleaned, flags=re.MULTILINE).strip()
    return cleaned


def _candidate_text(candidate: Dict[str, Any]) -> str:
    metadata = candidate.get("metadata") or {}
    parts = [
        candidate.get("document", ""),
        str(metadata.get("section_title", "")).replace("_", " "),
        str(metadata.get("doc_source", "")),
        str(metadata.get("doc_id", "")),
    ]
    return " ".join(part for part in parts if part)


def rerank_candidates(question: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    question_tokens = tokenize(question)
    ranked: List[Dict[str, Any]] = []

    for index, candidate in enumerate(candidates):
        metadata = candidate.get("metadata") or {}
        section_tokens = tokenize(str(metadata.get("section_title", "")).replace("_", " "))
        candidate_tokens = tokenize(_candidate_text(candidate))
        overlap = len(question_tokens & candidate_tokens)
        title_overlap = len(question_tokens & section_tokens)
        distance = float(candidate.get("distance", 1.0) or 1.0)

        overlap_score = overlap / max(len(question_tokens), 1)
        title_score = title_overlap / max(len(section_tokens), 1) if section_tokens else 0.0
        dense_score = 1.0 / (1.0 + max(distance, 0.0))
        rank_bonus = 1.0 / (index + 1)

        score = (overlap_score * 0.55) + (title_score * 0.25) + (dense_score * 0.15) + (rank_bonus * 0.05)

        enriched = dict(candidate)
        enriched["ranking"] = {
            "score": round(score, 4),
            "overlap": overlap,
            "title_overlap": title_overlap,
            "distance": distance,
        }
        ranked.append(enriched)

    ranked.sort(
        key=lambda item: (
            item["ranking"]["score"],
            item["ranking"]["title_overlap"],
            item["ranking"]["overlap"],
            -item["ranking"]["distance"],
        ),
        reverse=True,
    )
    return ranked


def _clean_lines(document: str) -> List[str]:
    return [
        line.strip()
        for line in document.splitlines()
        if line.strip() and line.strip() != "==="
    ]


def extract_answer_from_context(question: str, candidates: List[Dict[str, Any]]) -> str:
    question_tokens = tokenize(question)
    best_answer = ""
    best_score = 0.0

    for candidate in candidates:
        lines = _clean_lines(candidate.get("document", ""))
        for index, line in enumerate(lines):
            normalized_line = line.lower()
            overlap = len(question_tokens & tokenize(line))

            if normalized_line.startswith("q:") and index + 1 < len(lines):
                next_line = lines[index + 1]
                if next_line.lower().startswith("a:"):
                    score = overlap + 0.5
                    if score > best_score:
                        best_score = score
                        best_answer = next_line[2:].strip()
                    continue

            if overlap <= 0:
                continue

            score = overlap / max(len(question_tokens), 1)
            if score > best_score:
                best_score = score
                best_answer = re.sub(r"^[QA]:\s*", "", line).strip()

    return best_answer


def is_insufficient_answer(answer: str) -> bool:
    normalized = strip_think_block(answer).lower()
    return any(pattern in normalized for pattern in INSUFFICIENT_PATTERNS)
