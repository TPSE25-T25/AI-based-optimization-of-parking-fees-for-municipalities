// ERROR BOUNDARY - Catches React render errors and shows a readable message
// instead of a blank white page (React 18 unmounts the tree on uncaught errors).

import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary] Caught error:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          height: '100vh', background: '#fafafa', fontFamily: 'sans-serif',
          padding: '2rem',
        }}>
          <div style={{
            maxWidth: 480, background: '#fff', border: '1px solid #ddd',
            borderRadius: 6, padding: '2rem', boxShadow: '0 2px 8px rgba(0,0,0,.08)',
          }}>
            <h2 style={{ color: '#d32f2f', margin: '0 0 .75rem' }}>Something went wrong</h2>
            <pre style={{
              background: '#f5f5f5', borderRadius: 4, padding: '1rem',
              fontSize: 12, overflowX: 'auto', whiteSpace: 'pre-wrap',
              wordBreak: 'break-word', color: '#333',
            }}>
              {this.state.error?.toString()}
            </pre>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{
                marginTop: '1rem', padding: '8px 18px', background: '#2b80ff',
                color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer',
              }}
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
