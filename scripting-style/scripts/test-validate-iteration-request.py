#!/usr/bin/env python3
"""Run deterministic compatibility tests for the iteration request validator."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "validate-iteration-request.py"
FIXTURE_ROOT = SKILL_ROOT / "validation" / "fixtures" / "iteration-source"


def skill_fingerprint() -> str:
    """Hash persistent Skill files so validator writes cannot go unnoticed."""

    digest = hashlib.sha256()
    for path in sorted(SKILL_ROOT.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        digest.update(str(path.relative_to(SKILL_ROOT)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run_request(request: dict, expected_success: bool = True):
    """Run one stdin request and assert the expected exit class."""

    result = subprocess.run(
        ["python3", str(VALIDATOR), "-"],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
    )
    if expected_success and result.returncode != 0:
        raise AssertionError(result.stderr)
    if not expected_success and result.returncode == 0:
        raise AssertionError("Request unexpectedly passed validation.")
    return result


def phase1_request(example, iteration_id="compat-test") -> dict:
    return {
        "schema_version": "1.0",
        "iteration_id": iteration_id,
        "phase": "phase1",
        "target_skill": str(SKILL_ROOT),
        "new_examples": [example],
        "context_readmes": [],
        "approval": {"confirmed": False, "accepted_decisions": []},
    }


before = skill_fingerprint()

# Existing schema 1.0 R request remains valid.
old_request = phase1_request(str(FIXTURE_ROOT / "scripts" / "example.R"))
old_manifest = json.loads(run_request(old_request).stdout)
assert [entry["language"] for entry in old_manifest["examples"]] == ["R"]

# Notebook is accepted, and the legacy stage hint is metadata rather than routing.
notebook_request = phase1_request(
    {
        "path": str(FIXTURE_ROOT / "scripts" / "example.ipynb"),
        "stage_hint": "legacy-context",
        "role_hint": "candidate",
    },
    iteration_id="notebook-test",
)
notebook_manifest = json.loads(run_request(notebook_request).stdout)
assert notebook_manifest["examples"][0]["language"] == "Notebook"
assert notebook_manifest["examples"][0]["stage_hint"] == "legacy-context"

# A project directory discovers exactly the four supported file types under scripts/.
directory_manifest = json.loads(
    run_request(
        phase1_request(str(FIXTURE_ROOT), iteration_id="directory-test")
    ).stdout
)
assert {entry["language"] for entry in directory_manifest["examples"]} == {
    "R",
    "Python",
    "Bash",
    "Notebook",
}
assert len(directory_manifest["examples"]) == 4

# Excluded directories inside the fixture repository remain rejected explicitly.
for excluded_path in [
    FIXTURE_ROOT / "data" / "ignored.R",
    FIXTURE_ROOT / "R" / "ignored.R",
]:
    rejected = run_request(
        phase1_request(str(excluded_path), iteration_id="excluded-test"),
        expected_success=False,
    )
    assert "excluded directory" in rejected.stderr

# A machine-level ancestor named data is not mistaken for a project data/ directory.
with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
    machine_data_dir = Path(temp_dir) / "data"
    machine_data_dir.mkdir()
    external_example = machine_data_dir / "example.R"
    external_example.write_text("value <- 1\n", encoding="utf-8")
    run_request(
        phase1_request(str(external_example), iteration_id="ancestor-test")
    )

# A malformed file with an .ipynb suffix passes byte-level preflight by design;
# Phase 1 performs Notebook JSON and semantic review.
with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
    malformed_notebook = Path(temp_dir) / "malformed.ipynb"
    malformed_notebook.write_text("not notebook json\n", encoding="utf-8")
    malformed_manifest = json.loads(
        run_request(
            phase1_request(str(malformed_notebook), iteration_id="malformed-test")
        ).stdout
    )
    assert malformed_manifest["examples"][0]["language"] == "Notebook"

# Negative contract checks remain intact.
schema_request = dict(old_request)
schema_request["schema_version"] = "2.0"
run_request(schema_request, expected_success=False)

confirmed_phase1 = dict(old_request)
confirmed_phase1["approval"] = {"confirmed": True, "accepted_decisions": []}
run_request(confirmed_phase1, expected_success=False)

with tempfile.TemporaryDirectory(dir="/tmp") as review_dir:
    incomplete_phase2 = dict(old_request)
    incomplete_phase2["phase"] = "phase2"
    incomplete_phase2["phase1_review_dir"] = review_dir
    incomplete_phase2["approval"] = {"confirmed": True, "accepted_decisions": []}
    run_request(incomplete_phase2, expected_success=False)

    complete_phase2 = dict(incomplete_phase2)
    complete_phase2["approval"] = {
        "confirmed": True,
        "accepted_decisions": ["exact-type routing"],
    }
    phase2_manifest = json.loads(run_request(complete_phase2).stdout)
    assert phase2_manifest["phase2_request_complete"] is True
    assert phase2_manifest["validator_grants_write_authority"] is False
    assert phase2_manifest["requires_current_conversation_confirmation"] is True

assert old_manifest["source_examples_read_only"] is True
assert old_manifest["skill_rule_write_allowed"] is False
assert before == skill_fingerprint()

print("iteration-validator-tests: pass")
