import type { ReferenceRun } from '../types/judge';
import { ReferenceRunTimeline } from './ReferenceRunTimeline';

type ReferenceAgentPanelProps = {
  referenceRun: ReferenceRun;
};

export function ReferenceAgentPanel({ referenceRun }: ReferenceAgentPanelProps) {
  return (
    <section className="doc-card">
      <div className="section-eyebrow">
        <span>Reference Agent Lab</span>
        <span className="pill pill-pass">{referenceRun.status}</span>
      </div>
      <div className="grid-2">
        <div>
          <h2>Run Web Log ReAct Agent</h2>
          <p>
            Fixture <span className="inline-code">{referenceRun.fixture}</span> produced a trace with Tool, RAG, MCP,
            validation, and final output events. Use this as the source trace for Judge Agent analysis.
          </p>
          <div className="grid-2">
            <label>
              <span className="badge-uppercase">Fixture</span>
              <select className="select" defaultValue={referenceRun.fixture}>
                <option>{referenceRun.fixture}</option>
                <option>validation-skipped-drift</option>
                <option>metric-hallucination-drift</option>
              </select>
            </label>
            <label>
              <span className="badge-uppercase">Mode</span>
              <select className="select" defaultValue="no-llm">
                <option value="no-llm">no-llm deterministic</option>
                <option value="hybrid">LLM enabled</option>
              </select>
            </label>
          </div>
          <p>
            <button className="button-secondary">Run reference agent</button>{' '}
            <button className="button-primary">Judge this trace</button>
          </p>
        </div>
        <div>
          <div className="section-eyebrow"><span>Event counts</span><span>Trace</span></div>
          <table className="table">
            <tbody>
              {Object.entries(referenceRun.eventCounts).map(([key, value]) => (
                <tr key={key}><td><span className="inline-code">{key}</span></td><td>{value}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="section-eyebrow"><span>ReAct timeline</span><span>{referenceRun.timeline.length} steps</span></div>
      <ReferenceRunTimeline events={referenceRun.timeline} />
    </section>
  );
}
