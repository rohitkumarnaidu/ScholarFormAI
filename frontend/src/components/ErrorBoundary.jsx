'use client';
import { Component } from 'react';
import { sendFrontendErrorLog } from '../services/api.core';

export default class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, info) {
        console.error('ErrorBoundary caught:', error, info);
        sendFrontendErrorLog({
            message: `React ErrorBoundary caught: ${error?.message || String(error)}`,
            stack: error?.stack || info?.componentStack,
        });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-8">
                    <div className="max-w-md text-center">
                        <span className="material-symbols-outlined text-6xl text-red-400 mb-4">error</span>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Something went wrong</h2>
                        <p className="text-gray-500 dark:text-gray-400 mb-6 text-sm">
                            {this.state.error?.message || 'An unexpected error occurred while loading providers.'}
                        </p>
                        <button
                            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
                            className="px-6 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm font-medium"
                        >
                            Reload Page
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
