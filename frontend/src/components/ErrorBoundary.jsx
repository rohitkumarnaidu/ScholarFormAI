// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React from 'react';
import { logFrontendError } from '@/src/services/api';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            hasError: false,
            details: '',
        };
    }

    static getDerivedStateFromError(error) {
        return {
            hasError: true,
            details: error?.message || '',
        };
    }

    async componentDidCatch(error, errorInfo) {
        console.error('UI rendering error captured by ErrorBoundary:', error, errorInfo);
        try {
            await logFrontendError({
                message: `ErrorBoundary caught: ${error?.message || String(error)}`,
                stack: `${error?.stack || ''}\nComponent Stack: ${errorInfo?.componentStack || ''}`
            });
        } catch (e) {
            console.warn('Failed to log error boundary capture to telemetry', e);
        }
    }

    handleRetry = () => {
        this.setState({
            hasError: false,
            details: '',
        });
    };

    handleReload = () => {
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 px-4">
                    <div className="max-w-lg w-full rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-xl">
                        <div className="flex items-start gap-3">
                            <span className="material-symbols-outlined text-red-600">error</span>
                            <div>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Something went wrong</h2>
                                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                                    We hit an unexpected issue while rendering this screen. Your data is still safe.
                                    Please try again.
                                </p>
                            </div>
                        </div>

                        <div className="mt-6 flex flex-col sm:flex-row gap-3">
                            <button
                                type="button"
                                onClick={this.handleRetry}
                                className="flex-1 rounded-lg bg-primary text-white px-4 py-2.5 text-sm font-bold hover:bg-blue-700 transition-colors"
                            >
                                Try Again
                            </button>
                            <button
                                type="button"
                                onClick={this.handleReload}
                                className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2.5 text-sm font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            >
                                Reload Page
                            </button>
                        </div>

                        {process.env.NODE_ENV !== 'production' && this.state.details ? (
                            <p className="mt-4 text-xs text-slate-500 break-words">
                                Debug: {this.state.details}
                            </p>
                        ) : null}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
