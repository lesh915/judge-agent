from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_RUNBOOK = """
# Web Service Incident Runbook

## /api/login
- Owner: identity-platform
- SLO: 99.9% availability, p95 latency < 800ms
- Common causes for 5xx spikes: auth provider timeout, session store saturation, recent identity deployment, database connection pool exhaustion.
- Recommended checks: recent deploys, auth-provider health, Redis/session-store latency, application error logs, rollback readiness.

## /api/payment
- Owner: payments-platform
- SLO: 99.95% availability, p95 latency < 900ms
- Common causes: PSP timeout, fraud service latency, payment gateway throttling.
"""


@dataclass
class RetrievedDocument:
    doc_id: str
    score: float
    content: str
    source: str


class LocalRunbookRetriever:
    """Tiny local RAG retriever used by the reference agent.

    It models the RAG component that a production LangChain agent would expose as
    a retriever tool. The implementation is deterministic for fixture stability.
    """

    def __init__(self, runbook_path: Optional[str] = None):
        self.runbook_path = Path(runbook_path) if runbook_path else None
        self.source = str(self.runbook_path) if self.runbook_path else "embedded:web-service-runbook"
        self.text = self.runbook_path.read_text(encoding="utf-8") if self.runbook_path and self.runbook_path.exists() else DEFAULT_RUNBOOK

    def retrieve(self, query: str, k: int = 3) -> Dict[str, Any]:
        chunks = [chunk.strip() for chunk in self.text.split("\n\n") if chunk.strip()]
        q_terms = {term.lower().strip("/.,:-_") for term in query.split() if term.strip()}
        docs: List[RetrievedDocument] = []
        for idx, chunk in enumerate(chunks):
            lowered = chunk.lower()
            score = sum(1 for term in q_terms if term and term in lowered)
            if "/api/login" in query and "/api/login" in chunk:
                score += 5
            if "/api/payment" in query and "/api/payment" in chunk:
                score += 5
            if score:
                docs.append(RetrievedDocument(f"runbook-{idx}", float(score), chunk, self.source))
        docs = sorted(docs, key=lambda d: d.score, reverse=True)[:k]
        return {"query": query, "documents": [doc.__dict__ for doc in docs]}
