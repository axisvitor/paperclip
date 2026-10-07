"""Local, explicit editorial checks. No network calls or Paperclip enforcement."""

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import struct


KINDS = ("research", "brief", "copy", "design")
WORKING = dict(zip(KINDS, ("RESEARCHING", "CURATING", "COPY_IN_PROGRESS", "DESIGN_IN_PROGRESS")))
READY = dict(zip(KINDS, ("RESEARCHED", "BRIEF_READY", "COPY_READY", "DESIGN_READY")))
NEXT = dict(zip(KINDS, ("CURATING", "COPY_IN_PROGRESS", "DESIGN_IN_PROGRESS", "REVIEW")))
PRODUCERS = {"research": "research", "brief": "editorial", "copy": "copy", "design": "design"}
RECEIVERS = {"research": "editorial", "brief": "copy", "copy": "editorial", "design": "editorial"}
STAGES = {"IDEA", "REVIEW", "APPROVED", *WORKING.values(), *READY.values()}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _integer(value):
    return type(value) is int and value > 0


def _timestamp(value):
    try:
        return _text(value) and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except (ValueError, TypeError):
        return False


def _ref(value, key="handoff_id"):
    return isinstance(value, dict) and set(value) == {key, "revision"} and all(_text(v) for v in value.values())


def _artifact_ref(handoff):
    return {"handoff_id": handoff["handoff_id"], "revision": handoff["artifact_revision"]}


def _required_text(data, fields, prefix, errors):
    for field in fields:
        if not _text(data.get(field)):
            errors.append(f"{prefix}{field}: nonempty string required")


def _validate_file(item, index, errors):
    prefix = f"files[{index}]."
    if not isinstance(item, dict):
        errors.append(prefix + "object required")
        return
    _required_text(item, ("attachment_id", "receipt_id", "name", "local_path", "alt_text"), prefix, errors)
    if item.get("storage_confirmed") is not True:
        errors.append(prefix + "storage_confirmed must be true")
    if item.get("role") not in ("final", "preview"):
        errors.append(prefix + "role must be final or preview")
    for key in ("width", "height", "byte_size"):
        if not _integer(item.get(key)):
            errors.append(prefix + key + ": positive integer required")
    if item.get("role") == "final" and not _integer(item.get("slide_index")):
        errors.append(prefix + "slide_index: positive integer required")
    if item.get("mime_type") != "image/png":
        errors.append(prefix + "only image/png is supported in contract v1")
    if not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
        errors.append(prefix + "sha256: lowercase SHA-256 required")
    try:
        if not _text(item.get("local_path")):
            return
        local = Path(item["local_path"])
        if not local.is_file():
            errors.append(prefix + "local file unavailable or not a regular file")
            return
        blob = local.read_bytes()
        if len(blob) != item.get("byte_size") or hashlib.sha256(blob).hexdigest() != item.get("sha256"):
            errors.append(prefix + "local bytes do not match byte_size/sha256")
        if len(blob) < 33 or blob[:8] != b"\x89PNG\r\n\x1a\n" or blob[12:16] != b"IHDR":
            errors.append(prefix + "local file has no PNG header")
        elif struct.unpack(">II", blob[16:24]) != (item.get("width"), item.get("height")):
            errors.append(prefix + "PNG dimensions differ from manifest")
    except (OSError, ValueError) as exc:
        errors.append(prefix + "local file unavailable: " + type(exc).__name__)


