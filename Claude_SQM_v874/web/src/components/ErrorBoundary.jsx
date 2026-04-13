import { Component } from 'react';

/**
 * ErrorBoundary — React 컴포넌트 에러 시 전체 앱 크래시(흰 화면) 방지
 * v8.7.1 P1-9: Audit 권고사항 반영
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] 컴포넌트 에러:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100vh', padding: 32,
          background: '#0f172a', color: '#f1f5f9', fontFamily: 'sans-serif',
        }}>
          <h2 style={{ color: '#f87171', marginBottom: 16 }}>⚠️ 오류가 발생했습니다</h2>
          <p style={{ color: '#94a3b8', marginBottom: 24, maxWidth: 480, textAlign: 'center' }}>
            예기치 않은 오류가 발생했습니다. 페이지를 새로고침해주세요.
          </p>
          <pre style={{
            background: '#1e293b', padding: 16, borderRadius: 8, fontSize: 12,
            maxWidth: 600, overflow: 'auto', color: '#fbbf24', marginBottom: 24,
          }}>
            {this.state.error?.toString()}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 24px', background: '#3b82f6', color: '#fff',
              border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14,
            }}
          >
            새로고침
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
