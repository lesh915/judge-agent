import type { ReferenceEvent } from '../types/judge';

type ReferenceRunTimelineProps = {
  events: ReferenceEvent[];
};

const typeLabels: Record<ReferenceEvent['type'], string> = {
  thought: 'Thought',
  action: 'Action',
  observation: 'Observation',
  tool: 'Tool',
  rag: 'RAG',
  mcp: 'MCP',
  validation: 'Validation',
  final: 'Final',
};

export function ReferenceRunTimeline({ events }: ReferenceRunTimelineProps) {
  return (
    <div className="timeline">
      {events.map((event) => (
        <div className="timeline-row" key={event.id}>
          <div className="timeline-step">{event.step}</div>
          <div className="badge-uppercase">{typeLabels[event.type]}</div>
          <div>
            <strong>{event.title}</strong>
            <p className="small">{event.detail}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
