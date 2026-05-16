import tempfile
import unittest
from pathlib import Path

from simple.judge_agent_simple.api_models import (
    AnalysisRequest,
    AnalysisSource,
    JudgeMessageRequest,
    JudgeSessionRequest,
    ReferenceRunRequest,
)
from simple.judge_agent_simple.api_services import (
    config_snapshot,
    create_analysis,
    create_judge_session,
    get_reference_trace,
    health,
    list_reference_fixtures,
    run_reference_agent,
    send_judge_message,
)
from simple.judge_agent_simple.api_store import ApiStore


class ApiServicesTest(unittest.TestCase):
    def test_health_config_and_fixtures(self):
        self.assertEqual(health()["status"], "ok")
        self.assertIn("appDefaults", config_snapshot())
        fixtures = list_reference_fixtures()["fixtures"]
        self.assertTrue(any(item["id"] == "normal-login-error-spike" for item in fixtures))

    def test_reference_run_analysis_and_judge_session_flow(self):
        with tempfile.TemporaryDirectory() as td:
            store = ApiStore(Path(td))
            run = run_reference_agent(
                ReferenceRunRequest(mode="fixture", fixtureId="normal-login-error-spike", useLlm=False),
                store=store,
            )["run"]
            self.assertEqual(run["status"], "succeeded")
            self.assertTrue(Path(run["tracePath"]).exists())
            self.assertTrue(Path(run["reportPath"]).exists())

            trace = get_reference_trace(run["id"], store=store)
            self.assertGreater(len(trace["events"]), 0)

            analysis = create_analysis(
                AnalysisRequest(source=AnalysisSource(kind="reference-run", referenceRunId=run["id"])),
                store=store,
            )["analysis"]
            self.assertEqual(analysis["status"], "succeeded")
            self.assertEqual(analysis["summary"]["runCount"], 1)

            session = create_judge_session(
                JudgeSessionRequest(analysisId=analysis["id"], sessionId="api-flow", mode="deterministic-v2"),
                store=store,
            )["session"]
            self.assertEqual(session["id"], "api-flow")

            response = send_judge_message(
                "api-flow",
                JudgeMessageRequest(content="왜 block이야?"),
                store=store,
            )
            self.assertIn("message", response)
            self.assertTrue(response["message"]["content"])


if __name__ == "__main__":
    unittest.main()
