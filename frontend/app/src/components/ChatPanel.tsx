import type { ChatMessage } from '../types/judge';
import { Card, Input, Button, Typography, Tag, Space, Divider } from 'antd';
import { SendOutlined, UserOutlined, SafetyCertificateOutlined } from '@ant-design/icons';

const { Text, Title } = Typography;

type ChatPanelProps = {
  messages: ChatMessage[];
  onSendMessage: (content: string) => void;
  isLoading?: boolean;
};

export function ChatPanel({ messages, onSendMessage, isLoading }: ChatPanelProps) {
  const handleSend = (value: string) => {
    if (value.trim()) {
      onSendMessage(value);
    }
  };

  return (
    <Card bordered={false} bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '16px 24px', borderBottom: '1px solid #f0f0f0' }}>
        <Title level={4} style={{ margin: 0 }}>Judge Agent Chat</Title>
        <Text type="secondary" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Deterministic Evidence</Text>
      </div>
      
      <div className="chat-list" style={{ flexGrow: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', backgroundColor: '#fafafa' }}>
        {messages.map((message) => (
          <div 
            key={message.id} 
            style={{ 
              maxWidth: '85%', 
              alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: message.role === 'user' ? '#1677ff' : message.role === 'system' ? '#fff' : '#fff',
              padding: '16px',
              borderRadius: '12px',
              borderBottomRightRadius: message.role === 'user' ? '2px' : '12px',
              borderBottomLeftRadius: message.role === 'user' ? '12px' : '2px',
              boxShadow: message.role === 'system' ? 'none' : '0 1px 2px rgba(0,0,0,0.05)',
              border: message.role === 'system' ? '1px dashed #d9d9d9' : '1px solid #f0f0f0',
              width: message.role === 'system' ? '100%' : 'auto'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              {message.role === 'user' ? <UserOutlined style={{ color: '#bae0ff' }} /> : <SafetyCertificateOutlined style={{ color: message.role === 'system' ? '#8c8c8c' : '#722ed1' }} />}
              <Text style={{ fontSize: '0.75rem', color: message.role === 'user' ? '#bae0ff' : '#8c8c8c', fontWeight: 600 }}>
                {message.role.toUpperCase()}
              </Text>
              <Text style={{ fontSize: '0.7rem', color: message.role === 'user' ? '#91caff' : '#bfbfbf' }}>
                {message.createdAt}
              </Text>
            </div>
            
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, color: message.role === 'user' ? '#fff' : '#262626' }}>
              {message.content}
            </div>
            
            {message.focusedMetric && (
              <div style={{ marginTop: '12px' }}>
                <Tag color={message.role === 'user' ? 'blue' : 'purple'} bordered={false}>
                  <Text code style={{ backgroundColor: 'transparent', color: 'inherit' }}>{message.focusedMetric}</Text>
                </Tag>
              </div>
            )}
            
            {message.toolCalls && message.toolCalls.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <Space size={[0, 8]} wrap>
                  {message.toolCalls.map((tool) => (
                    <Tag key={tool.name} color="default" bordered={false}>
                      {tool.name} <Text type="secondary">· {tool.status}</Text>
                    </Tag>
                  ))}
                </Space>
              </div>
            )}
            
            {message.actionButtons && message.actionButtons.length > 0 && (
              <>
                <Divider style={{ margin: '12px 0', borderColor: message.role === 'user' ? 'rgba(255,255,255,0.2)' : '#f0f0f0' }} />
                <Space size={[8, 8]} wrap>
                  {message.actionButtons.map((action, idx) => (
                    <Button 
                      key={idx}
                      shape="round"
                      onClick={() => onSendMessage(action.command)}
                      disabled={isLoading}
                      style={{ fontSize: '0.85rem' }}
                    >
                      {action.label}
                    </Button>
                  ))}
                </Space>
              </>
            )}
          </div>
        ))}
      </div>
      
      <div style={{ padding: '16px 24px', borderTop: '1px solid #f0f0f0', backgroundColor: '#fff' }}>
        <Input.Search
          placeholder="Type a command (e.g., /run) or ask a question..."
          enterButton={<Button type="primary" icon={<SendOutlined />} disabled={isLoading}>Send</Button>}
          size="large"
          onSearch={handleSend}
          disabled={isLoading}
        />
      </div>
    </Card>
  );
}
