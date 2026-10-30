"""模型传输和动作协议测试，不调用外部模型。"""

import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import ProxyHandler
from urllib.error import HTTPError, URLError

from src.model import DeepSeekModel, ModelAction, ModelConfig, mock_reply, parse_reply, strict_json, tool_specs


class ModelTests(unittest.TestCase):
    def test_catalog_contains_exactly_six_documented_actions(self):
        functions = [tool["function"] for tool in tool_specs()]
        self.assertEqual({item["name"] for item in functions}, {
            "search_materials", "save_script", "estimate_duration", "check_rules", "request_input", "finish"})
        self.assertTrue(all(item["description"] and item["parameters"]["additionalProperties"] is False for item in functions))
        self.assertNotIn("materials", next(item for item in functions if item["name"] == "check_rules")["parameters"]["properties"])

    def test_native_reply_retains_call_id_and_drops_reasoning(self):
        payload = {"choices": [{"message": {"reasoning_content": "private reasoning", "tool_calls": [{
            "id": "call-1", "type": "function", "function": {"name": "search_materials", "arguments": '{"query":"字幕","reason":"检索依据"}'}}]}}]}
        reply = parse_reply(payload)
        self.assertEqual(reply.action.call_id, "call-1")
        self.assertNotIn("reasoning_content", reply.message)
        reply.action.validate()

    def test_invalid_arguments_still_return_corresponding_tool_call(self):
        for arguments in ['{"query":', '[1]', '{"query":"A","query":"B"}', '{"value":NaN}']:
            payload = {"choices": [{"message": {"tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "search_materials", "arguments": arguments}}]}}]}
            with self.subTest(arguments=arguments):
                reply = parse_reply(payload)
                self.assertEqual(reply.error.code, "invalid_arguments_json")
                self.assertEqual(reply.message["tool_calls"][0]["id"], "call-1")

    def test_batch_calls_are_rejected_without_discarding_ids(self):
        first = mock_reply("search_materials", {"query": "字幕", "reason": "检索"}, "a").message
        second = mock_reply("finish", {"status": "completed", "reason": "完成"}, "b").message
        reply = parse_reply({"choices": [{"message": {"tool_calls": first["tool_calls"] + second["tool_calls"]}}]})
        self.assertEqual(reply.error.code, "multiple_actions")
        self.assertEqual(len(reply.message["tool_calls"]), 2)
        self.assertIsNone(reply.action)

    def test_incomplete_or_plain_text_response_is_invalid(self):
        for payload in [{}, {"choices": []}, {"choices": [{"message": {"content": "完成"}}]},
                        {"choices": [{"finish_reason": "length", "message": {}}]}]:
            with self.subTest(payload=payload):
                self.assertEqual(parse_reply(payload).error.code, "invalid_response")

    def test_local_action_validation_rejects_forged_check_inputs(self):
        invalid = [
            ModelAction("a", "unknown", {}),
            ModelAction("a", "check_rules", {"script_version": 1, "reason": "检查", "materials": []}),
            ModelAction("a", "estimate_duration", {"script_version": True, "reason": "检查"}),
            ModelAction("a", "finish", {"status": "failed", "reason": "失败"}),
            ModelAction("a", "request_input", {"missing_fields": [], "questions": [], "reason": "缺信息"}),
        ]
        for action in invalid:
            with self.subTest(name=action.name), self.assertRaises(ValueError):
                action.validate()

    def test_http_client_sends_tools_and_disables_thinking(self):
        captured = {}
        payload = {"choices": [{"message": mock_reply("finish", {"status": "incomplete", "reason": "测试"}, "a").message}]}

        def transport(request, timeout):
            captured.update(body=json.loads(request.data), timeout=timeout, endpoint=request.full_url)
            return io.BytesIO(json.dumps(payload).encode())

        config = ModelConfig("test-key", timeout_seconds=3)
        reply = DeepSeekModel(config, transport).next_turn([], tool_specs())
        self.assertEqual(reply.action.name, "finish")
        self.assertEqual(captured["body"]["model"], "deepseek-v4-pro")
        self.assertEqual(captured["body"]["thinking"], {"type": "disabled"})
        self.assertEqual(len(captured["body"]["tools"]), 6)
        self.assertEqual(captured["timeout"], 3)
        self.assertNotIn("test-key", repr(config))

    def test_transport_errors_are_structured_and_not_retried_in_adapter(self):
        for failure, code, retryable in [
            (TimeoutError(), "timeout", True), (URLError("private server detail"), "connection_error", True),
            (HTTPError("https://api.deepseek.com", 401, "private detail", {}, None), "http_401", False),
            (HTTPError("https://api.deepseek.com", 429, "private detail", {}, None), "http_429", True),
        ]:
            calls = []

            def transport(request, timeout):
                calls.append(request)
                raise failure

            with self.subTest(code=code):
                reply = DeepSeekModel(ModelConfig("test-key"), transport).next_turn([], [])
                self.assertEqual((reply.error.code, reply.error.retryable), (code, retryable))
                self.assertEqual(len(calls), 1)
                self.assertNotIn("private", reply.error.message)

    def test_non_json_http_response_is_invalid(self):
        model = DeepSeekModel(ModelConfig("test-key"), lambda *a, **k: io.BytesIO(b"not json"))
        self.assertEqual(model.next_turn([], []).error.code, "invalid_response")

    def test_proxy_setting_is_scoped_to_deepseek_client(self):
        with patch("src.model.build_opener") as opener:
            DeepSeekModel(ModelConfig("test-key"))
            proxies = [handler for handler in opener.call_args.args if isinstance(handler, ProxyHandler)]
            self.assertEqual(len(proxies), 1)
            self.assertEqual(proxies[0].proxies, {})
            opener.reset_mock()
            DeepSeekModel(ModelConfig("test-key", use_proxy=True))
            self.assertFalse(any(isinstance(handler, ProxyHandler) for handler in opener.call_args.args))

    @unittest.skipUnless(importlib.util.find_spec("dotenv"), "python-dotenv is not installed")
    def test_environment_overrides_file_and_quotes_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('DEEPSEEK_API_KEY="file-key"\nDEEPSEEK_MODEL=file-model\n', encoding="utf-8")
            config = ModelConfig.from_env(path, {"DEEPSEEK_API_KEY": "env-key"})
            self.assertEqual(config.api_key, "env-key")
            self.assertEqual(config.model, "file-model")
            self.assertFalse(config.use_proxy)
            self.assertTrue(ModelConfig.from_env(path, {"DEEPSEEK_USE_PROXY": "true"}).use_proxy)
            with self.assertRaises(ValueError):
                ModelConfig.from_env(path, {"DEEPSEEK_USE_PROXY": "invalid"})
            self.assertNotIn("env-key", repr(config))
            with self.assertRaises(ValueError):
                ModelConfig.from_env(path, {"DEEPSEEK_API_KEY": ""})

    def test_config_rejects_missing_key_invalid_endpoint_and_timeout(self):
        for kwargs in [dict(api_key=""), dict(api_key="x", base_url="http://example.com"),
                       dict(api_key="x", base_url="https://user:password@example.com"),
                       dict(api_key="x", timeout_seconds=float("nan"))]:
            with self.subTest(fields=tuple(kwargs)), self.assertRaises(ValueError):
                ModelConfig(**kwargs)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_constants(self):
        for text in ['{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}']:
            with self.assertRaises(ValueError):
                strict_json(text)


if __name__ == "__main__":
    unittest.main()
