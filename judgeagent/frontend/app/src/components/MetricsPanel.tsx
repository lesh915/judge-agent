import type { AnalysisSummary, Finding } from '../types/judge';
import { Typography, Tag, Progress, Collapse, Space, Row, Col, Badge } from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

type MetricsPanelProps = {
  summary: AnalysisSummary | null;
  findings: Finding[];
};

const SEVERITY_CONFIG = {
  critical: { color: '#ef4444', bg: '#fef2f2', border: '#fecaca', label: 'Critical' },
  high:     { color: '#f97316', bg: '#fff7ed', border: '#fed7aa', label: 'High' },
  medium:   { color: '#f59e0b', bg: '#fffbeb', border: '#fde68a', label: 'Medium' },
  low:      { color: '#10b981', bg: '#f0fdf4', border: '#bbf7d0', label: 'Low' },
};

const GATE_CONFIG = {
  block:   { color: '#ef4444', bg: '#fef2f2', border: '#fecaca', icon: <CloseCircleOutlined />,    label: 'BLOCK' },
  warning: { color: '#f59e0b', bg: '#fffbeb', border: '#fde68a', icon: <ExclamationCircleOutlined />, label: 'WARNING' },
  pass:    { color: '#10b981', bg: '#f0fdf4', border: '#bbf7d0', icon: <CheckCircleOutlined />,    label: 'PASS' },
};

function SeverityBadge({ severity }: { severity: string }) {
  const cfg = SEVERITY_CONFIG[severity as keyof typeof SEVERITY_CONFIG];
  if (!cfg) return <Tag>{severity}</Tag>;
  return (
    <Tag style={{ color: cfg.color, backgroundColor: cfg.bg, borderColor: cfg.border, fontWeight: 600, fontSize: '0.7rem' }}>
      {cfg.label}
    </Tag>
  );
}

function FindingItem({ finding }: { finding: Finding }) {
  const confidence = Math.round(finding.confidence * 100);
  const items = [
    {
      key: finding.id,
      label: (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <SeverityBadge severity={finding.severity} />
          <Text strong style={{ fontSize: '0.85rem' }}>{finding.metric}</Text>
          <Text type="secondary" style={{ fontSize: '0.75rem' }}>· {finding.category}</Text>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Text type="secondary" style={{ fontSize: '0.75rem' }}>Confidence</Text>
            <Progress
              percent={confidence}
              size="small"
              showInfo={false}
              strokeColor={confidence >= 80 ? '#ef4444' : confidence >= 60 ? '#f59e0b' : '#10b981'}
              style={{ width: 60 }}
            />
            <Text style={{ fontSize: '0.75rem', fontWeight: 600 }}>{confidence}%</Text>
          </div>
        </div>
      ),
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', padding: '4px 0' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Expected</Text>
              <Text style={{ fontSize: '0.82rem' }}>{finding.expected}</Text>
            </Col>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Actual</Text>
              <Text style={{ fontSize: '0.82rem', color: '#ef4444' }}>{finding.actual}</Text>
            </Col>
          </Row>
          {finding.recommendation && (
            <div style={{ backgroundColor: '#f8fafc', borderRadius: 6, padding: '8px 12px', borderLeft: '3px solid #1677ff' }}>
              <Text type="secondary" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 2 }}>Recommendation</Text>
              <Text style={{ fontSize: '0.82rem' }}>{finding.recommendation}</Text>
            </div>
          )}
          {finding.evidence && finding.evidence.length > 0 && (
            <div>
              <Text type="secondary" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Evidence</Text>
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                {finding.evidence.map((e, i) => (
                  <Text key={i} style={{ fontSize: '0.8rem', color: '#475569' }}>· {e}</Text>
                ))}
              </Space>
            </div>
          )}
        </div>
      ),
    },
  ];

  return <Collapse ghost size="small" items={items} style={{ border: '1px solid #e2e8f0', borderRadius: 8, backgroundColor: '#fff', marginBottom: 6 }} />;
}

export function MetricsPanel({ summary, findings }: MetricsPanelProps) {
  if (!summary) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <InfoCircleOutlined style={{ fontSize: 24, color: '#94a3b8', marginBottom: 8 }} />
        <div><Text type="secondary">Run Reference Agent and click "Judge this trace" to see metrics.</Text></div>
      </div>
    );
  }

  const gateKey = summary.gateCounts.block > 0 ? 'block' : summary.gateCounts.warning > 0 ? 'warning' : 'pass';
  const gate = GATE_CONFIG[gateKey];
  const totalFindings = findings.length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Gate + Severity summary row */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'stretch' }}>
        {/* Gate Status */}
        <div style={{ flex: '0 0 22%', backgroundColor: gate.bg, border: `1px solid ${gate.border}`, borderRadius: 10, padding: '12px 10px', textAlign: 'center' }}>
          <div style={{ fontSize: 20, color: gate.color, marginBottom: 2 }}>{gate.icon}</div>
          <Text style={{ fontWeight: 700, fontSize: '0.95rem', color: gate.color, display: 'block' }}>{gate.label}</Text>
          <Text type="secondary" style={{ fontSize: '0.65rem' }}>Gate Status</Text>
        </div>

        {/* Severity counts */}
        {(['critical', 'high', 'medium', 'low'] as const).map((sev) => {
          const cfg = SEVERITY_CONFIG[sev];
          const count = summary.severityCounts[sev] ?? 0;
          return (
            <div key={sev} style={{ flex: 1, backgroundColor: count > 0 ? cfg.bg : '#f8fafc', border: `1px solid ${count > 0 ? cfg.border : '#e2e8f0'}`, borderRadius: 10, padding: '10px 6px', textAlign: 'center' }}>
              <Text style={{ fontWeight: 700, fontSize: '1.2rem', color: count > 0 ? cfg.color : '#94a3b8', display: 'block' }}>{count}</Text>
              <Text style={{ fontSize: '0.65rem', color: count > 0 ? cfg.color : '#94a3b8', fontWeight: 600 }}>{cfg.label}</Text>
            </div>
          );
        })}

        {/* Total findings */}
        <div style={{ flex: '0 0 12%', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '10px 6px', textAlign: 'center' }}>
          <Text style={{ fontWeight: 700, fontSize: '1.2rem', color: '#1e293b', display: 'block' }}>{totalFindings}</Text>
          <Text type="secondary" style={{ fontSize: '0.65rem', fontWeight: 600 }}>Total</Text>
        </div>
      </div>

      {/* Top Findings list */}
      {summary.topFindings && summary.topFindings.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Title level={5} style={{ margin: 0 }}>Top Findings</Title>
            <Badge count={summary.topFindings.length} color="#64748b" />
          </div>
          {summary.topFindings.map((f) => (
            <FindingItem key={f.id} finding={f} />
          ))}
        </div>
      )}
    </div>
  );
}
