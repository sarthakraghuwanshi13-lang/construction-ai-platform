import os
import unittest
from unittest import mock

from construction_ai import schemas as S
from construction_ai.imaging import PreparedImage
from construction_ai.llm import LLMClient, LLMError, LLMUnavailable, extract_json, schema_hint

GOOD = '{"summary": "fine", "overall_risk": "low", "ppe": [], "hazards": [], "immediate_actions": []}'


class FakeClient(LLMClient):
    """LLMClient with a scripted transport (no network)."""

    def __init__(self, replies):
        super().__init__(api_key="test-key")
        self.replies = list(replies)
        self.calls = []

    def _send(self, system, messages, max_tokens):
        self.calls.append(messages)
        return self.replies.pop(0)


class ExtractJsonTests(unittest.TestCase):
    def test_plain_fenced_and_prose(self):
        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})
        self.assertEqual(extract_json('```json\n{"a": {"b": 2}}\n```'), {"a": {"b": 2}})
        self.assertEqual(extract_json('Here you go: {"a": 1} hope it helps'), {"a": 1})

    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            extract_json("no braces here")
        with self.assertRaises(ValueError):
            extract_json("{broken")

    def test_schema_hint_is_compact_json(self):
        hint = schema_hint(S.SafetyReport)
        self.assertIn("overall_risk", hint)
        self.assertNotIn("\n", hint)
        self.assertNotIn(' "title"', hint)


class ClientTests(unittest.TestCase):
    def test_unavailable_without_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            c = LLMClient(api_key=None)
            self.assertFalse(c.available)
            with self.assertRaises(LLMUnavailable):
                c.generate_structured(S.SafetyReport, "x")

    def test_success_first_try_and_image_block(self):
        c = FakeClient([GOOD])
        img = PreparedImage(name="a", data_b64="QUJD", width=40, height=40)
        r = c.generate_structured(S.SafetyReport, "analyze", images=[img])
        self.assertEqual(r.overall_risk, "low")
        content = c.calls[0][0]["content"]
        self.assertEqual(content[0]["type"], "image")
        self.assertEqual(content[0]["source"]["media_type"], "image/jpeg")
        self.assertEqual(content[-1]["type"], "text")
        self.assertIn("JSON Schema", content[-1]["text"])

    def test_repair_retry_succeeds(self):
        c = FakeClient(['{"summary": "x", "overall_risk": "bad"}', GOOD])
        r = c.generate_structured(S.SafetyReport, "analyze")
        self.assertEqual(r.summary, "fine")
        self.assertEqual(len(c.calls), 2)
        self.assertEqual(c.calls[1][-1]["role"], "user")
        self.assertIn("invalid", c.calls[1][-1]["content"])

    def test_gives_up_after_retry(self):
        c = FakeClient(["not json", "still not json"])
        with self.assertRaises(LLMError) as cm:
            c.generate_structured(S.SafetyReport, "analyze")
        self.assertIn("expected format", str(cm.exception))
        self.assertEqual(len(c.calls), 2)

    def test_transport_error_propagates(self):
        class Boom(FakeClient):
            def _send(self, *a, **k):
                raise LLMError("Rate limit reached.")
        with self.assertRaises(LLMError):
            Boom([]).generate_structured(S.SafetyReport, "x")

    def test_demo_mode_generates_valid_schemas(self):
        c = LLMClient(provider="demo")
        self.assertTrue(c.available)

        safety = c.generate_structured(S.SafetyReport, "check safety")
        self.assertIn(safety.overall_risk, ["low", "medium", "high", "critical"])
        self.assertTrue(len(safety.ppe) > 0)

        crack = c.generate_structured(S.CrackReport, "check crack")
        self.assertTrue(crack.crack_visible)
        self.assertIsNotNone(crack.crack_type)

        val = c.generate_structured(S.ValuationReport, "check valuation")
        self.assertTrue(val.estimated_value_low <= val.estimated_value_mid <= val.estimated_value_high)

        plan = c.generate_structured(S.ProjectPlan, "check plan")
        self.assertTrue(len(plan.tasks) >= 1)

        daily = c.generate_structured(S.DailyReport, "check daily")
        self.assertTrue(len(daily.work_completed) > 0)

        weather = c.generate_structured(S.WeatherNarrative, "check weather")
        self.assertTrue(len(weather.daily) > 0)

        know = c.generate_structured(S.KnowledgeAnswer, "check knowledge")
        self.assertTrue(len(know.key_points) > 0)

        gen = c.generate_structured(S.GeneralAnalysis, "check general")
        self.assertTrue(len(gen.observations) > 0)

    @mock.patch("requests.post")
    def test_gemini_transport_and_structured(self, mock_post):
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": GOOD}]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        c = LLMClient(api_key="gem-test-key", provider="gemini")
        self.assertTrue(c.available)
        r = c.generate_structured(S.SafetyReport, "analyze this")
        self.assertEqual(r.overall_risk, "low")
        self.assertTrue(mock_post.called)
        call_url = mock_post.call_args[0][0]
        self.assertIn("key=gem-test-key", call_url)

    def test_anthropic_credit_balance_error_handled(self):
        c = LLMClient(api_key="sk-ant-test", provider="anthropic")
        mock_anthropic = mock.MagicMock()
        fake_api_err = Exception("Your credit balance is too low to access the Anthropic API.")
        fake_api_err.status_code = 400
        fake_api_err.message = "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.'}}"
        fake_api_err.body = {"type": "error", "error": {"type": "invalid_request_error", "message": "Your credit balance is too low to access the Anthropic API."}}

        # Create a mock APIStatusError
        class FakeAPIStatusError(Exception):
            status_code = 400
            message = fake_api_err.message
            body = fake_api_err.body

        mock_client_instance = mock.MagicMock()
        mock_client_instance.messages.create.side_effect = FakeAPIStatusError("credit error")
        mock_anthropic.Anthropic.return_value = mock_client_instance
        mock_anthropic.AuthenticationError = type("AuthenticationError", (Exception,), {})
        mock_anthropic.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_anthropic.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_anthropic.APIStatusError = FakeAPIStatusError

        with mock.patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with self.assertRaises(LLMError) as cm:
                c._send("system", [{"role": "user", "content": []}], 1000)
            self.assertIn("credits depleted", str(cm.exception).lower())
            self.assertIn("console.anthropic.com/settings/plans", str(cm.exception))


if __name__ == "__main__":
    unittest.main()

