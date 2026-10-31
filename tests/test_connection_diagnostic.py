"""模拟传输验证诊断分类与凭据过滤，不作真实网络证据。"""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
from io import BytesIO, StringIO
import json
from pathlib import Path
import socket
import ssl
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from src.model import ModelConfig, mock_reply

PATH = Path(__file__).resolve().parents[1] / "scripts/check_deepseek_connection.py"
SPEC = importlib.util.spec_from_file_location("connection_diagnostic", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SECRET = "diagnostic-known-token"


class Response(BytesIO):
    status = 200


def response(models=None):
    return Response(json.dumps({"data": [{"id": x} for x in (models or ["deepseek-v4-pro"])],
                                "extra": SECRET}).encode())


class ConnectionDiagnosticTests(unittest.TestCase):
    def test_get_models_uses_configured_endpoint_and_keeps_key_out_of_report(self):
        config = ModelConfig(SECRET, base_url="https://api.deepseek.com/v1")
        transport = Mock(return_value=response())
        report = MODULE.check_connection(config, timeout=7, transport=transport)
        request = transport.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, "https://api.deepseek.com/v1/models")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + SECRET)
        self.assertEqual(transport.call_args.kwargs["timeout"], 7)
        self.assertEqual(report["status"], "passed")
        self.assertNotIn(SECRET, json.dumps(report))

    def test_wrapped_errors_are_classified_without_raw_exception_text(self):
        cases = [(socket.gaierror(-2, SECRET), "dns_error"),
                 (ssl.SSLCertVerificationError(SECRET), "tls_certificate_error"),
                 (ssl.SSLError(SECRET), "tls_error"),
                 (TimeoutError(SECRET), "timeout"),
                 (ConnectionRefusedError(SECRET), "connection_refused"),
                 (ConnectionResetError(SECRET), "connection_reset"),
                 (SECRET, "connection_error")]
        for error, expected in cases:
            with self.subTest(expected=expected):
                report = MODULE.check_connection(ModelConfig(SECRET), transport=Mock(side_effect=URLError(error)))
                self.assertEqual(report["status"], expected)
                self.assertTrue(report["wrapped_by_urlerror"])
                self.assertNotIn(SECRET, json.dumps(report))

    def test_http_errors_return_only_status_and_close_response(self):
        for code in (401, 403, 429, 500):
            with self.subTest(code=code):
                body = BytesIO(SECRET.encode())
                error = HTTPError("https://example.invalid/" + SECRET, code, SECRET, {}, body)
                report = MODULE.check_connection(ModelConfig(SECRET), transport=Mock(side_effect=error))
                self.assertEqual(report["status"], "http_error")
                self.assertEqual(report["http_status"], code)
                self.assertNotIn(SECRET, json.dumps(report))
                self.assertTrue(body.closed)

    def test_invalid_and_oversized_responses_are_not_dumped(self):
        for body in (SECRET.encode(), b'{"data":null}', b'x' * (1024 * 1024 + 1)):
            with self.subTest(length=len(body)):
                report = MODULE.check_connection(ModelConfig(SECRET), transport=Mock(return_value=Response(body)))
                self.assertEqual(report["status"], "invalid_response")
                self.assertNotIn(SECRET, json.dumps(report))

    def test_missing_model_is_distinct_from_connection_failure(self):
        report = MODULE.check_connection(ModelConfig(SECRET), transport=Mock(return_value=response(["other-model"])))
        self.assertEqual(report["status"], "model_not_listed")
        self.assertFalse(report["model_list_contains_configured_model"])
        self.assertEqual(report["http_status"], 200)

    def test_default_transport_reuses_existing_clients_proxy_configuration(self):
        config = ModelConfig(SECRET, use_proxy=True)
        with patch.object(MODULE, "DeepSeekModel") as client:
            client.return_value.transport = Mock(return_value=response())
            report = MODULE.check_connection(config)
            client.assert_called_once_with(config)
        self.assertTrue(report["use_proxy"])
        self.assertEqual(report["status"], "passed")

    def test_cli_writes_safe_report_and_respects_separate_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "check"
            stdout = StringIO()
            with patch.object(MODULE.ModelConfig, "from_env", return_value=ModelConfig(SECRET)), \
                    patch.object(MODULE, "DeepSeekModel") as client, redirect_stdout(stdout):
                transport = Mock(return_value=response())
                client.return_value.transport = transport
                status = MODULE.main(["--output-dir", str(output), "--timeout", "2"])
            self.assertEqual(status, 0)
            self.assertEqual(transport.call_args.kwargs["timeout"], 2)
            report = (output / "report.json").read_text()
            self.assertNotIn(SECRET, report + stdout.getvalue())
            self.assertIn("diagnostic_script_sha256", json.loads(report))
            with redirect_stderr(StringIO()):
                self.assertEqual(MODULE.main(["--output-dir", str(output)]), 2)
            self.assertEqual((output / "report.json").read_text(), report)

    def test_chat_probe_uses_actual_json_client_and_only_records_action_name(self):
        message = mock_reply("finish", {"status": "incomplete", "reason": SECRET}, "test-call").message
        payload = {"choices": [{"message": message}]}
        transport = Mock(return_value=Response(json.dumps(payload).encode()))
        report = MODULE.check_chat(ModelConfig(SECRET), timeout=4, transport=transport)
        request = transport.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + SECRET)
        body = json.loads(request.data)
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual([x["function"]["name"] for x in body["tools"]], ["finish"])
        self.assertEqual(transport.call_args.kwargs["timeout"], 4)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["tool_action"], "finish")
        self.assertNotIn(SECRET, json.dumps(report))

    def test_chat_probe_preserves_wrapped_timeout_and_http_categories(self):
        for error, status in [(URLError(TimeoutError(SECRET)), "timeout"),
                              (URLError(ssl.SSLError(SECRET)), "tls_error"),
                              (HTTPError("https://api.deepseek.com", 401, SECRET, {}, None), "http_error")]:
            with self.subTest(status=status):
                report = MODULE.check_chat(ModelConfig(SECRET), transport=Mock(side_effect=error))
                self.assertEqual(report["status"], status)
                self.assertNotIn(SECRET, json.dumps(report))

    def test_chat_probe_distinguishes_protocol_response_from_network_failure(self):
        payload = {"choices": [{"message": {"content": SECRET}}]}
        report = MODULE.check_chat(ModelConfig(SECRET), transport=Mock(return_value=Response(json.dumps(payload).encode())))
        self.assertEqual(report["http_status"], 200)
        self.assertEqual(report["status"], "protocol_error")
        self.assertNotIn(SECRET, json.dumps(report))

    def test_stage_observer_keeps_certificate_validation_and_identifies_tls_timeout(self):
        stages = MODULE.NetworkStages()
        connection = MODULE.ObservedHTTPSConnection("api.deepseek.com", stages=stages)
        self.assertEqual(connection._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(connection._context.check_hostname)
        connection._context = Mock()
        connection._context.wrap_socket.side_effect = TimeoutError(SECRET)
        def connected(instance):
            instance.sock = Mock()
        with patch.object(MODULE.http.client.HTTPConnection, "connect", connected):
            with self.assertRaises(TimeoutError):
                connection.connect()
        self.assertEqual(stages.phase, "tls_handshake")
        self.assertEqual([(e["stage"], e["status"]) for e in stages.events],
                         [("connect", "passed"), ("tls_handshake", "failed")])
        self.assertNotIn(SECRET, json.dumps(stages.events))

    def test_connect_timeout_is_not_misattributed_to_tls(self):
        stages = MODULE.NetworkStages()
        connection = MODULE.ObservedHTTPSConnection("api.deepseek.com", stages=stages)
        with patch.object(MODULE.http.client.HTTPConnection, "connect", side_effect=TimeoutError(SECRET)):
            with self.assertRaises(TimeoutError):
                connection.connect()
        self.assertEqual(stages.phase, "connect")
        self.assertEqual([e["stage"] for e in stages.events], ["connect"])
        self.assertNotIn(SECRET, json.dumps(stages.events))

    def test_send_and_wait_timeouts_have_distinct_stages_without_payloads(self):
        for operation, expected in (("send", "send_request"), ("getresponse", "wait_http_response")):
            with self.subTest(operation=operation):
                stages = MODULE.NetworkStages()
                connection = MODULE.ObservedHTTPSConnection("api.deepseek.com", stages=stages)
                connection.sock = Mock()
                with patch.object(MODULE.http.client.HTTPConnection, operation, side_effect=TimeoutError(SECRET)):
                    with self.assertRaises(TimeoutError):
                        getattr(connection, operation)(*([SECRET.encode()] if operation == "send" else []))
                self.assertEqual(stages.phase, expected)
                self.assertNotIn(SECRET, json.dumps(stages.events))

    def test_stage_opener_preserves_proxy_scope_and_redirect_block(self):
        with patch.object(MODULE, "build_opener") as opener:
            MODULE.observed_opener(ModelConfig(SECRET), MODULE.NetworkStages())
            handlers = opener.call_args.args
            self.assertTrue(any(isinstance(h, MODULE.ObservedHTTPSHandler) for h in handlers))
            self.assertTrue(any(isinstance(h, MODULE._NoRedirect) for h in handlers))
            self.assertEqual([h.proxies for h in handlers if isinstance(h, MODULE.ProxyHandler)], [{}])
            opener.reset_mock()
            MODULE.observed_opener(ModelConfig(SECRET, use_proxy=True), MODULE.NetworkStages())
            self.assertFalse(any(isinstance(h, MODULE.ProxyHandler) for h in opener.call_args.args))


if __name__ == "__main__":
    unittest.main()
