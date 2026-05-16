import { Card, Statistic, Typography } from 'antd';
import { CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

const { Text } = Typography;

type MetricCardProps = {
  label: string;
  value: string | number;
  note?: string;
  tone?: 'pass' | 'warning' | 'critical';
};

export function MetricCard({ label, value, note, tone }: MetricCardProps) {
  let color = '#1e293b';
  let prefix = null;
  
  if (tone === 'pass') {
    color = '#10b981';
    prefix = <CheckCircleOutlined />;
  } else if (tone === 'warning') {
    color = '#f59e0b';
    prefix = <ExclamationCircleOutlined />;
  } else if (tone === 'critical') {
    color = '#ef4444';
    prefix = <CloseCircleOutlined />;
  }

  return (
    <Card bordered={false} style={{ height: '100%', backgroundColor: '#f8fafc', boxShadow: 'inset 0 0 0 1px #e2e8f0' }}>
      <Statistic 
        title={<span style={{ fontWeight: 600, color: '#64748b', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.05em' }}>{label}</span>}
        value={value}
        valueStyle={{ color, fontWeight: 700 }}
        prefix={prefix}
      />
      {note && (
        <div style={{ marginTop: '8px' }}>
          <Text type="secondary" style={{ fontSize: '0.85rem' }}>{note}</Text>
        </div>
      )}
    </Card>
  );
}
