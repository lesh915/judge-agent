import type { AnalysisSummary, ChatMessage, ConfigSnapshot, Finding, ReferenceRun } from '../types/judge';

const BASE_URL = 'http://localhost:8000';

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(error.message || 'API request failed');
  }
  return response.json();
}

export async function getConfig(): Promise<ConfigSnapshot> {
  const data = await apiFetch<any>('/api/config');
  return {
    configDir: data.configDir,
    adapter: data.appDefaults?.adapter || 'reference-weblog-jsonl',
    chatMode: data.appDefaults?.chat_mode || 'deterministic-v2',
    llmProvider: data.llmProfiles?.defaultProvider || 'none',
    model: data.llmProfiles?.defaultModel || '',
    metricCount: data.metrics?.count || 0,
  };
}

export async function getFixtures(): Promise<any[]> {
  const data = await apiFetch<any>('/api/reference/fixtures');
  return data.fixtures || [];
}

export async function runReferenceAgent(fixtureId: string, useLlm: boolean = false): Promise<ReferenceRun> {
  const data = await apiFetch<any>('/api/reference/runs', {
    method: 'POST',
    body: JSON.stringify({
      mode: 'fixture',
      fixtureId,
      useLlm,
    }),
  });
  const run = data.run;
  return {
    id: run.id,
    fixture: run.fixtureId,
    mode: run.mode,
    status: run.status,
    userInput: run.userInput,
    tracePath: run.tracePath,
    reportPath: run.reportPath,
    eventCounts: run.eventCounts,
    timeline: (run.timelinePreview || []).map((ev: any, idx: number) => ({
      id: `ev-${idx}`,
      step: idx + 1,
      type: ev.type,
      title: ev.title,
      detail: ev.detail,
    })),
  };
}

export async function createAnalysis(referenceRunId: string, adapter: string): Promise<any> {
  const data = await apiFetch<any>('/api/analyses', {
    method: 'POST',
    body: JSON.stringify({
      source: { kind: 'reference-run', referenceRunId },
      adapter,
    }),
  });
  return data.analysis;
}

export async function createJudgeSession(analysisId: string, mode: string): Promise<any> {
  const data = await apiFetch<any>('/api/judge/sessions', {
    method: 'POST',
    body: JSON.stringify({
      analysisId,
      mode,
      sessionId: `session-${Date.now()}`,
    }),
  });
  return data.session;
}

export async function sendJudgeMessage(sessionId: string, content: string): Promise<{ message: ChatMessage; session: any }> {
  return apiFetch<{ message: ChatMessage; session: any }>(`/api/judge/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

// Keep mocks for fallback if needed or initial state
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
  timeline: [],
};

export const mockSummary: AnalysisSummary = {
  sessionId: 'weblog-drift-review',
  runCount: 0,
  gateCounts: { pass: 0, warning: 0, block: 0 },
  severityCounts: { low: 0, medium: 0, high: 0, critical: 0 },
  topFindings: [],
};

export const mockConfig: ConfigSnapshot = {
  configDir: 'simple/config',
  adapter: 'reference-weblog-jsonl',
  chatMode: 'deterministic-v2',
  llmProvider: 'none',
  model: '',
  metricCount: 0,
};

export function getMockReviewData() {
  return {
    referenceRun: mockReferenceRun,
    summary: mockSummary,
    findings: [],
    messages: [],
    config: mockConfig,
  };
}
