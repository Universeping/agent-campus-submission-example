"""离线模型驱动真实本地工具，不证明真实模型决策效果。"""

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import unittest

from src.agent import AgentLimits, AgentRunner
from src.model import MockModel, ModelReply, mock_reply
from src.schemas import RunMode, SearchResult, Material, ToolError
from src.trace import TraceRecorder
from src.tools import load_materials, load_brand_rules

ROOT = Path(__file__).resolve().parents[1]
HAS_GRAPH = importlib.util.find_spec("langgraph") is not None


class ScriptedModel:
    mode = RunMode.MOCK

    def __init__(self, actions):
        self.actions = iter(actions)
        self.requests = []

    def next_turn(self, messages, tools):
        self.requests.append(messages)
        value = next(self.actions)
        return value if isinstance(value, ModelReply) else mock_reply(value[0], value[1], f"scripted-{len(self.requests)}")


def action(name, **kwargs):
    return name, {"reason": "单元测试动作", **kwargs}


def save(narration="支持为视频添加字幕。", sources=None):
    return action("save_script", title="给视频加字幕", shots=[{
        "id": "S01", "visual": "字幕示意画面", "narration": narration,
        "source_ids": ["P01"] if sources is None else sources,
    }])


class NodeContractTests(unittest.TestCase):
    """直接验证节点边界，不代替真实 LangGraph 图集成测试。"""

    def setUp(self):
        self.input = json.loads((ROOT / "examples/normal/input.json").read_text())
        self.materials, self.rules = load_materials(), load_brand_rules()

    def nodes(self, model, *, overrides=None, limits=None):
        runner = AgentRunner(model, self.materials, self.rules, tool_overrides=overrides, limits=limits)
        trace = TraceRecorder("node-contract-test")
        state = runner._prepare(runner.initial_state(self.input), trace)
        for unused in range(runner.limits.max_steps + 1):
            if state["result"]:
                return state, trace
            state = runner._call_model(state, trace)
            if not state["result"]:
                state = runner._dispatch(state, trace)
        if state["result"]:
            return state, trace
        self.fail("nodes did not terminate within budget")

    def test_mock_node_scenarios_repair_using_real_tool_feedback(self):
        for scenario, expected_version in [("normal", 1), ("over-duration", 2), ("unsupported-claim", 2)]:
            with self.subTest(scenario=scenario):
                state, unused = self.nodes(MockModel(scenario))
                self.assertEqual(state["result"].status, "completed")
                self.assertEqual(state["current_version"], expected_version)

    def test_bad_reply_without_action_uses_budget_and_can_be_corrected(self):
        state, unused = self.nodes(ScriptedModel([ModelReply(), action("finish", status="incomplete")]))
        self.assertEqual(state["step_count"], 2)
        self.assertEqual(state["error_history"][0]["error"]["code"], "invalid_response")

    def test_untrusted_search_result_cannot_replace_fact_body(self):
        forged = lambda *a, **k: SearchResult("字幕", [Material("P01", "效率提升80%")])
        model = ScriptedModel([action("search_materials", query="字幕"), action("finish", status="incomplete")])
        state, unused = self.nodes(model, overrides={"search_materials": forged})
        self.assertEqual(state["retrieved"], {})
        self.assertEqual(state["result"].errors[0].code, "invalid_tool_result")

    def test_bad_tool_return_type_is_structured(self):
        model = ScriptedModel([action("search_materials", query="字幕"), action("finish", status="incomplete")])
        state, unused = self.nodes(model, overrides={"search_materials": lambda *a, **k: None})
        self.assertEqual(state["result"].errors[0].code, "invalid_tool_result")

    def test_stale_backend_report_is_rejected(self):
        from src.tools import estimate_duration

        def stale(script, target):
            return replace(estimate_duration(script, target), script_version=script.version + 1)

        model = ScriptedModel([action("search_materials", query="字幕"), save(),
                               action("estimate_duration", script_version=1), action("finish", status="incomplete")])
        state, unused = self.nodes(model, overrides={"estimate_duration": stale})
        self.assertIsNone(state["result"].duration_result)
        self.assertEqual(state["result"].errors[0].code, "stale_tool_result")

    def test_failed_recheck_invalidates_previously_passing_report(self):
        from src.tools import estimate_duration
        calls = []

        def fail_second(script, target):
            calls.append(script)
            return estimate_duration(script, target) if len(calls) == 1 else ToolError("estimate_duration", "unavailable", "估时失败")

        model = ScriptedModel([action("search_materials", query="字幕"), save(),
                               action("estimate_duration", script_version=1), action("estimate_duration", script_version=1),
                               action("finish", status="incomplete")])
        state, unused = self.nodes(model, overrides={"estimate_duration": fail_second})
        self.assertIsNone(state["result"].duration_result)
        self.assertEqual(state["result"].errors[0].code, "unavailable")

    def test_every_native_call_receives_corresponding_tool_feedback(self):
        state, unused = self.nodes(MockModel())
        messages = state["messages"]
        for index, message in enumerate(messages):
            if message["role"] == "assistant":
                self.assertEqual(messages[index + 1]["role"], "tool")
                self.assertEqual(messages[index + 1]["tool_call_id"], message["tool_calls"][0]["id"])

    def test_transport_retries_stop_and_count_each_request(self):
        failure = ModelReply(error=ToolError("model", "timeout", "超时", True))
        state, unused = self.nodes(ScriptedModel([failure, failure]))
        self.assertEqual(state["step_count"], 2)
        self.assertEqual(state["result"].status, "failed")

    def test_node_budget_stops_unknown_actions(self):
        state, unused = self.nodes(ScriptedModel([action("unknown")] * 2), limits=AgentLimits(max_steps=2))
        self.assertEqual(state["step_count"], 2)
        self.assertEqual(state["result"].status, "incomplete")


