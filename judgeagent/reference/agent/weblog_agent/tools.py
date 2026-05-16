from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import quantiles
from typing import Any, Dict, Iterable, List, Optional

LOG_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) [^"]+" (?P<status>\d{3}) (?P<size>\S+) "(?P<referer>[^"]*)" "(?P<ua>[^"]*)" (?P<latency>\d+)'
)
TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"


def read_log_file(path: str, max_lines: int = 10000) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"log file not found: {path}")
    lines: List[str] = []
    with p.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= max_lines:
                return {"path": str(p), "lines": lines, "line_count": len(lines), "truncated": True}
            lines.append(line.rstrip("\n"))
    return {"path": str(p), "lines": lines, "line_count": len(lines), "truncated": False}


def _parse_time(value: str) -> str:
    return datetime.strptime(value, TIME_FMT).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_access_log(lines: List[str], format: str = "nginx_combined") -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    errors = 0
    for line in lines:
        if format == "json":
            try:
                obj = json.loads(line)
                records.append(obj)
            except Exception:
                errors += 1
            continue
        m = LOG_RE.match(line)
        if not m:
            errors += 1
            continue
        gd = m.groupdict()
        try:
            records.append({
                "timestamp": _parse_time(gd["time"]),
                "ip": gd["ip"],
                "method": gd["method"],
                "path": gd["path"].split("?", 1)[0],
                "status": int(gd["status"]),
                "latency_ms": int(gd["latency"]),
                "user_agent": gd["ua"],
                "raw": line,
            })
        except Exception:
            errors += 1
    return {"records": records, "parse_error_count": errors, "total_lines": len(lines)}


def filter_log_records(records: List[Dict[str, Any]], start_time: Optional[str] = None, end_time: Optional[str] = None,
                       path_pattern: Optional[str] = None, status_min: int = 0, status_max: int = 599) -> Dict[str, Any]:
    def in_range(rec: Dict[str, Any]) -> bool:
        ts = rec.get("timestamp", "")
        if start_time and ts < start_time:
            return False
        if end_time and ts > end_time:
            return False
        if path_pattern and path_pattern not in rec.get("path", ""):
            return False
        status = int(rec.get("status", 0))
        return status_min <= status <= status_max

    matched = [r for r in records if in_range(r)]
    return {"records": matched, "matched_count": len(matched), "total_count": len(records)}


def _percentile(values: List[int], pct: int) -> int:
    if not values:
        return 0
    values = sorted(values)
    idx = max(0, min(len(values) - 1, round((pct / 100) * (len(values) - 1))))
    return int(values[idx])


def compute_log_metrics(records: List[Dict[str, Any]], group_by=None, latency_percentiles=None) -> Dict[str, Any]:
    request_count = len(records)
    count_4xx = sum(1 for r in records if 400 <= int(r.get("status", 0)) <= 499)
    count_5xx = sum(1 for r in records if 500 <= int(r.get("status", 0)) <= 599)
    error_count = count_4xx + count_5xx
    latencies = [int(r.get("latency_ms", 0)) for r in records]
    top_paths = Counter(r.get("path") for r in records).most_common(5)
    top_ips = Counter(r.get("ip") for r in records).most_common(5)
    return {
        "request_count": request_count,
        "error_count": error_count,
        "4xx_count": count_4xx,
        "5xx_count": count_5xx,
        "error_rate": round(error_count / request_count, 4) if request_count else 0.0,
        "p50_latency_ms": _percentile(latencies, 50),
        "p95_latency_ms": _percentile(latencies, 95),
        "p99_latency_ms": _percentile(latencies, 99),
        "top_paths": [{"path": k, "count": v} for k, v in top_paths if k],
        "top_ips": [{"ip": k, "count": v} for k, v in top_ips if k],
    }


def detect_log_anomalies(metrics: Dict[str, Any], baseline: Optional[Dict[str, Any]] = None, thresholds: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    thresholds = thresholds or {"error_rate_warning": 0.05, "error_rate_critical": 0.10, "p95_latency_warning_ms": 1000}
    baseline = baseline or {}
    anomalies: List[Dict[str, Any]] = []
    error_rate = float(metrics.get("error_rate", 0.0))
    base_error_rate = baseline.get("error_rate")
    expected_error = base_error_rate if base_error_rate is not None else thresholds.get("error_rate_warning", 0.05)
    if error_rate >= thresholds.get("error_rate_critical", 0.10):
        anomalies.append({"type": "error_rate_spike", "severity": "critical", "metric": "error_rate", "actual": error_rate, "expected": expected_error, "reason": "error_rate exceeded critical threshold"})
    elif error_rate >= thresholds.get("error_rate_warning", 0.05):
        anomalies.append({"type": "error_rate_spike", "severity": "medium", "metric": "error_rate", "actual": error_rate, "expected": expected_error, "reason": "error_rate exceeded warning threshold"})
    p95 = int(metrics.get("p95_latency_ms", 0))
    if p95 >= thresholds.get("p95_latency_warning_ms", 1000):
        anomalies.append({"type": "latency_spike", "severity": "medium", "metric": "p95_latency_ms", "actual": p95, "expected": thresholds.get("p95_latency_warning_ms"), "reason": "p95 latency exceeded warning threshold"})
    for ip in metrics.get("top_ips", [])[:1]:
        if metrics.get("request_count", 0) and ip["count"] / metrics["request_count"] > 0.5:
            anomalies.append({"type": "suspicious_ip", "severity": "medium", "metric": "top_ips", "actual": ip, "expected": "no single IP > 50%", "reason": "single IP generated majority of filtered traffic"})
    return {"anomalies": anomalies}
