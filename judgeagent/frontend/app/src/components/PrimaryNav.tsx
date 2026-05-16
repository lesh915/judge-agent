type PrimaryNavProps = {
  onNewAnalysis: () => void;
};

export function PrimaryNav({ onNewAnalysis }: PrimaryNavProps) {
  return (
    <>
      <nav className="primary-nav" aria-label="Primary navigation">
        <div className="brand">
          <span className="logo-mark" aria-hidden="true">🦔</span>
          <span>Judge Agent · Drift Review</span>
        </div>
        <div className="nav-actions">
          <button className="button-tertiary">Docs</button>
          <button className="button-tertiary">Config</button>
          <button className="button-primary" onClick={onNewAnalysis}>New analysis</button>
        </div>
      </nav>
      <div className="sub-nav">
        <div className="sub-nav-links" aria-label="Workspace sections">
          <span className="pill pill-active">Review</span>
          <span className="pill">Reference Agent</span>
          <span className="pill">Traces</span>
          <span className="pill">Metrics</span>
          <span className="pill">Config</span>
        </div>
        <span>reference run → trace → judge review</span>
      </div>
    </>
  );
}
