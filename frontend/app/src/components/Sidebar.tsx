import type { ConfigSnapshot, ReferenceRun } from '../types/judge';

type SidebarProps = {
  referenceRun: ReferenceRun;
  config: ConfigSnapshot;
};

export function Sidebar({ referenceRun, config }: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Workspace sidebar">
      <section className="card">
        <div className="section-eyebrow"><span>Session</span><span>Live</span></div>
        <h3>weblog-drift-review</h3>
        <p className="small">Loaded with Reference Agent fixture output and Judge Agent mock findings.</p>
        <div className="row-list">
          <div className="row-item"><span className="badge-uppercase">Mode</span><br /><span className="inline-code">{config.chatMode}</span></div>
          <div className="row-item"><span className="badge-uppercase">Adapter</span><br /><span className="inline-code">{config.adapter}</span></div>
          <div className="row-item"><span className="badge-uppercase">Model</span><br /><span className="inline-code">{config.model}</span></div>
        </div>
      </section>

      <section className="card">
        <div className="section-eyebrow"><span>Reference run</span><span className="pill pill-pass">{referenceRun.status}</span></div>
        <h3>{referenceRun.fixture}</h3>
        <p className="small">Generated trace is ready for Judge Agent review.</p>
        <p><span className="inline-code">{referenceRun.tracePath}</span></p>
      </section>

      <section className="banner banner-blue">
        <strong>💡 MVP flow</strong>
        <p className="small">Start with mock UI, then connect Reference Agent run API → Judge analyze API → chat API.</p>
      </section>
    </aside>
  );
}
