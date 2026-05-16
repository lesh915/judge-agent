export function TraceUploadCard() {
  return (
    <section className="card">
      <div className="section-eyebrow"><span>Trace input</span><span>JSONL</span></div>
      <h3>Load trace path or glob</h3>
      <p className="small">MVP starts with path/glob input. File upload and persistence come in the next phase.</p>
      <input className="input" defaultValue="reference_agent/weblog_agent/traces/*.jsonl" />
      <p><button className="button-secondary">Analyze traces</button></p>
    </section>
  );
}
