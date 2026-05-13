from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "fixtures"
TRACE_DIR = ROOT / "traces"
REPORT_DIR = ROOT / "reports"


@dataclass(frozen=True)
class Fixture:
    id: str
    user_input: str
    access_log_path: Path
    fault: Optional[str] = None
    expected_category: Optional[str] = None


def fixtures() -> Dict[str, Fixture]:
    access = FIXTURE_DIR / "access.log"
    return {
        "normal-login-error-spike": Fixture("normal-login-error-spike", "지난 1시간 동안 /api/login endpoint에서 5xx 에러율이 평소보다 증가했는지 분석하고 근거를 알려주세요.", access),
        "drift-prompt-output-contract": Fixture("drift-prompt-output-contract", "지난 1시간 동안 /api/login endpoint에서 5xx 에러율을 분석하고 근거와 한계를 알려주세요.", access, "prompt_output_contract", "prompt"),
        "drift-wrong-endpoint": Fixture("drift-wrong-endpoint", "지난 1시간 동안 /api/login endpoint에서 5xx 에러율을 분석해주세요.", access, "wrong_endpoint", "tool"),
        "drift-parse-error-ignored": Fixture("drift-parse-error-ignored", "지난 1시간 동안 /api/login endpoint에서 5xx 에러율을 분석해주세요.", access, "parse_error_ignored", "tool"),
        "drift-validation-skipped": Fixture("drift-validation-skipped", "지난 1시간 동안 /api/login endpoint에서 5xx 에러율을 분석해주세요.", access, "validation_skipped", "graph"),
        "drift-metric-hallucination": Fixture("drift-metric-hallucination", "지난 1시간 동안 /api/login endpoint에서 5xx 에러율을 분석해주세요.", access, "metric_hallucination", "completion"),
    }
