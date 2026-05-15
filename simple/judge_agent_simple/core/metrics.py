from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class DriftMetricSpec:
    name: str
    category: str
    measurement_method: str
    value_type: str
    description: str
    severity: str
    mvp_priority: Optional[int] = None
    ref_agent_priority: Optional[int] = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _load_metrics_from_config() -> List[DriftMetricSpec]:
    from .config import metrics_config

    data = metrics_config()
    metrics: List[DriftMetricSpec] = []
    for item in data.get("metrics", []):
        metrics.append(DriftMetricSpec(
            name=str(item["name"]),
            category=str(item["category"]),
            measurement_method=str(item["measurement_method"]),
            value_type=str(item["value_type"]),
            description=str(item["description"]),
            severity=str(item["severity"]),
            mvp_priority=item.get("mvp_priority"),
            ref_agent_priority=item.get("ref_agent_priority"),
        ))
    return metrics


_METRICS: List[DriftMetricSpec] = _load_metrics_from_config()

METRIC_REGISTRY: Dict[str, DriftMetricSpec] = {metric.name: metric for metric in _METRICS}


def get_metric(name: str) -> Optional[DriftMetricSpec]:
    return METRIC_REGISTRY.get(name)


def require_metric(name: str) -> DriftMetricSpec:
    metric = get_metric(name)
    if metric is None:
        raise KeyError(f"unknown drift metric: {name}")
    return metric


def list_metrics(category: Optional[str] = None) -> List[DriftMetricSpec]:
    metrics = list(METRIC_REGISTRY.values())
    if category:
        metrics = [metric for metric in metrics if metric.category == category]
    return sorted(metrics, key=metric_sort_key)


def metric_sort_key(metric: DriftMetricSpec) -> tuple:
    priority = metric.mvp_priority if metric.mvp_priority is not None else metric.ref_agent_priority
    return (priority is None, priority or 999, metric.category, metric.name)


def enrich_finding(finding: dict) -> dict:
    metric = get_metric(str(finding.get("metric") or ""))
    if not metric:
        return dict(finding)
    enriched = dict(finding)
    enriched["metric_spec"] = metric.to_dict()
    enriched.setdefault("category", metric.category)
    enriched.setdefault("severity", metric.severity.lower())
    enriched["metric_category"] = metric.category
    enriched["metric_priority"] = metric.mvp_priority or metric.ref_agent_priority
    return enriched


def known_metric_names() -> List[str]:
    return sorted(METRIC_REGISTRY)


def validate_metric_coverage(metric_names: Iterable[str]) -> List[str]:
    return sorted({name for name in metric_names if name not in METRIC_REGISTRY})
