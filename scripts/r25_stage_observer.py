"""Internal fixed-fixture stage transport; no execution or authentication API."""
import hashlib
import json

from cbdk.extension_preflight import MAX_ARCHIVE_BYTES
from cbdk.extension_stage_evidence import STAGES, FAILURES

STAGE_PREFIX = "CBDK_R25_NATIVE_STAGE "


def archive_digest(path):
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_ARCHIVE_BYTES + 1)
        if len(raw) > MAX_ARCHIVE_BYTES:
            return None
        return hashlib.sha256(raw).hexdigest()
    except OSError:
        return None


def stage_record(case, version, run_id, digest, stage, status, diagnostic=None):
    return {"case": case, "blender": version, "run_id": run_id,
            "artifact_sha256": digest, "stage": stage, "status": status,
            "reason": FAILURES[stage] if status == "failed" else None,
            "diagnostic": diagnostic}


def parse_records(log, prefix, *, max_records):
    if not isinstance(log, str) or len(log) > 2_000_000:
        raise ValueError("Missing or oversized fixture output")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate observation field")
            result[key] = value
        return result
    rows = [line[len(prefix):] for line in log.splitlines() if line.startswith(prefix)]
    if len(rows) > max_records:
        raise ValueError("Excess fixture records")
    result = [json.loads(row, object_pairs_hook=unique) for row in rows]
    if any(type(row) is not dict for row in result):
        raise ValueError("Invalid fixture observation")
    return result


def finish_failure(records):
    # Only an explicit observed failed gate allows not_run successors.
    # Missing observations remain incomplete, not fabricated failures.
    if not records or records[-1].get("status") != "failed":
        return
    last = records[-1]
    if type(last.get("stage")) is not str or last["stage"] not in STAGES or len(records) != STAGES.index(last["stage"]) + 1:
        return
    required = {"case", "blender", "run_id", "artifact_sha256", "stage", "status", "reason", "diagnostic"}
    if set(last) != required:
        return
    for stage in STAGES[len(records):]:
        records.append(stage_record(last["case"], last["blender"], last["run_id"],
                                    last["artifact_sha256"], stage, "not_run"))
