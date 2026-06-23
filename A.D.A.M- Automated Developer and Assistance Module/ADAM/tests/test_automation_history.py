"""Tests for job history."""
import os

import pytest

from ADAM.automations.history import JobHistory, reset_job_history


@pytest.fixture()
def history(tmp_path, monkeypatch):
    from ADAM.core.config import reset_settings
    reset_settings()
    reset_job_history()
    monkeypatch.setenv("ADAM_DB_PATH", str(tmp_path / "test.db"))
    return JobHistory()


def test_record_and_get(history):
    record = history.record(
        {
            "job_id": "job1",
            "workflow_id": "wf1",
            "start_time": "2026-06-22T00:00:00",
            "end_time": "2026-06-22T00:00:01",
            "duration": 1.0,
            "success": True,
            "output_summary": {"ok": True},
        }
    )
    assert record["job_id"] == "job1"
    loaded = history.get("job1")
    assert loaded["success"] == 1


def test_list_jobs_filtered(history):
    history.record(
        {
            "job_id": "job1",
            "workflow_id": "wf1",
            "start_time": "2026-06-22T00:00:00",
            "success": True,
        }
    )
    history.record(
        {
            "job_id": "job2",
            "workflow_id": "wf2",
            "start_time": "2026-06-22T00:00:00",
            "success": False,
            "error_message": "boom",
        }
    )
    wf1_jobs = history.list_jobs(workflow_id="wf1")
    assert len(wf1_jobs) == 1
    failed_jobs = history.list_jobs(success=False)
    assert len(failed_jobs) == 1
    assert failed_jobs[0]["error_message"] == "boom"
