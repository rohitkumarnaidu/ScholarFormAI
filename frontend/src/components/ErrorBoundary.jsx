'use client';
import { Component } from 'react';
import { AlertTriangle } from 'lucide-react';
import Button from '@/components/ui/Button';

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
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 p-8">
                    <div className="max-w-md text-center">
                        <AlertTriangle className="text-6xl text-red-400 mb-4" />
                        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">Something went wrong</h2>
                        <p className="text-slate-500 dark:text-slate-400 mb-6 text-sm">
                            {this.state.error?.message || 'An unexpected error occurred while loading providers.'}
                        </p>
                        <Button
                            variant="primary"
                            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload(); }}
                        >
                            Reload Page
                        </Button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
