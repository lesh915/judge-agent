import type { AnalysisSummary } from '../types/judge';

type RunCompareTableProps = {
  summary: AnalysisSummary;
};

export function RunCompareTable({ summary }: RunCompareTableProps) {
  const rows = [
    { run: 'ref-normal-login-error-spike-001', gate: 'block', score: 55, findings: 3 },
    { run: 'ref-normal-login-error-spike-baseline', gate: 'pass', score: 96, findings: 0 },
    { run: 'ref-chat-followup-001', gate: 'warning', score: 82, findings: 1 },
  ];

  return (
    <section className="doc-card">
      <div className="section-eyebrow"><span>Run comparison</span><span>{summary.runCount} runs</span></div>
      <table className="table">
        <thead>
          <tr><th>Run</th><th>Gate</th><th>Score</th><th>Findings</th></tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.run}>
              <td><span className="inline-code">{row.run}</span></td>
              <td><span className={`pill ${row.gate === 'block' ? 'pill-critical' : row.gate === 'pass' ? 'pill-pass' : 'pill-medium'}`}>{row.gate}</span></td>
              <td>{row.score}</td>
              <td>{row.findings}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
