import type { ChatMessage } from '../types/judge';

type ChatPanelProps = {
  messages: ChatMessage[];
};

export function ChatPanel({ messages }: ChatPanelProps) {
  return (
    <section className="doc-card">
      <div className="section-eyebrow"><span>Conversational Judge</span><span>deterministic-v2</span></div>
      <div className="chat-list">
        {messages.map((message) => (
          <article className={`message ${message.role}`} key={message.id}>
            <div className="message-meta"><span>{message.role}</span><span>{message.createdAt}</span></div>
            <div>{message.content}</div>
            {message.focusedMetric ? <p><span className="inline-code">{message.focusedMetric}</span></p> : null}
            {message.toolCalls?.map((tool) => (
              <span className="pill tool-chip" key={tool.name}>{tool.name} · {tool.status}</span>
            ))}
          </article>
        ))}
      </div>
      <div style={{ marginTop: 14 }}>
        <textarea className="textarea" placeholder="왜 block이야? · JD-001 근거 · run 비교" defaultValue="JD-001 근거 보여줘" />
        <p><button className="button-secondary">Ask Judge Agent</button></p>
      </div>
    </section>
  );
}
