import type { Finding } from '../types/judge';

type FindingsPanelProps = {
  findings: Finding[];
  selectedFindingId: string;
  onSelectFinding: (findingId: string) => void;
};

function severityClass(severity: Finding['severity']) {
  if (severity === 'critical') return 'pill-critical';
  if (severity === 'high') return 'pill-high';
  if (severity === 'medium') return 'pill-medium';
  return '';
}

export function FindingsPanel({ findings, selectedFindingId, onSelectFinding }: FindingsPanelProps) {
  return (
    <section className="doc-card">
      <div className="section-eyebrow"><span>Judge findings</span><span>{findings.length} findings</span></div>
      <div className="row-list" style={{ gap: 10 }}>
        {findings.map((finding) => (
          <button
            type="button"
            key={finding.id}
            className={`finding-card ${selectedFindingId === finding.id ? 'active' : ''}`}
            onClick={() => onSelectFinding(finding.id)}
          >
            <div className="finding-header">
              <div>
                <div className="finding-title">{finding.id} <span className="inline-code">{finding.metric}</span></div>
                <span className="badge-uppercase">{finding.category}</span>
              </div>
              <span className={`pill ${severityClass(finding.severity)}`}>{finding.severity}</span>
            </div>
            <p className="small">{finding.actual}</p>
            <span className="pill">Evidence {finding.evidence.length}</span>{' '}
            <span className="pill">Priority {finding.priority ?? '—'}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