def _validate_handoff(data):
    """Return structural/local-file errors; [] does not assert editorial quality."""
    errors = []
    if not isinstance(data, dict):
        return ["handoff: object required"]
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    _required_text(data, ("handoff_id", "operation_id", "company_id", "brand_id", "source_issue_id",
                          "producer", "intended_receiver", "artifact_revision", "locale", "objective"), "", errors)
    if "target_issue_id" not in data or (data["target_issue_id"] is not None and not _text(data["target_issue_id"])):
        errors.append("target_issue_id: nonempty string or explicit null required")
    scope_ids = {"brand_intelligence": "research_batch_id", "campaign": "campaign_id", "content": "content_id"}
    if data.get("scope") not in scope_ids:
        errors.append("scope: brand_intelligence, campaign or content required")
    elif not _text(data.get(scope_ids[data["scope"]])):
        errors.append(scope_ids[data["scope"]] + ": required for this scope")
    for field in ("channel", "format"):
        if field not in data or (data.get("scope") == "content" and not _text(data.get(field))):
            errors.append(field + ": required (null permitted only outside content)")
        elif data[field] is not None and not _text(data[field]):
            errors.append(field + ": string or null required")
    if not _timestamp(data.get("created_at")):
        errors.append("created_at: ISO-8601 timestamp with timezone required")
    if not _ref(data.get("brand_ref"), "document_id"):
        errors.append("brand_ref: exact document_id/revision required")
    kind = data.get("artifact_kind")
    if kind not in KINDS:
        errors.append("artifact_kind: research, brief, copy or design required")
    if kind != "research" and data.get("scope") != "content":
        errors.append("v1 brief/copy/design require content scope")
    if kind in KINDS and data.get("proposed_next_stage") != NEXT[kind]:
        errors.append("proposed_next_stage: does not match the artifact gate")
    based_on = data.get("based_on")
    if not isinstance(based_on, dict) or any(not _ref(v) for v in based_on.values()):
        errors.append("based_on: mapping to exact handoff_id/revision references required")
    elif kind in KINDS and set(based_on) != set(KINDS[:KINDS.index(kind)]):
        errors.append("based_on: every preceding artifact kind is required, with no extras")
    receipt = data.get("payload_ref")
    if (not isinstance(receipt, dict) or any(not _text(receipt.get(k)) for k in ("document_id", "revision", "receipt_id"))
            or receipt.get("storage_confirmed") is not True or receipt.get("revision") != data.get("artifact_revision")):
        errors.append("payload_ref: confirmed document receipt on artifact_revision required")
    for field in ("checklist", "open_questions", "blockers", "files"):
        if not isinstance(data.get(field), list):
            errors.append(field + ": explicit list required")
    checklist = data.get("checklist", [])
    if not isinstance(checklist, list) or not checklist or any(
        not isinstance(c, dict) or not _text(c.get("criterion")) or type(c.get("passed")) is not bool for c in checklist
    ):
        errors.append("checklist: at least one criterion and boolean passed required")
    payload = data.get("payload")
    if not isinstance(payload, dict):
        errors.append("payload: inline object required")
        return errors
    text_fields = {
        "research": ("summary",),
        "brief": ("audience", "pain", "message", "benefit", "angle", "allowed_promise", "cta", "deadline"),
        "copy": ("message", "hook", "headline", "caption", "cta", "reading_notes", "space_limits"),
        "design": ("direction", "rationale", "reproduction_recipe", "tool_provenance"),
    }
    _required_text(payload, text_fields.get(kind, ()), "payload.", errors)
    list_fields = {
        "research": ("sources", "claims", "insights", "candidate_topics", "gaps", "source_conflicts", "used_references", "rejected_recommendations"),
        "brief": ("allowed_claim_ids", "restrictions", "intended_metrics", "structure"),
        "copy": ("slides", "claim_ids", "requested_variants"),
        "design": ("applied_text", "assets", "prompts", "limitations"),
    }
    for field in list_fields.get(kind, ()):
        if not isinstance(payload.get(field), list):
            errors.append("payload." + field + ": explicit list required")
    if kind == "research":
        source_ids = set()
        sources = payload.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append("payload.sources: at least one source required")
        else:
            for source in sources:
                if not isinstance(source, dict):
                    errors.append("payload.sources: source object required")
                    continue
                _required_text(source, ("source_id", "url", "title", "organization", "source_type", "reliability", "evidence_location"), "source.", errors)
                if source.get("read_confirmed") is not True or not _timestamp(source.get("accessed_at")) or "published_at" not in source:
                    errors.append("source: read_confirmed/accessed_at/published_at (nullable) required")
                if _text(source.get("source_id")):
                    if source["source_id"] in source_ids:
                        errors.append("source: duplicate source_id")
                    source_ids.add(source["source_id"])
        claims = payload.get("claims")
        if isinstance(claims, list):
            ids = set()
            for claim in claims:
                if not isinstance(claim, dict):
                    errors.append("claim: object required")
                    continue
                _required_text(claim, ("claim_id", "statement", "evidence_location", "limits", "validity"), "claim.", errors)
                if claim.get("classification") not in ("fact", "interpretation", "hypothesis"):
                    errors.append("claim.classification: fact/interpretation/hypothesis required")
                refs = claim.get("source_ids")
                if not isinstance(refs, list) or not refs or any(not _text(s) or s not in source_ids for s in refs):
                    errors.append("claim.source_ids: existing source IDs required")
                if _text(claim.get("claim_id")):
                    if claim["claim_id"] in ids:
                        errors.append("claim: duplicate claim_id")
                    ids.add(claim["claim_id"])
        for field in ("insights", "candidate_topics"):
            if not payload.get(field):
                errors.append("payload." + field + ": nonempty list required")
    if kind == "brief":
        for key in ("slide_count", "width", "height"):
            if not _integer(payload.get(key)):
                errors.append("payload." + key + ": positive integer required")
    if kind in ("copy", "design"):
        items = payload.get("slides" if kind == "copy" else "applied_text")
        if not isinstance(items, list) or not items:
            errors.append("payload: nonempty ordered text list required")
        else:
            for i, item in enumerate(items, 1):
                if not isinstance(item, dict) or item.get("slide_index") != i or not _text(item.get("text")):
                    errors.append("payload: slide_index must be consecutive from 1, with exact text")
                elif kind == "copy" and not _text(item.get("narrative_function")):
                    errors.append("payload.slides: narrative_function required")
    if kind == "design" and isinstance(payload.get("assets"), list):
        for asset in payload["assets"]:
            if not isinstance(asset, dict):
                errors.append("payload.assets: object with asset_id/origin/permission required")
            else:
                _required_text(asset, ("asset_id", "origin", "permission"), "asset.", errors)
    files = data.get("files")
    if isinstance(files, list):
        for i, item in enumerate(files):
            _validate_file(item, i, errors)
        if kind == "design":
            finals = [f for f in files if isinstance(f, dict) and f.get("role") == "final"]
            previews = [f for f in files if isinstance(f, dict) and f.get("role") == "preview"]
            if not finals or len(previews) != 1:
                errors.append("design: actual final PNG files and exactly one preview with receipts required; prompts are insufficient")
            if [f.get("slide_index") for f in finals] != list(range(1, len(finals) + 1)):
                errors.append("design: final files must be in consecutive slide order")
            ids = [f.get("attachment_id") for f in files if isinstance(f, dict)]
            if any(not _text(i) for i in ids) or len(set(i for i in ids if _text(i))) != len(ids):
                errors.append("files: attachment IDs must be unique")
    return errors


