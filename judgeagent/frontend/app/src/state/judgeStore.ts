import { getMockReviewData } from '../api/judgeClient';
import type { ChatMessage, Finding } from '../types/judge';

const data = getMockReviewData();

export type JudgeViewState = {
  selectedFindingId: string;
  activeTab: 'review' | 'reference' | 'chat' | 'config';
};

export const initialViewState: JudgeViewState = {
  selectedFindingId: data.findings[0]?.id ?? '',
  activeTab: 'review',
};

export function selectedFinding(findings: Finding[], selectedFindingId: string): Finding | undefined {
  return findings.find((finding) => finding.id === selectedFindingId) ?? findings[0];
}

export function makeUserMessage(content: string): ChatMessage {
  return {
    id: `user-${Date.now()}`,
    role: 'user',
    content,
    createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  };
}

export { data as mockReviewData };
