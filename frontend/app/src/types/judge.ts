export type Gate = 'pass' | 'warning' | 'block';
export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type ReferenceRunStatus = 'queued' | 'running' | 'succeeded' | 'failed';
export type ReferenceRunMode = 'fixture' | 'custom-analysis' | 'chat';

export type ReferenceEvent = {
  id: string;
  step: number;
  type: 'thought' | 'action' | 'observation' | 'tool' | 'rag' | 'mcp' | 'validation' | 'final';
  title: string;
  detail: string;
  payload?: Record<string, unknown>;
};

export type ReferenceRun = {
  id: string;
  fixture?: string;
  mode: ReferenceRunMode;
  status: ReferenceRunStatus;
  tracePath?: string;
  reportPath?: string;
  eventCounts: Record<string, number>;
  timeline: ReferenceEvent[];
};

export type Finding = {
  id: string;
  metric: string;
  category: string;
  severity: Severity;
  confidence: number;
  expected: string;
  actual: string;
  recommendation: string;
  evidence: string[];
  runId: string;
  priority?: number;
};

export type AnalysisSummary = {
  sessionId: string;
  runCount: number;
  gateCounts: Record<Gate, number>;
  severityCounts: Record<Severity, number>;
  topFindings: Finding[];
};

export type ToolCall = {
  name: string;
  status: 'success' | 'fallback' | 'error';
  summary: string;
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  createdAt: string;
  toolCalls?: ToolCall[];
  focusedFindingId?: string;
  focusedMetric?: string;
};

export type ConfigSnapshot = {
  configDir: string;
  adapter: string;
  chatMode: string;
  llmProvider: string;
  model: string;
  metricCount: number;
};