def validate_handoff(data):
    """Return errors for arbitrary JSON-compatible input, never a type exception."""
    try:
        return _validate_handoff(data)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return ["malformed handoff: " + str(exc)]


def package_snapshot(workflow):
    """Exact decision target; paths are excluded, attachment identities are retained."""
    artifacts = workflow.get("artifacts", {})
    design = artifacts.get("design", {}).get("handoff", {})
    copy = artifacts.get("copy", {}).get("handoff", {}).get("payload", {})
    return {
        "content_id": workflow["content_id"], "brand_ref": deepcopy(workflow["brand_ref"]),
        "artifacts": {k: _artifact_ref(v["handoff"]) for k, v in artifacts.items() if v.get("valid")},
        "files": [{k: f[k] for k in ("attachment_id", "receipt_id", "sha256", "byte_size", "name", "role", "mime_type", "width", "height", "alt_text")}
                  | ({"slide_index": f["slide_index"]} if f["role"] == "final" else {})
                  for f in design.get("files", []) if artifacts.get("design", {}).get("valid")],
        "caption": copy.get("caption"), "cta": copy.get("cta"),
    }


def _fail(condition, message):
    if not condition:
        raise ValueError(message)


def _invalidate(workflow, kind):
    for dependent in KINDS[KINDS.index(kind):]:
        if dependent in workflow["artifacts"]:
            workflow["artifacts"][dependent]["valid"] = False
        workflow["acceptances"].pop(dependent, None)
    workflow["approvals"] = {}
    workflow["stage"] = WORKING[kind]