@unittest.skipUnless(HAS_GRAPH, "LangGraph is not installed; integration tests require the real framework")
class AgentTests(unittest.TestCase):
    def setUp(self):
        self.input = json.loads((ROOT / "examples/normal/input.json").read_text())
        self.materials, self.rules = load_materials(), load_brand_rules()

    def run_agent(self, model=None, **kwargs):
        return AgentRunner(model or MockModel(), self.materials, self.rules, **kwargs).run(self.input)

    def test_normal_mock_completes_with_real_bound_checks(self):
        run = self.run_agent()
        self.assertEqual(run.result.status, "completed")
        self.assertEqual(run.result.mode, "mock")
        self.assertEqual(run.state["tool_call_count"], 3)
        self.assertEqual(run.state["step_count"], 5)
        self.assertTrue(run.result.duration_result.matches(run.result.script))
        self.assertTrue(run.result.rule_check_result.matches(run.result.script))
        self.assertEqual([event["action"] for event in run.trace.events if event["event"] == "action"],
                         ["search_materials", "save_script", "estimate_duration", "check_rules", "finish"])

    def test_over_duration_causes_revision_and_real_recheck(self):
        run = self.run_agent(MockModel("over-duration"))
        self.assertEqual(run.result.status, "completed")
        self.assertEqual(run.result.script.version, 2)
        self.assertFalse(run.state["duration_results"][1].passed)
        self.assertTrue(run.state["duration_results"][2].passed)
        self.assertEqual(set(run.state["scripts"]), {1, 2})
        self.assertEqual(run.result.duration_result.script_version, 2)

    def test_unsupported_claim_is_repaired_after_rule_feedback(self):
        run = self.run_agent(MockModel("unsupported-claim"))
        self.assertEqual(run.result.status, "completed")
        self.assertFalse(run.state["rule_results"][1].passed)
        self.assertTrue(run.state["rule_results"][2].passed)
        self.assertNotIn("80%", run.result.script.shots[0].narration)

    def test_unchecked_finish_is_rejected_then_model_continues(self):
        run = self.run_agent(MockModel("early-finish"))
        self.assertEqual(run.result.status, "completed")
        first = next(event for event in run.trace.events if event["event"] == "action")
        self.assertEqual(first["action"], "finish")
        self.assertIn("error", first["observation"])

    def test_new_revision_cannot_reuse_old_passing_reports(self):
        model = ScriptedModel([
            action("search_materials", query="字幕"), save(),
            action("estimate_duration", script_version=1), action("check_rules", script_version=1),
            save(), action("finish", status="completed"), action("finish", status="incomplete"),
        ])
        run = self.run_agent(model)
        self.assertEqual(run.result.status, "incomplete")
        self.assertEqual(run.result.script.version, 2)
        self.assertIsNone(run.result.duration_result)
        self.assertIsNone(run.result.rule_check_result)
        self.assertTrue(run.state["duration_results"][1].passed)
        self.assertIn("旧稿检查不可复用", run.state["error_history"][-1]["error"]["message"])

    def test_missing_input_returns_questions_without_model_request(self):
        model = ScriptedModel([])
        data = dict(self.input)
        del data["topic"]
        run = AgentRunner(model, self.materials, self.rules).run(data)
        self.assertEqual(run.result.status, "needs_input")
        self.assertEqual(run.result.missing_fields, ("topic",))
        self.assertTrue(run.result.questions)
        self.assertEqual(len(model.requests), 0)

    def test_no_materials_leads_to_request_input(self):
        run = AgentRunner(MockModel(), [], self.rules).run(self.input)
        self.assertEqual(run.result.status, "needs_input")
        self.assertIn("materials", run.result.missing_fields)

    def test_transient_tool_failure_is_observed_and_cleared_after_success(self):
        run = self.run_agent(simulate_search_failure=True)
        self.assertEqual(run.result.status, "completed")
        self.assertFalse(run.result.errors)
        self.assertTrue(run.state["error_history"])
        self.assertEqual(run.state["tool_call_count"], 4)

    def test_persistent_tool_failure_is_not_hidden(self):
        def failure(*args, **kwargs):
            return ToolError("search_materials", "unavailable", "资料服务失败", True)
        run = self.run_agent(tool_overrides={"search_materials": failure})
        self.assertEqual(run.result.status, "incomplete")
        self.assertEqual(run.result.errors[0].code, "unavailable")

    def test_step_and_tool_limits_return_explicit_incomplete(self):
        for limits in [AgentLimits(max_steps=1), AgentLimits(max_tool_calls=1)]:
            with self.subTest(limits=limits):
                run = self.run_agent(limits=limits)
                self.assertEqual(run.result.status, "incomplete")
                self.assertIn("上限", run.result.reason)
                self.assertLessEqual(run.state["step_count"], limits.max_steps)
                self.assertLessEqual(run.state["tool_call_count"], limits.max_tool_calls)

    def test_bad_actions_consume_budget_without_executing_tools(self):
        model = ScriptedModel([action("unknown") for _ in range(3)])
        run = self.run_agent(model, limits=AgentLimits(max_steps=3))
        self.assertEqual(run.result.status, "incomplete")
        self.assertEqual(run.state["step_count"], 3)
        self.assertEqual(run.state["tool_call_count"], 0)

    def test_model_cannot_widen_scope_or_override_trusted_inputs(self):
        model = ScriptedModel([
            action("search_materials", query="字幕", material_ids=["P99"]),
            action("check_rules", script_version=1, materials=[]),
            action("finish", status="incomplete"),
        ])
        run = self.run_agent(model)
        self.assertEqual(run.state["tool_call_count"], 0)
        self.assertEqual(len(run.state["error_history"]), 2)

    def test_transport_retry_consumes_step_and_authentication_is_fatal(self):
        retry = ModelReply(error=ToolError("model", "timeout", "超时", True))
        run = self.run_agent(ScriptedModel([retry, action("finish", status="incomplete")]))
        self.assertEqual(run.state["step_count"], 2)
        self.assertEqual(run.result.status, "incomplete")
        failed = self.run_agent(ScriptedModel([ModelReply(error=ToolError("model", "http_401", "认证失败"))]))
        self.assertEqual(failed.result.status, "failed")
        self.assertEqual(failed.state["step_count"], 1)

    def test_batch_rejection_replies_to_every_call_and_executes_nothing(self):
        one = mock_reply("search_materials", {"query": "字幕", "reason": "检索"}, "a").message
        two = mock_reply("finish", {"status": "completed", "reason": "结束"}, "b").message
        message = {"role": "assistant", "content": None, "tool_calls": one["tool_calls"] + two["tool_calls"]}
        model = ScriptedModel([ModelReply(message=message, error=ToolError("model", "multiple_actions", "一次一个动作")),
                               action("finish", status="incomplete")])
        run = self.run_agent(model)
        feedback = [item["tool_call_id"] for item in run.state["messages"] if item["role"] == "tool"]
        self.assertEqual(feedback[:2], ["a", "b"])
        self.assertEqual(run.state["tool_call_count"], 0)

    def test_material_body_not_exposed_before_retrieval_and_state_is_isolated(self):
        model = ScriptedModel([action("finish", status="incomplete")])
        self.run_agent(model)
        view = json.loads(model.requests[0][1]["content"].split("\n", 1)[1])
        self.assertEqual(view["retrieved_materials"], [])
        self.assertEqual(view["allowed_material_ids"], ["P01"])
        self.assertNotIn("支持为视频添加字幕", json.dumps(model.requests[0], ensure_ascii=False))
        self.assertEqual(self.run_agent().result.script.version, 1)
        self.assertEqual(self.run_agent().result.script.version, 1)


if __name__ == "__main__":
    unittest.main()
