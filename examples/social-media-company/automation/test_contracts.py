"""Deterministic fixtures; these are not real Paperclip upload receipts."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from contracts import KINDS, NEXT, PRODUCERS, RECEIVERS, package_snapshot, transition, validate_handoff


NOW = "2026-10-06T15:00:00-03:00"


def png(width=2, height=2):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    raw = b"".join(b"\0" + b"\xff\xff\xff" * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "slide.png"
        self.path.write_bytes(png())
        self.serial = 0
        self.w = {
            "schema_version": "1.0", "company_id": "company-1", "brand_id": "brand-1", "content_id": "content-1",
            "brand_ref": {"document_id": "brand-context-1", "revision": "brand-r1"},
            "actors": {k: "actor-" + k for k in ("editorial", "research", "copy", "design", "human")},
            "human_approval_required": False, "revision": 0, "stage": "IDEA", "operational_status": "active",
            "artifacts": {}, "acceptances": {}, "approvals": {}, "history": [],
        }

    def event(self, action, actor="editorial", **fields):
        self.serial += 1
        return {
            "event_id": f"event-{self.serial}", "operation_id": f"op-{self.serial}", "type": action,
            "company_id": self.w["company_id"], "content_id": self.w["content_id"],
            "actor_id": self.w["actors"][actor], "created_at": NOW, "expected_revision": self.w["revision"], **fields,
        }

    def apply(self, action, actor="editorial", **fields):
        self.w = transition(self.w, self.event(action, actor, **fields))

    def handoff(self, kind):
        self.serial += 1
        h = {
            "schema_version": "1.0", "handoff_id": f"handoff-{kind}", "operation_id": f"handoff-op-{self.serial}",
            "artifact_kind": kind, "artifact_revision": f"r{self.serial}", "created_at": NOW,
            "scope": "content", "company_id": self.w["company_id"], "brand_id": self.w["brand_id"], "content_id": self.w["content_id"],
            "source_issue_id": f"issue-{kind}", "target_issue_id": "issue-content", "producer": self.w["actors"][PRODUCERS[kind]],
            "intended_receiver": self.w["actors"][RECEIVERS[kind]], "brand_ref": deepcopy(self.w["brand_ref"]),
            "based_on": {k: {"handoff_id": self.w["artifacts"][k]["handoff"]["handoff_id"], "revision": self.w["artifacts"][k]["handoff"]["artifact_revision"]} for k in KINDS[:KINDS.index(kind)]},
            "channel": "instagram", "format": "static", "locale": "pt-BR", "objective": "Ensinar conceito",
            "checklist": [{"criterion": "manual fixture review", "passed": True}], "open_questions": [], "blockers": [], "files": [],
            "proposed_next_stage": NEXT[kind],
        }
        h["payload_ref"] = {"document_id": f"doc-{kind}", "revision": h["artifact_revision"], "receipt_id": f"doc-receipt-{self.serial}", "storage_confirmed": True}
        h["payload"] = {
            "research": {
                "summary": "Dossiê de teste", "sources": [{"source_id": "s1", "url": "https://example.org/source", "title": "Fonte",
                    "organization": "Exemplo", "published_at": None, "accessed_at": NOW, "source_type": "primary",
                    "reliability": "Fonte primária", "evidence_location": "parágrafo 1", "read_confirmed": True}],
                "claims": [{"claim_id": "c1", "statement": "Fato de teste", "source_ids": ["s1"], "evidence_location": "parágrafo 1",
                    "classification": "fact", "limits": "Só fixture", "validity": "Somente este teste"}],
                "insights": ["Insight"], "candidate_topics": ["Tema"], "gaps": [], "source_conflicts": [], "used_references": [], "rejected_recommendations": [],
            },
            "brief": {"audience": "Leitores", "pain": "Dúvida", "message": "Mensagem", "benefit": "Entendimento", "angle": "Didático",
                "allowed_promise": "Explicação", "cta": "Leia", "deadline": NOW, "allowed_claim_ids": ["c1"], "restrictions": [],
                "intended_metrics": [], "structure": ["Mensagem"], "slide_count": 1, "width": 2, "height": 2},
            "copy": {"message": "Mensagem", "hook": "Pergunta", "headline": "Título", "caption": "Legenda", "cta": "Leia",
                "reading_notes": "Ênfase no título", "space_limits": "Uma frase", "slides": [{"slide_index": 1, "text": "Texto exato", "narrative_function": "Mensagem"}],
                "claim_ids": ["c1"], "requested_variants": []},
            "design": {"direction": "Composição simples", "rationale": "Legibilidade", "reproduction_recipe": "Fixture PNG stdlib",
                "tool_provenance": "Python stdlib; nenhum gerador", "applied_text": [{"slide_index": 1, "text": "Texto exato"}], "assets": [], "prompts": [], "limitations": []},
        }[kind]
        if kind == "design":
            blob = self.path.read_bytes()
            file = {"attachment_id": "final-1", "receipt_id": "receipt-final-1", "name": "slide.png", "local_path": str(self.path),
                    "storage_confirmed": True, "mime_type": "image/png", "width": 2, "height": 2, "byte_size": len(blob),
                    "sha256": hashlib.sha256(blob).hexdigest(), "role": "final", "slide_index": 1, "alt_text": "Fixture branca"}
            preview = {**file, "role": "preview", "attachment_id": "preview-1", "receipt_id": "receipt-preview-1"}
            del preview["slide_index"]
            h["files"] = [file, preview]
        return h

    def accept(self, kind):
        h = self.w["artifacts"][kind]["handoff"]
        self.apply("accept", RECEIVERS[kind], artifact_kind=kind, decision_id=f"decision-{self.serial}", reason="Inspecionado",
                   artifact_ref={"handoff_id": h["handoff_id"], "revision": h["artifact_revision"]}, brand_ref=deepcopy(self.w["brand_ref"]))

    def reach(self, kind="design"):
        if self.w["stage"] == "IDEA":
            self.apply("start_research", request_ref="request-1", objective="Ensinar", audience="Leitores")
        for k in KINDS[:KINDS.index(kind) + 1]:
            self.apply("submit", PRODUCERS[k], handoff=self.handoff(k))
            self.accept(k)

    def rejection(self, kind):
        return self.event("reject", cause=kind, reviewed_package=package_snapshot(self.w), correction_id=f"correction-{self.serial}",
                          criterion="Qualidade", location="slide 1", evidence="Problema demonstrado", change_requested="Corrigir",
                          acceptance_condition="Problema ausente", priority="normal", deadline=NOW,
                          responsible_actor_id=self.w["actors"][PRODUCERS[kind]],
                          affected_artifacts=[k for k in KINDS[KINDS.index(kind):] if k in self.w["artifacts"]])

    def test_manual_post_reaches_approved_with_every_gate(self):
        self.reach()
        self.assertEqual(self.w["stage"], "REVIEW")
        before = deepcopy(self.w)
        self.apply("approve", decision_id="final-editorial", reason="Todos os critérios atendidos", package=package_snapshot(self.w))
        self.assertEqual(self.w["stage"], "APPROVED")
        self.assertEqual(before["stage"], "REVIEW")
        self.assertEqual(set(self.w["acceptances"]), set(KINDS))

    def test_human_gate_needs_same_current_package(self):
        self.w["human_approval_required"] = True
        self.reach()
        self.apply("approve", decision_id="ed-final", reason="Revisado", package=package_snapshot(self.w))
        self.assertEqual(self.w["stage"], "REVIEW")
        old = package_snapshot(self.w)
        old["brand_ref"]["revision"] = "stale"
        with self.assertRaisesRegex(ValueError, "stale"):
            transition(self.w, self.event("approve", "human", decision_id="human-final", reason="Aprovado", package=old))
        self.apply("approve", "human", decision_id="human-final", reason="Aprovado", package=package_snapshot(self.w))
        self.assertEqual(self.w["stage"], "APPROVED")

    def test_visual_rejection_preserves_upstream(self):
        self.reach()
        upstream = deepcopy({k: self.w["acceptances"][k] for k in KINDS[:-1]})
        self.apply("approve", decision_id="ed-final", reason="Revisado", package=package_snapshot(self.w))
        self.w = transition(self.w, self.rejection("design"))
        self.assertEqual(self.w["stage"], "DESIGN_IN_PROGRESS")
        self.assertEqual(self.w["acceptances"], upstream)
        self.assertEqual(self.w["approvals"], {})
        self.assertFalse(self.w["artifacts"]["design"]["valid"])

    def test_bad_source_returns_to_research_and_invalidates_chain(self):
        self.reach()
        self.w = transition(self.w, self.rejection("research"))
        self.assertEqual(self.w["stage"], "RESEARCHING")
        self.assertEqual(self.w["acceptances"], {})
        self.assertTrue(all(not item["valid"] for item in self.w["artifacts"].values()))

    def test_copy_correction_invalidates_design_and_final_approvals(self):
        self.reach()
        self.w = transition(self.w, self.rejection("copy"))
        self.assertEqual(self.w["stage"], "COPY_IN_PROGRESS")
        self.assertEqual(set(self.w["acceptances"]), {"research", "brief"})
        stale_design = deepcopy(self.w["artifacts"]["design"]["handoff"])
        fresh = self.handoff("copy")
        fresh["payload"]["slides"][0]["text"] = "Texto corrigido"
        self.apply("submit", "copy", handoff=fresh)
        self.accept("copy")
        with self.assertRaisesRegex(ValueError, "stale based_on"):
            transition(self.w, self.event("submit", "design", handoff=stale_design))

    def test_brand_revision_change_is_explicit_and_invalidates_all(self):
        self.reach()
        self.apply("brand_change", "human", previous_brand_ref=deepcopy(self.w["brand_ref"]),
                   brand_ref={"document_id": "brand-context-1", "revision": "brand-r2"}, decision_id="brand-decision",
                   publication_receipt_id="brand-receipt", impact_reason="Mudança de posicionamento afeta toda a cadeia")
        self.assertEqual(self.w["stage"], "RESEARCHING")
        self.assertEqual(self.w["acceptances"], {})
        self.assertEqual(self.w["brand_ref"]["revision"], "brand-r2")
        self.assertEqual(self.w["artifacts"]["research"]["handoff"]["brand_ref"]["revision"], "brand-r1")

    def test_duplicate_event_idempotent_conflicting_reuse_rejected(self):
        event = self.event("start_research", request_ref="request-1", objective="Ensinar", audience="Leitores")
        result = transition(self.w, event)
        self.assertEqual(transition(result, event), result)
        event["objective"] = "Outra coisa"
        with self.assertRaisesRegex(ValueError, "already used"):
            transition(result, event)

    def test_event_cas_and_foreign_content_are_rejected(self):
        e = self.event("start_research", request_ref="request", objective="Objetivo", audience="Público")
        e["expected_revision"] = 99
        with self.assertRaisesRegex(ValueError, "stale"):
            transition(self.w, e)
        e["expected_revision"] = 0
        e["content_id"] = "other"
        with self.assertRaisesRegex(ValueError, "another"):
            transition(self.w, e)

    def test_block_resume_and_cancel(self):
        self.reach("copy")
        self.apply("block", "design", reason="Gerador indisponível", resolution_owner="operator", resume_condition="Imagem gerada")
        self.assertEqual(self.w["stage"], "DESIGN_IN_PROGRESS")
        with self.assertRaisesRegex(ValueError, "blocked"):
            transition(self.w, self.event("submit", "design", handoff=self.handoff("design")))
        self.apply("resume", resolution_evidence="Ferramenta testada e arquivo produzido")
        self.assertEqual(self.w["operational_status"], "active")
        self.apply("cancel", reason="Pedido cancelado")
        with self.assertRaisesRegex(ValueError, "cancelled"):
            transition(self.w, self.event("resume", resolution_evidence="Não deve retomar"))

    def test_prompts_missing_files_or_fake_receipt_fail(self):
        self.reach("copy")
        h = self.handoff("design")
        self.assertEqual(validate_handoff(h), [])
        h["files"] = []
        h["payload"]["prompts"] = ["Crie uma imagem bonita"]
        self.assertTrue(any("prompts" in e for e in validate_handoff(h)))
        h = self.handoff("design")
        h["files"][0]["storage_confirmed"] = False
        self.assertTrue(any("storage_confirmed" in e for e in validate_handoff(h)))
        h = self.handoff("design")
        self.path.unlink()
        self.assertTrue(any("unavailable" in e for e in validate_handoff(h)))

    def test_changed_file_bytes_or_dimensions_fail(self):
        self.reach("copy")
        h = self.handoff("design")
        self.path.write_bytes(png(3, 2))
        errors = validate_handoff(h)
        self.assertTrue(any("sha256" in e for e in errors))
        self.assertTrue(any("dimensions" in e for e in errors))

    def test_design_must_preserve_exact_copy(self):
        self.reach("copy")
        h = self.handoff("design")
        h["payload"]["applied_text"][0]["text"] = "Texto encurtado sem revisão"
        with self.assertRaisesRegex(ValueError, "text differs"):
            transition(self.w, self.event("submit", "design", handoff=h))

    def test_carousel_order_and_count_checked(self):
        self.reach("copy")
        h = self.handoff("design")
        h["payload"]["applied_text"][0]["slide_index"] = 2
        self.assertTrue(any("consecutive" in e for e in validate_handoff(h)))
        h = self.handoff("design")
        h["files"][0]["slide_index"] = 3
        self.assertTrue(any("consecutive" in e for e in validate_handoff(h)))

    def test_required_fields_and_unknown_sources_rejected(self):
        h = self.handoff("research")
        self.assertEqual(validate_handoff(h), [])
        for field in ("scope", "content_id", "payload_ref", "brand_ref", "checklist", "blockers", "files", "artifact_revision"):
            with self.subTest(field=field):
                bad = deepcopy(h)
                del bad[field]
                self.assertTrue(validate_handoff(bad))
        h["payload"]["claims"][0]["source_ids"] = ["unknown"]
        self.assertTrue(any("source_ids" in e for e in validate_handoff(h)))

    def test_scope_does_not_invent_content_id_for_shared_research(self):
        h = self.handoff("research")
        h.update(scope="brand_intelligence", research_batch_id="batch-1", channel=None, format=None)
        del h["content_id"]
        self.assertEqual(validate_handoff(h), [])

    def test_old_gate_revision_and_self_acceptance_rejected(self):
        self.apply("start_research", request_ref="request", objective="Objetivo", audience="Público")
        h = self.handoff("research")
        self.apply("submit", "research", handoff=h)
        e = self.event("accept", artifact_kind="research", decision_id="decision", reason="Revisado",
                       artifact_ref={"handoff_id": h["handoff_id"], "revision": "old"}, brand_ref=self.w["brand_ref"])
        with self.assertRaisesRegex(ValueError, "stale"):
            transition(self.w, e)
        e["artifact_ref"]["revision"] = h["artifact_revision"]
        e["actor_id"] = self.w["actors"]["research"]
        with self.assertRaisesRegex(ValueError, "receiver"):
            transition(self.w, e)

    def test_blockers_and_failed_checklist_stop_gate(self):
        self.apply("start_research", request_ref="request", objective="Objetivo", audience="Público")
        h = self.handoff("research")
        h["blockers"] = ["Fato comercial desconhecido"]
        self.apply("submit", "research", handoff=h)
        with self.assertRaisesRegex(ValueError, "blockers"):
            self.accept("research")

    def test_changed_bytes_between_review_and_approval_fail(self):
        self.reach()
        before = deepcopy(self.w)
        self.path.write_bytes(b"invalid")
        with self.assertRaisesRegex(ValueError, "eligible"):
            transition(self.w, self.event("approve", decision_id="final", reason="Revisado", package=package_snapshot(self.w)))
        self.assertEqual(self.w, before)

    def test_malformed_json_input_is_reported_without_type_errors(self):
        for value in (None, [], "text", {}, {"scope": []}, {"artifact_kind": {}}, {"files": [None]}):
            with self.subTest(value=value):
                self.assertTrue(validate_handoff(value))
        with self.assertRaises(ValueError):
            transition({}, {})

    def test_human_cannot_approve_before_editorial(self):
        self.w["human_approval_required"] = True
        self.reach()
        with self.assertRaisesRegex(ValueError, "precede"):
            transition(self.w, self.event("approve", "human", decision_id="human", reason="Aprovado", package=package_snapshot(self.w)))

    def test_two_slide_carousel_preserves_order_through_approval(self):
        self.reach("research")
        brief = self.handoff("brief")
        brief["format"] = "carousel"
        brief["payload"]["slide_count"] = 2
        self.apply("submit", handoff=brief)
        self.accept("brief")
        copy = self.handoff("copy")
        copy["format"] = "carousel"
        copy["payload"]["slides"].append({"slide_index": 2, "text": "Segundo slide", "narrative_function": "Fechamento"})
        self.apply("submit", "copy", handoff=copy)
        self.accept("copy")
        design = self.handoff("design")
        design["format"] = "carousel"
        design["payload"]["applied_text"].append({"slide_index": 2, "text": "Segundo slide"})
        second = {**design["files"][0], "attachment_id": "final-2", "receipt_id": "receipt-final-2", "slide_index": 2}
        design["files"].insert(1, second)
        self.apply("submit", "design", handoff=design)
        self.accept("design")
        self.apply("approve", decision_id="final", reason="Revisado", package=package_snapshot(self.w))
        self.assertEqual(self.w["stage"], "APPROVED")
        self.assertEqual([f["slide_index"] for f in package_snapshot(self.w)["files"] if f["role"] == "final"], [1, 2])

    def test_brief_rejection_preserves_only_research(self):
        self.reach()
        self.w = transition(self.w, self.rejection("brief"))
        self.assertEqual(self.w["stage"], "CURATING")
        self.assertEqual(set(self.w["acceptances"]), {"research"})

    def test_corrected_design_requires_new_revision_and_gate(self):
        self.reach()
        old = deepcopy(self.w["artifacts"]["design"]["handoff"])
        self.w = transition(self.w, self.rejection("design"))
        with self.assertRaisesRegex(ValueError, "already used|immutable"):
            transition(self.w, self.event("submit", "design", handoff=old))
        fresh = self.handoff("design")
        self.apply("submit", "design", handoff=fresh)
        self.assertEqual(self.w["stage"], "DESIGN_READY")
        self.assertNotIn("design", self.w["acceptances"])
        self.accept("design")
        self.apply("approve", decision_id="final-new", reason="Correção inspecionada", package=package_snapshot(self.w))
        self.assertEqual(self.w["stage"], "APPROVED")

    def test_forged_acceptance_or_stale_editorial_package_is_not_reused(self):
        self.w["human_approval_required"] = True
        self.reach()
        bad = deepcopy(self.w)
        bad["acceptances"]["copy"]["artifact_ref"]["revision"] = "old"
        with self.assertRaisesRegex(ValueError, "stale gate"):
            transition(bad, self.event("approve", decision_id="ed", reason="Review", package=package_snapshot(bad)))
        self.apply("approve", decision_id="ed", reason="Review", package=package_snapshot(self.w))
        self.w["approvals"]["editorial"]["package"]["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "earlier approval"):
            transition(self.w, self.event("approve", "human", decision_id="human", reason="Review", package=package_snapshot(self.w)))


if __name__ == "__main__":
    unittest.main()
