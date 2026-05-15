import type { AnalysisSummary, ChatMessage, ConfigSnapshot, Finding, ReferenceRun } from '../types/judge';

export const mockReferenceRun: ReferenceRun = {
  id: 'ref-normal-login-error-spike-001',
  fixture: 'normal-login-error-spike',
  mode: 'fixture',
  status: 'succeeded',
  tracePath: 'reference_agent/weblog_agent/traces/normal-login-error-spike.jsonl',
  reportPath: 'reference_agent/weblog_agent/reports/normal-login-error-spike.md',
  eventCounts: {
    react_step: 9,
    tool_end: 7,
    mcp_end: 1,
    validation_result: 1,
    final_output: 1,
  },
  timeline: [
    { id: 't1', step: 1, type: 'thought', title: 'Parse request scope', detail: 'User asked for /api/login 5xx error-rate analysis.' },
    { id: 't2', step: 2, type: 'action', title: 'parse_user_request', detail: 'targetPath=/api/login, metric=error_rate' },
    { id: 't3', step: 3, type: 'tool', title: 'compute_log_metrics', detail: 'request_count=80, error_rate=0.15, p95_latency=1400ms' },
    { id: 't4', step: 4, type: 'rag', title: 'retrieve_runbook', detail: 'Retrieved login incident runbook and dependency hints.' },
    { id: 't5', step: 5, type: 'mcp', title: 'get_service_context', detail: 'owner=identity-platform, dependencies=session-store, auth-db' },
    { id: 't6', step: 6, type: 'validation', title: 'validate_findings', detail: 'Metrics, evidence, RAG, MCP, and output contract checked.' },
    { id: 't7', step: 7, type: 'final', title: 'finalize report', detail: 'Markdown report emitted with confidence and limitations.' },
  ],
};

export const mockFindings: Finding[] = [
  {
    id: 'JD-001',
    metric: 'validation_path_coverage',
    category: 'LangGraph Flow',
    severity: 'critical',
    confidence: 0.98,
    expected: 'validate_findings node and validation_result events must run before final output.',
    actual: 'Validation path was missing or explicitly skipped in the drift fixture.',
    recommendation: 'Restore validation edge and block finalization when validation is absent.',
    evidence: ['node_start sequence=[initialize_agent, react_agent, finalize]', 'validation_result_count=0', 'validation_skipped_edge=true'],
    runId: 'ref-normal-login-error-spike-001',
    priority: 4,
  },
  {
    id: 'JD-002',
    metric: 'target_endpoint_consistency',
    category: 'Tool Use',
    severity: 'high',
    confidence: 0.96,
    expected: 'All tool arguments and metric paths should use /api/login.',
    actual: 'Trace used /api/payment in a metric top_paths result.',
    recommendation: 'Ground filter/query arguments in parsed targetPath and add argument validation.',
    evidence: ['metrics.top_paths contains /api/payment, expected /api/login'],
    runId: 'ref-normal-login-error-spike-001',
    priority: 2,
  },
  {
    id: 'JD-003',
    metric: 'rag_context_presence_and_usage',
    category: 'Context / Retrieval',
    severity: 'medium',
    confidence: 0.85,
    expected: 'RAG runbook retrieval should occur for incident analysis.',
    actual: 'RAG context was missing from the final report.',
    recommendation: 'Call retrieve_runbook before final report and separate RAG from measured evidence.',
    evidence: ['No tool_end(retrieve_runbook) event found.'],
    runId: 'ref-normal-login-error-spike-001',
    priority: 6,
  },
];

export const mockSummary: AnalysisSummary = {
  sessionId: 'weblog-drift-review',
  runCount: 3,
  gateCounts: { pass: 1, warning: 1, block: 1 },
  severityCounts: { low: 0, medium: 1, high: 1, critical: 1 },
  topFindings: mockFindings,
};

export const mockMessages: ChatMessage[] = [
  {
    id: 'm1',
    role: 'user',
    content: '왜 block이야?',
    createdAt: '22:14',
  },
  {
    id: 'm2',
    role: 'assistant',
    content: 'block의 직접 원인은 critical finding인 validation_path_coverage입니다. final output 전에 validate_findings node와 validation_result가 실행되어야 하는데, trace에서는 validation path가 누락되거나 skip되었습니다.',
    createdAt: '22:14',
    focusedFindingId: 'JD-001',
    focusedMetric: 'validation_path_coverage',
    toolCalls: [{ name: 'explain_gate', status: 'success', summary: 'block 1개, warning 1개 확인' }],
  },
];

export const mockConfig: ConfigSnapshot = {
  configDir: 'simple/config',
  adapter: 'reference-weblog-jsonl',
  chatMode: 'deterministic-v2',
  llmProvider: 'ollama',
  model: 'qwen3.5:latest',
  metricCount: 35,
};

export function getMockReviewData() {
  return {
    referenceRun: mockReferenceRun,
    summary: mockSummary,
    findings: mockFindings,
    messages: mockMessages,
    config: mockConfig,
  };
}