def _current_inputs(workflow, kind):
    refs = {}
    for upstream in KINDS[:KINDS.index(kind)]:
        item = workflow["artifacts"].get(upstream, {})
        _fail(item.get("valid") and upstream in workflow["acceptances"], f"unaccepted/invalid input: {upstream}")
        _accepted(workflow, upstream)
        _fail(item["handoff"]["brand_ref"] == workflow["brand_ref"], f"stale brand in {upstream}")
        refs[upstream] = _artifact_ref(item["handoff"])
    return refs


def _accepted(workflow, kind):
    h = workflow["artifacts"][kind]["handoff"]
    decision = workflow["acceptances"][kind]
    _fail(decision.get("artifact_ref") == _artifact_ref(h) and decision.get("brand_ref") == workflow["brand_ref"], "stale gate decision: " + kind)
    _fail(decision.get("actor_id") == workflow["actors"][RECEIVERS[kind]], "wrong gate reviewer")


def _transition(workflow, event):
    """Pure transition: new dict or ValueError, without writing state or calling APIs."""
    _fail(isinstance(workflow, dict) and isinstance(event, dict), "workflow/event must be objects")
    w, e = deepcopy(workflow), deepcopy(event)
    _fail(w.get("schema_version") == "1.0" and w.get("stage") in STAGES, "invalid workflow schema/stage")
    _fail(w.get("operational_status") in ("active", "blocked", "cancelled"), "invalid operational_status")
    _fail(type(w.get("revision")) is int and w["revision"] >= 0, "workflow revision must be a nonnegative integer")
    _fail(all(_text(w.get(k)) for k in ("company_id", "brand_id", "content_id")), "workflow identity missing")
    _fail(_ref(w.get("brand_ref"), "document_id"), "approved exact brand_ref required")
    _fail(type(w.get("human_approval_required")) is bool, "human_approval_required boolean required")
    actors = w.get("actors")
    _fail(isinstance(actors, dict) and all(_text(actors.get(k)) for k in ("editorial", "research", "copy", "design", "human")), "five actor IDs required (four agents and the human)")
    _fail(len(set(actors.values())) == len(actors), "producer/reviewer identities must be distinct")
    for field in ("artifacts", "acceptances", "approvals"):
        w.setdefault(field, {})
        _fail(isinstance(w[field], dict), field + " must be an object")
    w.setdefault("history", [])
    _fail(isinstance(w["history"], list), "history must be a list")
    _fail(all(_text(e.get(k)) for k in ("event_id", "operation_id", "type", "actor_id")), "event identity/type required")
    _fail(_timestamp(e.get("created_at")), "event created_at requires timezone")
    _fail(e.get("content_id") == w["content_id"] and e.get("company_id") == w["company_id"], "event targets another company/content")
    for record in w["history"]:
        prior = record["event"]
        if e["event_id"] == prior["event_id"] or e["operation_id"] == prior["operation_id"]:
            _fail(e == prior, "event/operation ID already used with different data")
            return w
        for key in ("decision_id", "correction_id"):
            if key in e:
                _fail(e[key] != prior.get(key), key + " already used")
    _fail(type(e.get("expected_revision")) is int and e["expected_revision"] == w["revision"], "stale expected_revision")
    _fail(e["actor_id"] in actors.values(), "unknown actor_id")
    action = e["type"]
    _fail(w["operational_status"] != "cancelled", "cancelled workflow cannot advance")
    if action == "block":
        _fail(w["operational_status"] == "active" and w["stage"] != "APPROVED", "only active unfinished work can block")
        _fail(all(_text(e.get(k)) for k in ("reason", "resolution_owner", "resume_condition")), "block requires reason/owner/resume condition")
        w["operational_status"] = "blocked"
        w["block"] = {"resume_stage": w["stage"], **{k: e[k] for k in ("reason", "resolution_owner", "resume_condition")}}
    elif action == "resume":
        _fail(w["operational_status"] == "blocked" and e["actor_id"] == actors["editorial"], "only editorial resumes blocked work")
        _fail(_text(e.get("resolution_evidence")), "resolution evidence required")
        _fail(w["stage"] == w["block"]["resume_stage"], "blocked stage changed")
        w["operational_status"] = "active"
        del w["block"]
    elif action == "cancel":
        _fail(e["actor_id"] in (actors["editorial"], actors["human"]) and _text(e.get("reason")), "editorial/human cancellation with reason required")
        w["operational_status"] = "cancelled"
        w["approvals"] = {}
    else:
        _fail(w["operational_status"] == "active", "blocked workflow cannot advance")
        if action == "start_research":
            _fail(w["stage"] == "IDEA" and e["actor_id"] == actors["editorial"], "start_research requires Editorial at IDEA")
            _fail(_text(e.get("request_ref")) and _text(e.get("objective")) and _text(e.get("audience")), "normalized request, objective and audience required")
            w["stage"] = "RESEARCHING"
        elif action == "submit":
            h = e.get("handoff")
            errors = validate_handoff(h)
            _fail(not errors, "; ".join(errors))
            kind = h["artifact_kind"]
            _fail(w["stage"] == WORKING[kind], "submission does not match active stage")
            _fail(e["actor_id"] == h["producer"] == actors[PRODUCERS[kind]], "wrong producer")
            _fail(h["intended_receiver"] == actors[RECEIVERS[kind]], "wrong receiver")
            _fail(all(h[k] == w[k] for k in ("company_id", "brand_id", "brand_ref")), "foreign or stale brand reference")
            _fail(h["scope"] != "content" or h["content_id"] == w["content_id"], "foreign content_id")
            _fail(h["based_on"] == _current_inputs(w, kind), "stale based_on reference")
            for record in w["history"]:
                old = record["event"].get("handoff")
                if old:
                    _fail(old["operation_id"] != h["operation_id"], "handoff operation_id already used")
                    _fail(_artifact_ref(old) != _artifact_ref(h), "artifact revision is immutable; create a new revision")
            if kind in ("copy", "design"):
                brief = w["artifacts"]["brief"]["handoff"]
                _fail(all(h[k] == brief[k] for k in ("channel", "format", "locale", "objective")), "channel/format/locale/objective differ from brief")
                texts = h["payload"]["slides" if kind == "copy" else "applied_text"]
                _fail(len(texts) == brief["payload"]["slide_count"], "slide count differs from brief")
                if kind == "copy":
                    _fail(all(c in brief["payload"]["allowed_claim_ids"] for c in h["payload"]["claim_ids"]), "copy uses unapproved claim")
                else:
                    copy = w["artifacts"]["copy"]["handoff"]["payload"]
                    _fail(texts == [{"slide_index": s["slide_index"], "text": s["text"]} for s in copy["slides"]], "design text differs from accepted copy")
                    finals = [f for f in h["files"] if f["role"] == "final"]
                    _fail(len(finals) == len(texts), "final file count differs from copy")
                    _fail(all((f["width"], f["height"]) == (brief["payload"]["width"], brief["payload"]["height"]) for f in finals), "export dimensions differ from brief")
            if kind == "brief":
                claims = {c["claim_id"] for c in w["artifacts"]["research"]["handoff"]["payload"]["claims"]}
                _fail(all(c in claims for c in h["payload"]["allowed_claim_ids"]), "brief references unknown claim")
            _invalidate(w, kind)
            w["artifacts"][kind] = {"handoff": h, "valid": True}
            w["stage"] = READY[kind]
        elif action == "accept":
            kind = e.get("artifact_kind")
            _fail(kind in KINDS and w["stage"] == READY[kind], "acceptance requires matching READY stage")
            _fail(e["actor_id"] == actors[RECEIVERS[kind]], "only intended receiver accepts")
            h = w["artifacts"][kind]["handoff"]
            _fail(_text(e.get("decision_id")) and _text(e.get("reason")), "decision identity/reason required")
            _fail(e.get("artifact_ref") == _artifact_ref(h) and e.get("brand_ref") == w["brand_ref"] == h["brand_ref"], "acceptance targets stale revision/brand")
            _fail(h["based_on"] == _current_inputs(w, kind), "stale input at acceptance")
            _fail(not h["blockers"] and all(c["passed"] for c in h["checklist"]), "blockers/failed checklist prevent acceptance")
            _fail(not validate_handoff(h), "artifact no longer passes validation (including files)")
            w["acceptances"][kind] = e
            w["stage"] = NEXT[kind]
        elif action == "approve":
            _fail(w["stage"] == "REVIEW", "final approval requires REVIEW")
            role = "editorial" if e["actor_id"] == actors["editorial"] else "human"
            _fail(e["actor_id"] == actors[role], "only editorial or human can approve")
            _fail(role != "human" or "editorial" in w["approvals"], "editorial decision must precede human approval")
            _fail(_text(e.get("decision_id")) and _text(e.get("reason")), "decision identity/reason required")
            _fail(e.get("package") == package_snapshot(w), "approval targets stale/incomplete package")
            for kind in KINDS:
                item = w["artifacts"].get(kind, {})
                _fail(item.get("valid") and kind in w["acceptances"], "every gate must be accepted")
                _accepted(w, kind)
                h = item["handoff"]
                _fail(h["brand_ref"] == w["brand_ref"] and h["based_on"] == _current_inputs(w, kind), "stale chain")
                _fail(not validate_handoff(h) and not h["blockers"] and all(c["passed"] for c in h["checklist"]), "artifact no longer eligible")
            _fail(all(d.get("package") == package_snapshot(w) for d in w["approvals"].values()), "earlier approval targets a different package")
            w["approvals"][role] = e
            if "editorial" in w["approvals"] and (not w["human_approval_required"] or "human" in w["approvals"]):
                w["stage"] = "APPROVED"
        elif action == "reject":
            kind = e.get("cause")
            _fail(kind in KINDS and kind in w["artifacts"], "causal artifact required")
            _fail(e["actor_id"] == actors["editorial"], "only editorial routes corrections")
            _fail(e.get("reviewed_package") == package_snapshot(w), "feedback targets stale package")
            _fail(all(_text(e.get(k)) for k in ("correction_id", "criterion", "location", "evidence", "change_requested", "acceptance_condition", "priority", "deadline")), "structured correction fields required")
            _fail(e.get("responsible_actor_id") == actors[PRODUCERS[kind]], "correction owner must match causal stage")
            affected = [k for k in KINDS[KINDS.index(kind):] if k in w["artifacts"]]
            _fail(e.get("affected_artifacts") == affected, "explicit affected downstream artifact list required")
            _invalidate(w, kind)
        elif action == "brand_change":
            _fail(e["actor_id"] == actors["human"], "brand changes require the configured human identity")
            _fail(e.get("previous_brand_ref") == w["brand_ref"], "stale previous brand")
            _fail(_ref(e.get("brand_ref"), "document_id") and e["brand_ref"] != w["brand_ref"], "new exact brand revision required")
            _fail(_text(e.get("decision_id")) and _text(e.get("publication_receipt_id")) and _text(e.get("impact_reason")), "brand publication receipt/decision/impact analysis required")
            w["brand_ref"] = e["brand_ref"]
            _invalidate(w, "research")
        else:
            raise ValueError("unsupported event type: " + action)
    w["revision"] += 1
    w["history"].append({"revision": w["revision"], "event": e})
    return w


def transition(workflow, event):
    """Return a copied state, or ValueError; malformed JSON state never leaks KeyError."""
    try:
        return _transition(workflow, event)
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
        raise ValueError("malformed workflow/event: " + str(exc)) from exc


def _main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "transition", "snapshot"))
    parser.add_argument("input", type=Path)
    parser.add_argument("event", type=Path, nargs="?")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text())
        if args.command == "validate":
            result = validate_handoff(data)
            print(json.dumps({"errors": result}, ensure_ascii=False, indent=2))
            return bool(result)
        if args.command == "snapshot":
            result = package_snapshot(data)
        else:
            if args.event is None:
                parser.error("transition requires an event JSON file")
            result = transition(data, json.loads(args.event.read_text()))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
