'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
  apiEndpoint?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  isSubmitting: boolean;
  submitted: boolean;
}

export class CrashBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    isSubmitting: false,
    submitted: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null, isSubmitting: false, submitted: false };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReport = async () => {
    this.setState({ isSubmitting: true });
    
    const payload = {
      title: `Crash: ${this.state.error?.message || 'Unknown Error'}`,
      description: `Uncaught Exception in React Tree.\n\nComponent Stack:\n${this.state.errorInfo?.componentStack}`,
      category: 'crash',
      severity: 'critical',
      source: 'crash-screen',
      system_info: {
        userAgent: navigator.userAgent,
        url: window.location.href,
        stack: this.state.error?.stack
      }
    };

    try {
      const endpoint = this.props.apiEndpoint || '/api/v1/issues';
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      this.setState({ submitted: true, isSubmitting: false });
    } catch (e) {
      console.error(e);
      this.setState({ isSubmitting: false });
      alert('Failed to send crash report.');
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl p-8 max-w-2xl w-full border border-red-200 dark:border-red-900">
            <h1 className="text-2xl font-bold text-red-600 dark:text-red-500 mb-4">
              Something went wrong.
            </h1>
            <p className="text-slate-600 dark:text-slate-300 mb-6">
              The application encountered an unexpected error.
            </p>
            
            <div className="bg-slate-100 dark:bg-slate-950 rounded p-4 mb-6 overflow-auto max-h-48">
              <pre className="text-sm text-slate-800 dark:text-slate-200 font-mono">
                {this.state.error?.message}
              </pre>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => window.location.reload()}
                className="bg-slate-200 hover:bg-slate-300 text-slate-800 font-medium py-2 px-4 rounded transition-colors"
              >
                Reload Page
              </button>
              
              <button
                onClick={this.handleReport}
                disabled={this.state.isSubmitting || this.state.submitted}
                className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded transition-colors disabled:opacity-50"
              >
                {this.state.submitted 
                  ? 'Report Sent' 
                  : this.state.isSubmitting 
                    ? 'Sending...' 
                    : 'Send Crash Report'}
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
