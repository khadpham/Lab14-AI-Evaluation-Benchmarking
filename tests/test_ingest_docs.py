from pathlib import Path

from data.ingest_docs import DOC_CONFIG, parse_document_file


REPO_ROOT = Path(__file__).resolve().parents[1]


def _chunk_map(filename: str):
    filepath = REPO_ROOT / "data" / "docs" / filename
    chunks = parse_document_file(str(filepath), DOC_CONFIG[filename])
    return {chunk["chunk_id"]: chunk for chunk in chunks}


def test_hr_remote_chunk_keeps_remote_policy_facts():
    chunks = _chunk_map("hr_leave_policy.txt")

    remote_chunk = chunks["hr_leave_policy_4_remote_work"]["content"]

    assert "2 ngày/tuần" in remote_chunk
    assert "Team Lead phải phê duyệt" in remote_chunk


def test_it_helpdesk_chunks_keep_key_answers():
    chunks = _chunk_map("it_helpdesk_faq.txt")

    vpn_chunk = chunks["it_helpdesk_2_vpn_remote"]["content"]
    software_chunk = chunks["it_helpdesk_3_software_license"]["content"]
    hardware_chunk = chunks["it_helpdesk_4_hardware_device"]["content"]

    assert "Cisco AnyConnect" in vpn_chunk
    assert "Line Manager phải phê duyệt" in software_chunk
    assert "onboarding đầu tiên" in hardware_chunk
