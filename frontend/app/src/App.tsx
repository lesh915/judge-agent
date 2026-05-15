import { useMemo, useState } from 'react';
import { ChatPanel } from './components/ChatPanel';
import { EvidenceBlock } from './components/EvidenceBlock';
import { FindingsPanel } from './components/FindingsPanel';
import { MetricCard } from './components/MetricCard';
import { ReferenceAgentPanel } from './components/ReferenceAgentPanel';
import { RunCompareTable } from './components/RunCompareTable';
import { Sidebar } from './components/Sidebar';
import { TraceUploadCard } from './components/TraceUploadCard';
import { AppShell } from './components/AppShell';
import { initialViewState, mockReviewData, selectedFinding } from './state/judgeStore';

function App() {
  const { referenceRun, summary, findings, messages, config } = mockReviewData;
  const [selectedFindingId, setSelectedFindingId] = useState(initialViewState.selectedFindingId);
  const focusedFinding = useMemo(() => selectedFinding(findings, selectedFindingId), [findings, selectedFindingId]);

  return (
    <AppShell>
      <div className="layout">
        <Sidebar referenceRun={referenceRun} config={config} />

        <main className="main-stack">
          <section className="card">
            <div className="section-eyebrow"><span>Review workspace</span><span>Mock MVP</span></div>
            <h1>Review agent drift from trace evidence.</h1>
            <p>
              Run the Reference Web Log ReAct Agent, inspect the generated trace, then ask Judge Agent to explain
              drift findings with deterministic evidence.
            </p>
            <div className="grid-3">
              <MetricCard label="Gate status" value="Block" note={`${summary.gateCounts.block} blocked run needs validation review.`} tone="critical" />
              <MetricCard label="Severity" value={summary.severityCounts.critical} note="critical finding from validation path coverage." tone="critical" />
              <MetricCard label="Metrics" value={config.metricCount} note="loaded from file-based config registry." tone="pass" />
            </div>
          </section>

          <ReferenceAgentPanel referenceRun={referenceRun} />
          <FindingsPanel findings={findings} selectedFindingId={selectedFindingId} onSelectFinding={setSelectedFindingId} />
          <RunCompareTable summary={summary} />
          <ChatPanel messages={messages} />
        </main>

        <aside className="detail-panel">
          <TraceUploadCard />
          <EvidenceBlock finding={focusedFinding} />
          <section className="card">
            <div className="section-eyebrow"><span>Config snapshot</span><span>read-only</span></div>
            <p><span className="badge-uppercase">Config dir</span><br /><span className="inline-code">{config.configDir}</span></p>
            <p><span className="badge-uppercase">LLM provider</span><br /><span className="inline-code">{config.llmProvider}</span></p>
            <p><span className="badge-uppercase">Model</span><br /><span className="inline-code">{config.model}</span></p>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}

export default App;
