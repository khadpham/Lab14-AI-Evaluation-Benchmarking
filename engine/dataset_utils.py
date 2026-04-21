import json
from pathlib import Path
from typing import Any, Dict, List


MERGE_MARKER_PREFIXES = ("<<<<<<<", "=======", ">>>>>>>")


def load_jsonl_records(path: str | Path) -> List[Dict[str, Any]]:
    dataset_path = Path(path)
    records: List[Dict[str, Any]] = []

    with dataset_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith(MERGE_MARKER_PREFIXES):
                continue
            records.append(json.loads(stripped))

    return records
