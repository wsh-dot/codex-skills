"""Meaningful offline workflow tests; semantic judgments are explicit fixtures, not model tests."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_loop as loop


class ReviewLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("REVIEW_LOOP_TEST_TMP"))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text("对照规范和验收解释计算，保留冲突；只读，不修改代码。", encoding="utf-8")
        self.a = self.root / "规范.md"
        self.b = self.root / "验收.md"
        self.a.write_text("现行规范\n关联采用实物量。\n不得修改权威文件。\n", encoding="utf-8")
        self.b.write_text("现行验收\n人工改量后关联随主定额量变化。\n", encoding="utf-8")
        self.plan = {
            "scope": "只修正文稿", "authority_policy": "两份来源冲突，不自行裁决",
            "max_rounds": 6,
            "sources": [
                {"id": "S1", "path": str(self.a), "role": "authority", "purpose": "核对基数",
                 "version": "当前读取", "order": 1, "ranges": []},
                {"id": "S2", "path": str(self.b), "role": "acceptance", "purpose": "核对预期",
                 "version": "当前读取", "order": 2, "ranges": []}],
            "criteria": [{"id": "R1", "requirement": "说明双方口径并保留冲突",
                          "prompt_quote": "保留冲突", "source_ids": ["S1", "S2"]}],
            "conflicts": [{"id": "K1", "description": "实物量与人工主量冲突",
                           "source_ids": ["S1", "S2"], "policy": "preserve"}],
            "prior_findings": [{"id": "P1", "criterion_id": "R1", "problem": "调用链暗中选择主量"}]
        }
        self.run = self.root / "run"
        self.good = ("规范采用实物量〔S1:L2〕；验收要求人工改量后关联随主定额量变化〔S2:L2〕。\n"
                     "二者冲突，本文不决定人工改量后的关联基数，也不指定重算公式。\n")
        self.bad = "关联基数冲突单列，不裁定。\n人工修改后依据生效成员主量重新累加计算关联量。\n"

    def start(self, draft=None):
        path = self.root / "plan.json"
        loop.write_json(path, self.plan)
        loop.prepare(self.prompt, path, self.run)
        if draft is not None:
            self.submit_draft(draft)

    def submit_draft(self, text):
        loop.packet(self.run)
        incoming = self.run / "incoming-draft.md"
        incoming.write_text(text, encoding="utf-8")
        return loop.submit(self.run, "draft", incoming)

    def citations(self):
        return [{"source_id": "S1", "start_line": 2, "end_line": 2, "quote": "关联采用实物量。"},
                {"source_id": "S2", "start_line": 2, "end_line": 2,
                 "quote": "人工改量后关联随主定额量变化。"}]

    def review(self, pass_review=True):
        request = loop.packet(self.run)
        state, contract = loop.state_read(self.run)
        draft = (self.run / state["draft"]).read_text(encoding="utf-8")
        citations = self.citations() if contract["sources"] else []
        return {
            "request_id": request["request_id"], "draft_sha256": state["draft_sha256"],
            "coverage": [{"criterion_id": c["id"], "status": "PASS" if pass_review else "FAIL",
                          "reason": "逐项核验实际正文和来源", "draft_quotes": [draft.strip()],
                          "citations": citations} for c in contract["plan"]["criteria"]],
            "cross_checks": [{"id": name, "status": "PASS", "reason": "全文检查已完成"}
                             for name in loop.CROSS_CHECKS],
            "findings": [] if pass_review else [
                {"id": "F1", "criterion_id": "R1",
                 "problem": "调用链选择主量，与保留冲突声明矛盾", "draft_quote": "依据生效成员主量",
                 "citations": citations, "fix": "改为不确定重算基数并保留双方来源",
                 "needs_user_decision": False}],
            "prior_findings": [{"id": f["id"], "status": "FIXED" if pass_review else "OPEN",
                                "reason": "核对实际正文", "draft_quotes": [draft.strip()],
                                "citations": citations} for f in state["ledger"]],
            "conflicts": [{"id": c["id"], "status": "PRESERVED" if pass_review else "DECIDED",
                           "reason": "检查调用链是否选边", "draft_quotes": [draft.strip()],
                           "citations": citations} for c in contract["plan"].get("conflicts", [])],
            "summary": "本轮审查结论"
        }

    def submit_review(self, report):
        incoming = self.run / "incoming-review.json"
        loop.write_json(incoming, report)
        return loop.submit(self.run, "review", incoming)

    def test_two_passes_publish_exact_bytes(self):
        self.start(self.good)
        state = self.submit_review(self.review())
        self.assertEqual(state["status"], "VERIFY")
        self.assertFalse((self.run / "final.md").exists())
        state = self.submit_review(self.review())
        self.assertEqual(state["status"], "PASSED")
        self.assertEqual((self.run / "final.md").read_bytes(), (self.run / "incoming-draft.md").read_bytes())
        self.assertEqual(loop.read_json(self.run / "approval.json")["clean_passes"], 2)

    def test_conflict_revision_loop_and_regression_ledger(self):
        self.start(self.bad)
        state = self.submit_review(self.review(False))
        self.assertEqual(state["status"], "REVISE")
        self.assertFalse((self.run / "final.md").exists())
        self.assertIn("依据生效成员主量", (self.run / "feedback.md").read_text(encoding="utf-8"))
        self.submit_draft(self.good)
        report = self.review()
        self.assertEqual({f["id"] for f in report["prior_findings"]}, {"P1", "F1"})
        self.submit_review(report)
        state = self.submit_review(self.review())
        self.assertEqual(state["round"], 2)
        self.assertEqual(state["status"], "PASSED")

    def test_stale_review_rejected(self):
        self.start(self.good)
        report = self.review()
        report["request_id"] = "old-request"
        with self.assertRaises(loop.GateError):
            self.submit_review(report)
        self.assertFalse((self.run / "final.md").exists())

    def test_wrong_draft_hash_rejected(self):
        self.start(self.good)
        report = self.review()
        report["draft_sha256"] = "0" * 64
        with self.assertRaises(loop.GateError):
            self.submit_review(report)

    def test_fabricated_quote_rejected(self):
        self.start(self.good)
        report = self.review()
        report["coverage"][0]["citations"][0]["quote"] = "来源并没有说过这句话"
        with self.assertRaises(loop.GateError):
            self.submit_review(report)

    def test_wrong_line_rejected(self):
        self.start(self.good)
        report = self.review()
        report["coverage"][0]["citations"][0]["start_line"] = 1
        report["coverage"][0]["citations"][0]["end_line"] = 1
        with self.assertRaises(loop.GateError):
            self.submit_review(report)

    def test_missing_criterion_rejected(self):
        self.start(self.good)
        report = self.review()
        report["coverage"] = []
        with self.assertRaises(loop.GateError):
            self.submit_review(report)

    def test_missing_prior_finding_rejected(self):
        self.start(self.good)
        report = self.review()
        report["prior_findings"] = []
        with self.assertRaises(loop.GateError):
            self.submit_review(report)

    def test_self_claim_without_draft_evidence_rejected(self):
        self.start(self.good)
        report = self.review()
        report["coverage"][0]["draft_quotes"] = []
        with self.assertRaises(loop.GateError):
            self.submit_review(report)

    def test_missing_one_side_of_conflict_rejected(self):
        self.start(self.good)
        report = self.review()
        report["conflicts"][0]["citations"] = self.citations()[:1]
        with self.assertRaises(loop.GateError):
            self.submit_review(report)

    def test_source_changed_stops_publication(self):
        self.start(self.good)
        report = self.review()
        self.a.write_text("已改变的规范", encoding="utf-8")
        with self.assertRaises(loop.GateError):
            self.submit_review(report)
        self.assertFalse((self.run / "final.md").exists())

    def test_frozen_plan_tampering_rejected(self):
        self.start(self.good)
        contract = loop.read_json(self.run / "contract.json")
        contract["plan"]["criteria"] = []
        loop.write_json(self.run / "contract.json", contract)
        with self.assertRaises(loop.GateError):
            loop.packet(self.run)

    def test_draft_edit_outside_submit_rejected(self):
        self.start(self.good)
        state, _ = loop.state_read(self.run)
        (self.run / state["draft"]).write_text("未审核改写", encoding="utf-8")
        with self.assertRaises(loop.GateError):
            loop.packet(self.run)

    def test_max_rounds_is_not_success(self):
        self.plan["max_rounds"] = 1
        self.start(self.bad)
        state = self.submit_review(self.review(False))
        self.assertEqual(state["status"], "LIMIT_REACHED")
        self.assertFalse((self.run / "final.md").exists())

    def test_unchanged_revision_is_stalled(self):
        self.start(self.bad)
        self.submit_review(self.review(False))
        state = self.submit_draft(self.bad)
        self.assertEqual(state["status"], "STALLED")
        self.assertFalse((self.run / "final.md").exists())

    def test_required_human_decision_blocks(self):
        self.plan["conflicts"][0]["policy"] = "block"
        self.start(self.good)
        state = self.submit_review(self.review())
        self.assertEqual(state["status"], "BLOCKED")
        self.assertFalse((self.run / "final.md").exists())

    def test_new_issue_needing_decision_blocks(self):
        self.start(self.bad)
        report = self.review(False)
        report["findings"][0]["needs_user_decision"] = True
        state = self.submit_review(report)
        self.assertEqual(state["status"], "BLOCKED")

    def test_claimed_pass_cannot_hide_new_findings(self):
        self.start(self.bad)
        report = self.review()
        finding = self.review(False)["findings"][0]
        report["findings"] = [finding]
        state = self.submit_review(report)
        self.assertEqual(state["status"], "REVISE")

    def test_bad_inline_reference_not_passed(self):
        self.start(self.good + "还有〔S1:L999〕。\n")
        state = self.submit_review(self.review())
        self.assertEqual(state["status"], "REVISE")
        self.assertIn("引用越界", (self.run / "feedback.md").read_text(encoding="utf-8"))

    def test_literal_check_is_a_gate_not_semantic_proof(self):
        self.plan["literal_checks"] = [{"criterion_id": "R1", "kind": "not_contains",
                                        "text": "禁止词"}]
        self.start(self.good + "禁止词")
        self.assertEqual(self.submit_review(self.review())["status"], "REVISE")

    def test_excerpt_cannot_cite_unread_lines(self):
        self.plan["sources"][0]["ranges"] = [[1, 1]]
        self.start(self.good)
        with self.assertRaises(loop.GateError):
            self.submit_review(self.review())

    def test_excerpt_read_receipt(self):
        self.plan["sources"][0]["ranges"] = [[2, 2]]
        self.start(self.good)
        _, contract = loop.state_read(self.run)
        self.assertEqual(contract["sources"][0]["coverage"], "excerpt")
        self.assertEqual(contract["sources"][0]["selected_lines"], 1)
        self.assertIn("L2-L2", (self.run / "reading-guide.md").read_text(encoding="utf-8"))

    def test_different_prompt_uses_different_criteria_without_business_sources(self):
        self.prompt.write_text("写一句温暖的生日祝福，不出现广告。", encoding="utf-8")
        self.plan = {"scope": "创作文稿", "authority_policy": "仅用户提示词",
                     "sources": [], "criteria": [
                         {"id": "W1", "requirement": "生日祝福温暖且无广告",
                          "prompt_quote": "温暖的生日祝福", "source_ids": []}],
                     "conflicts": [], "prior_findings": []}
        self.start("愿你生日快乐，每一天都有人与你分享喜悦。\n")
        packet = loop.packet(self.run)
        instructions = Path(packet["path"]).read_text(encoding="utf-8")
        self.assertNotIn("关联基数", instructions)
        self.submit_review(self.review())
        self.assertEqual(self.submit_review(self.review())["status"], "PASSED")

    def test_unrelated_prompt_quote_rejected_before_run_creation(self):
        self.plan["criteria"][0]["prompt_quote"] = "不存在的用户要求"
        with self.assertRaises(loop.GateError):
            self.start()
        self.assertFalse(self.run.exists())

    def test_protected_inputs_unchanged_after_full_loop(self):
        before = {str(p): p.read_bytes() for p in [self.a, self.b, self.prompt]}
        self.start(self.good)
        self.submit_review(self.review())
        self.submit_review(self.review())
        for path, data in before.items():
            self.assertEqual(Path(path).read_bytes(), data)

    def test_existing_run_never_overwritten(self):
        self.start()
        with self.assertRaises(loop.GateError):
            loop.prepare(self.prompt, self.root / "plan.json", self.run)

    def test_discover_reads_no_file_content_or_secret_files(self):
        secret = self.root / ".env.plan"
        secret.write_text("not to be inventoried", encoding="utf-8")
        result = loop.discover(self.root, "规范 验收 .env", 20)
        self.assertEqual({Path(c["path"]).name for c in result["candidates"]}, {"规范.md", "验收.md"})
        self.assertTrue(all("unread" in c["note"] for c in result["candidates"]))

    def test_cli_help_and_real_prepare_packet(self):
        script = str(Path(loop.__file__))
        help_run = subprocess.run([sys.executable, script, "--help"], capture_output=True)
        self.assertEqual(help_run.returncode, 0)
        loop.write_json(self.root / "plan.json", self.plan)
        result = subprocess.run([sys.executable, script, "prepare",
                                 "--prompt", str(self.prompt), "--plan", str(self.root / "plan.json"),
                                 "--out", str(self.run)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        result = subprocess.run([sys.executable, script, "packet", "--run", str(self.run)],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

