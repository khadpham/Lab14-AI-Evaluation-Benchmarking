from engine.dataset_utils import load_jsonl_records


def test_load_jsonl_records_skips_git_merge_markers(tmp_path):
    dataset = tmp_path / "golden_set.jsonl"
    dataset.write_text(
        "\n".join(
            [
                "<<<<<<< HEAD",
                '{"question":"Q1","expected_answer":"A1"}',
                "=======",
                '{"question":"Q2","expected_answer":"A2"}',
                ">>>>>>> branch",
            ]
        ),
        encoding="utf-8",
    )

    records = load_jsonl_records(dataset)

    assert records == [
        {"question": "Q1", "expected_answer": "A1"},
        {"question": "Q2", "expected_answer": "A2"},
    ]
