import type { ReferenceRun } from '../types/judge';
import { Typography, Collapse, Tag } from 'antd';
import { UserOutlined, RobotOutlined, SettingOutlined } from '@ant-design/icons';

const { Text } = Typography;

export function ReferenceChatView({ run }: { run: ReferenceRun }) {
  const internalEvents = run.timeline.filter(e => e.type !== 'final' && e.type !== 'final_output');
  const finalEvent = run.timeline.find(e => e.type === 'final' || e.type === 'final_output');

  if (run.timeline.length === 0) {
    return (
      <div style={{ padding: '40px 24px', textAlign: 'center' }}>
        <Text type="secondary" italic>No conversation history. Run the agent to start.</Text>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', padding: '16px 0' }}>
      {/* User Message */}
      {run.userInput && (
        <div style={{ alignSelf: 'flex-end', backgroundColor: '#e6f4ff', color: '#0f172a', padding: '12px 16px', borderRadius: '12px', borderBottomRightRadius: '2px', maxWidth: '85%', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            <UserOutlined style={{ color: '#1677ff', fontSize: '12px' }} />
            <Text style={{ fontSize: '0.75rem', color: '#1677ff', fontWeight: 600 }}>USER</Text>
          </div>
          <div style={{ lineHeight: 1.5 }}>{run.userInput}</div>
        </div>
      )}

      {/* Agent Response */}
      <div style={{ alignSelf: 'flex-start', backgroundColor: '#fff', border: '1px solid #e2e8f0', color: '#0f172a', padding: '16px', borderRadius: '12px', borderBottomLeftRadius: '2px', maxWidth: '100%', width: '100%', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <RobotOutlined style={{ color: '#52c41a', fontSize: '16px' }} />
          <Text style={{ fontSize: '0.8rem', color: '#52c41a', fontWeight: 600 }}>REFERENCE AGENT</Text>
          <Tag color={run.status === 'succeeded' ? 'success' : 'warning'} bordered={false} style={{ margin: 0, fontSize: '0.65rem' }}>
            {run.status.toUpperCase()}
          </Tag>
        </div>

        {/* Thinking Process (Collapsible) */}
        {internalEvents.length > 0 && (
          <Collapse 
            ghost 
            items={[{
              key: '1',
              label: <Text type="secondary" style={{ fontWeight: 500 }}><SettingOutlined style={{ marginRight: '6px' }} /> Thinking Process ({internalEvents.length} steps)</Text>,
              children: (
                <div style={{ maxHeight: '350px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {internalEvents.map(event => (
                    <div key={event.id} style={{ fontSize: '0.85rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <Tag color="default" bordered={false} style={{ margin: 0, fontSize: '0.65rem' }}>{event.type.toUpperCase()}</Tag>
                        <Text strong style={{ color: '#334155' }}>{event.title}</Text>
                      </div>
                      <div style={{ color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', paddingLeft: '8px', borderLeft: '2px solid #e2e8f0', marginLeft: '4px' }}>
                        {event.detail}
                      </div>
                    </div>
                  ))}
                </div>
              )
            }]} 
            style={{ backgroundColor: '#fafafa', borderRadius: '8px', border: '1px solid #f0f0f0', marginBottom: '16px' }} 
          />
        )}

        {/* Final Response */}
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, color: '#1e293b' }}>
          {finalEvent ? finalEvent.detail : (
            run.status === 'failed' ? (
              <Text type="danger">Agent execution failed.</Text>
            ) : run.status === 'succeeded' ? (
              <Text type="warning" italic>Processing final results...</Text>
            ) : (
              <Text type="secondary" italic>Thinking...</Text>
            )
          )}
        </div>
      </div>
    </div>
  );
}
