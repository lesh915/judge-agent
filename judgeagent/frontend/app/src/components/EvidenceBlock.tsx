import type { Finding } from '../types/judge';

type EvidenceBlockProps = {
  finding?: Finding;
};

export function EvidenceBlock({ finding }: EvidenceBlockProps) {
  if (!finding) {
    return <section className="doc-card"><p>No finding selected.</p></section>;
  }

  const jsonSnippet = JSON.stringify({
    finding_id: finding.id,
    metric: finding.metric,
    severity: finding.severity,
    evidence: finding.evidence,
  }, null, 2);

  return (
    <section className="doc-card">
      <div className="section-eyebrow"><span>Evidence detail</span><span>{finding.id}</span></div>
      <h3><span className="inline-code">{finding.metric}</span></h3>
      <p><strong>Expected:</strong> {finding.expected}</p>
      <p><strong>Actual:</strong> {finding.actual}</p>
      <div className="banner banner-red">
        <strong>⚠️ Recommendation</strong>
        <p className="small">{finding.recommendation}</p>
      </div>
      <p className="badge-uppercase" style={{ marginTop: 16 }}>Trace evidence</p>
      <pre className="code-block"><code>{jsonSnippet}</code></pre>
    </section>
  );
}
