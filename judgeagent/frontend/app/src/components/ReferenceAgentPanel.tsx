import { useState } from 'react';
import type { ReferenceRun } from '../types/judge';
import { ReferenceChatView } from './ReferenceChatView';
import { Card, Select, Button, Space, Typography, Tag, Divider, Row, Col } from 'antd';
import { PlayCircleOutlined, ExperimentOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

type ReferenceAgentPanelProps = {
  referenceRun: ReferenceRun;
  onRun: (fixtureId: string, useLlm: boolean) => void;
  onJudge: () => void;
  isLoading?: boolean;
};

export function ReferenceAgentPanel({ referenceRun, onRun, onJudge, isLoading }: ReferenceAgentPanelProps) {
  const [selectedFixture, setSelectedFixture] = useState(referenceRun.fixture || 'normal-login-error-spike');
  const [selectedMode, setSelectedMode] = useState('hybrid');

  const handleRun = () => {
    onRun(selectedFixture, selectedMode === 'hybrid');
  };

  return (
    <Card bordered={false} style={{ height: '100%' }} styles={{ body: { padding: '24px', display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, boxSizing: 'border-box' } }}>
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>Reference Agent Controls</Title>
        <Tag color={referenceRun.status === 'succeeded' ? 'success' : referenceRun.status === 'failed' ? 'error' : 'default'} style={{ margin: 0, textTransform: 'uppercase' }}>
          {referenceRun.status}
        </Tag>
      </div>
      
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col span={24}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={14}>
                <Text type="secondary" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Fixture</Text>
                <Select 
                  defaultValue={selectedFixture} 
                  style={{ width: '100%' }}
                  onChange={(val) => setSelectedFixture(val)}
                  options={[
                    { value: 'normal-login-error-spike', label: 'normal-login-error-spike' },
                    { value: 'drift-prompt-output-contract', label: 'drift-prompt-output-contract' },
                    { value: 'drift-wrong-endpoint', label: 'drift-wrong-endpoint' },
                    { value: 'drift-parse-error-ignored', label: 'drift-parse-error-ignored' },
                    { value: 'drift-validation-skipped', label: 'drift-validation-skipped' },
                    { value: 'drift-metric-hallucination', label: 'drift-metric-hallucination' }
                  ]}
                />
              </Col>
              <Col span={10}>
                <Text type="secondary" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '4px' }}>Mode</Text>
                <Select 
                  defaultValue={selectedMode} 
                  style={{ width: '100%' }}
                  onChange={(val) => setSelectedMode(val)}
                  options={[
                    { value: 'no-llm', label: 'Deterministic' },
                    { value: 'hybrid', label: 'Hybrid (LLM)' }
                  ]}
                />
              </Col>
            </Row>
            <Space style={{ marginTop: '8px' }}>
              <Button type="default" icon={<PlayCircleOutlined />} onClick={handleRun} loading={isLoading}>
                Run Reference Agent
              </Button>
              <Button type="primary" icon={<ExperimentOutlined />} onClick={onJudge} disabled={isLoading || referenceRun.status !== 'succeeded'}>
                Judge this trace
              </Button>
            </Space>
          </Space>
        </Col>
      </Row>

      {Object.keys(referenceRun.eventCounts).length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <Text type="secondary" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '8px' }}>Event counts</Text>
          <Space size={[8, 8]} wrap>
            {Object.entries(referenceRun.eventCounts).map(([key, value]) => (
              <Tag key={key} color="default" bordered={false} style={{ margin: 0 }}>
                {key} <strong style={{ marginLeft: '4px' }}>{value}</strong>
              </Tag>
            ))}
          </Space>
        </div>
      )}
      
      <Divider style={{ margin: '16px 0 0 0' }} />

      <div style={{ flexGrow: 1, minHeight: 0, overflowY: 'auto', paddingTop: '16px' }}>
        <ReferenceChatView run={referenceRun} />
      </div>
    </Card>
  );
}
