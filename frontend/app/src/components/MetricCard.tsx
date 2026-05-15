type MetricCardProps = {
  label: string;
  value: string | number;
  note: string;
  tone?: 'default' | 'critical' | 'pass';
};

export function MetricCard({ label, value, note, tone = 'default' }: MetricCardProps) {
  const toneClass = tone === 'critical' ? 'pill-critical' : tone === 'pass' ? 'pill-pass' : 'pill-medium';
  return (
    <div className="feature-tile">
      <div className="section-eyebrow">
        <span>{label}</span>
        <span className={`pill ${toneClass}`}>{tone}</span>
      </div>
      <div className="metric-value">{value}</div>
      <p className="small">{note}</p>
    </div>
  );
}
