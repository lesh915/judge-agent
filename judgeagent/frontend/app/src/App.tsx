import { useEffect, useState } from 'react';
import { ChatPanel } from './components/ChatPanel';
import { ReferenceAgentPanel } from './components/ReferenceAgentPanel';
import { MetricCard } from './components/MetricCard';
import * as api from './api/judgeClient';
import type { ChatMessage, ConfigSnapshot, ReferenceRun, AnalysisSummary, Finding } from './types/judge';
import { ConfigProvider, Layout, Row, Col, Typography, message } from 'antd';

const { Header, Content } = Layout;
const { Title } = Typography;

function App() {
  const [config, setConfig] = useState<ConfigSnapshot | null>(null);
  const [referenceRun, setReferenceRun] = useState<ReferenceRun | null>(null);
  const [summary, setSummary] = useState<AnalysisSummary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    async function init() {
      try {
        const cfg = await api.getConfig();
        setConfig(cfg);
        setMessages([{
          id: `sys-welcome`,
          role: 'system',
          content: '안녕하세요! 좌측 패널에서 레퍼런스 에이전트를 실행하고 트레이스를 모니터링할 수 있습니다.\n실행 완료 후 [Judge this trace]를 클릭하여 이곳에서 결과를 확인하세요.',
          createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      } catch (e) {
        console.error('Failed to load config', e);
      }
    }
    init();
  }, []);

  const handleRun = async (fixtureId: string, useLlm: boolean) => {
    setIsLoading(true);
    try {
      const run = await api.runReferenceAgent(fixtureId, useLlm);
      setReferenceRun(run);
      // Reset judge state
      setSummary(null);
      setFindings([]);
      setSessionId(null);
      setMessages([{
        id: `sys-${Date.now()}`,
        role: 'system',
        content: `✅ 실행 완료 (Fixture: ${fixtureId}).\n좌측 상단의 [Judge this trace] 버튼을 클릭하여 트레이스를 분석하세요.`,
        createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
    } catch (e) {
      messageApi.error('Failed to run: ' + e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleJudge = async () => {
    if (!referenceRun) return;
    if (!config) return;

    setIsLoading(true);
    setMessages([{
      id: `sys-j-${Date.now()}`,
      role: 'system',
      content: '🔍 트레이스 검증 및 지표 분석을 시작합니다...',
      createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);

    try {
      const analysis = await api.createAnalysis(referenceRun.id, config.adapter);
      setFindings(analysis.findings || []);
      setSummary(analysis.summary);
      
      const session = await api.createJudgeSession(analysis.id, config.chatMode);
      setSessionId(session.id);
      
      setMessages(prev => [...prev, {
        id: `sys-r-${Date.now()}`,
        role: 'system',
        content: `💬 대화형 세션이 준비되었습니다.\n상단의 지표(Metrics)를 확인하고 자유롭게 질문해 주세요!`,
        createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        actionButtons: [
          { label: "왜 block이야?", command: "왜 block이야?" },
          { label: "주요 Finding에 대한 근거를 보여줘", command: "주요 Finding에 대한 근거를 보여줘" }
        ]
      }]);
    } catch (e) {
      messageApi.error('Failed to judge: ' + e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!sessionId) {
      messageApi.warning('Please judge a trace first.');
      return;
    }
    
    setMessages(prev => [...prev, {
      id: `u-${Date.now()}`,
      role: 'user',
      content,
      createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }]);
    
    setIsLoading(true);
    try {
      const { message } = await api.sendJudgeMessage(sessionId, content);
      setMessages(prev => [...prev, message]);
    } catch (e) {
      messageApi.error('Failed to send message: ' + e);
    } finally {
      setIsLoading(false);
    }
  };

  const safeReferenceRun = referenceRun || {
    id: '', mode: 'fixture', status: 'queued', eventCounts: {}, timeline: []
  } as ReferenceRun;

  return (
    <ConfigProvider theme={{ token: { colorPrimary: '#1677ff', borderRadius: 8, fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif' } }}>
      {contextHolder}
      <Layout style={{ height: '100vh', overflow: 'hidden' }}>
        <Header style={{ backgroundColor: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', padding: '0 24px' }}>
          <Title level={3} style={{ margin: 0, color: '#0f172a' }}>Judge Agent Workspace</Title>
        </Header>
        
        <Content style={{ padding: '24px', backgroundColor: '#f1f5f9', overflow: 'hidden' }}>
          <Row gutter={24} style={{ height: '100%' }}>
            
            {/* Left Panel: Reference Agent Monitor */}
            <Col span={12} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <div style={{ flexGrow: 1, minHeight: 0, overflowY: 'auto', borderRadius: '8px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)' }}>
                <ReferenceAgentPanel 
                  referenceRun={safeReferenceRun} 
                  onRun={handleRun} 
                  onJudge={handleJudge} 
                  isLoading={isLoading} 
                />
              </div>
            </Col>

            {/* Right Panel: Judge Metrics & Chat */}
            <Col span={12} style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* Metrics Section */}
              <div style={{ borderRadius: '8px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', backgroundColor: '#fff', padding: '20px' }}>
                <Title level={4} style={{ margin: '0 0 16px 0' }}>Judge Agent Metrics</Title>
                <Row gutter={16}>
                  <Col span={12}>
                    <MetricCard
                      label="Gate Status"
                      value={summary ? (summary.gateCounts.block > 0 ? 'Block' : summary.gateCounts.warning > 0 ? 'Warning' : 'Pass') : '-'}
                      note={summary ? (summary.gateCounts.block > 0 ? 'Action required.' : 'No critical drift.') : 'Run judge to see status'}
                      tone={summary ? (summary.gateCounts.block > 0 ? 'critical' : summary.gateCounts.warning > 0 ? 'warning' : 'pass') : undefined}
                    />
                  </Col>
                  <Col span={12}>
                    <MetricCard
                      label="Critical Findings"
                      value={summary ? summary.severityCounts.critical : '-'}
                      note={summary ? `Out of ${findings.length} total findings` : 'Run judge to see findings'}
                      tone={summary && summary.severityCounts.critical > 0 ? 'critical' : 'pass'}
                    />
                  </Col>
                </Row>
              </div>
              
              {/* Chat Section */}
              <div style={{ flexGrow: 1, minHeight: 0, overflow: 'hidden', borderRadius: '8px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)' }}>
                <ChatPanel messages={messages} onSendMessage={handleSendMessage} isLoading={isLoading} />
              </div>
              
            </Col>
          </Row>
        </Content>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
