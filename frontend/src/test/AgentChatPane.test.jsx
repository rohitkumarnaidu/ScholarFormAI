// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import AgentChatPane from '../components/generator/AgentChatPane';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }) => <div {...props}>{children}</div>,
    },
    AnimatePresence: ({ children }) => <>{children}</>,
}));

vi.mock('../components/generator/ModelSelector', () => ({
    default: ({ selectedModel, onModelChange, userToken }) => (
        <div data-testid="model-selector" data-model={selectedModel} data-token={userToken}>
            <button onClick={() => onModelChange('gpt-4')}>Change Model</button>
        </div>
    ),
}));

vi.mock('@/src/context/AuthContext', () => ({
    useAuth: () => ({ user: { access_token: 'mock-token' } }),
}));

beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
});

describe('AgentChatPane', () => {
    const defaultProps = {
        messages: [],
        onSendMessage: vi.fn(),
        onStop: vi.fn(),
        isTyping: false,
        error: null,
        selectedModel: '',
        onModelChange: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
    });

    it('renders empty state with ready prompt', () => {
        render(<AgentChatPane {...defaultProps} />);
        expect(screen.getByText('Ready to write?')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Type your prompt here...')).toBeInTheDocument();
    });

    it('renders user messages', () => {
        const messages = [{ id: '1', role: 'user', content: 'Write a paper on AI', timestamp: new Date().toISOString() }];
        render(<AgentChatPane {...defaultProps} messages={messages} />);
        expect(screen.getByText('Write a paper on AI')).toBeInTheDocument();
    });

    it('renders assistant messages with sources', () => {
        const messages = [{
            id: '2', role: 'assistant', content: 'Here is an outline.',
            timestamp: new Date().toISOString(),
            sources: [{ source_doc: 'paper1.pdf', section: 'Introduction' }],
        }];
        render(<AgentChatPane {...defaultProps} messages={messages} />);
        expect(screen.getByText('Here is an outline.')).toBeInTheDocument();
        expect(screen.getByText(/paper1\.pdf/)).toBeInTheDocument();
    });

    it('renders outline structure in assistant messages', () => {
        const messages = [{
            id: '3', role: 'assistant', content: {
                outline: { sections: [{ title: 'Introduction', expectedWordCount: 500 }] },
            },
            timestamp: new Date().toISOString(),
        }];
        render(<AgentChatPane {...defaultProps} messages={messages} />);
        expect(screen.getByText('Outline')).toBeInTheDocument();
        expect(screen.getByText('Introduction')).toBeInTheDocument();
    });

    it('renders quality score in assistant messages', () => {
        const messages = [{
            id: '4', role: 'assistant', content: { overallScore: 92 },
            timestamp: new Date().toISOString(),
        }];
        render(<AgentChatPane {...defaultProps} messages={messages} />);
        expect(screen.getByText('92/100')).toBeInTheDocument();
    });

    it('renders status messages with amber styling', () => {
        const messages = [{
            id: '5', role: 'assistant', content: 'Processing...', isStatus: true,
            timestamp: new Date().toISOString(),
        }];
        render(<AgentChatPane {...defaultProps} messages={messages} />);
        expect(screen.getByText('Processing...')).toBeInTheDocument();
    });

    it('calls onSendMessage on form submit', () => {
        const onSendMessage = vi.fn();
        render(<AgentChatPane {...defaultProps} onSendMessage={onSendMessage} />);
        const input = screen.getByPlaceholderText('Type your prompt here...');
        fireEvent.change(input, { target: { value: 'Hello' } });
        fireEvent.click(screen.getByTitle('Submit (Ctrl+Enter)'));
        expect(onSendMessage).toHaveBeenCalledWith('Hello');
        expect(input.value).toBe('');
    });

    it('submits with Ctrl+Enter', () => {
        const onSendMessage = vi.fn();
        render(<AgentChatPane {...defaultProps} onSendMessage={onSendMessage} />);
        const input = screen.getByPlaceholderText('Type your prompt here...');
        fireEvent.change(input, { target: { value: 'Ctrl+Enter test' } });
        fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true });
        expect(onSendMessage).toHaveBeenCalledWith('Ctrl+Enter test');
    });

    it('does not send empty message', () => {
        const onSendMessage = vi.fn();
        render(<AgentChatPane {...defaultProps} onSendMessage={onSendMessage} />);
        fireEvent.click(screen.getByTitle('Submit (Ctrl+Enter)'));
        expect(onSendMessage).not.toHaveBeenCalled();
    });

    it('shows typing indicator when isTyping is true', () => {
        render(<AgentChatPane {...defaultProps} isTyping={true} />);
        expect(screen.getByPlaceholderText('Agent is thinking...')).toBeInTheDocument();
    });

    it('disables input when typing', () => {
        render(<AgentChatPane {...defaultProps} isTyping={true} />);
        const input = screen.getByPlaceholderText('Agent is thinking...');
        expect(input).toBeDisabled();
    });

    it('shows stop button when typing', () => {
        const onStop = vi.fn();
        render(<AgentChatPane {...defaultProps} isTyping={true} onStop={onStop} />);
        const stopBtn = screen.getByTitle('Stop Agent');
        expect(stopBtn).toBeInTheDocument();
        fireEvent.click(stopBtn);
        expect(onStop).toHaveBeenCalled();
    });

    it('renders error message', () => {
        render(<AgentChatPane {...defaultProps} error="Something went wrong" />);
        expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('integrates ModelSelector with model change handler', () => {
        const onModelChange = vi.fn();
        render(<AgentChatPane {...defaultProps} onModelChange={onModelChange} />);
        expect(screen.getByTestId('model-selector')).toBeInTheDocument();
        fireEvent.click(screen.getByText('Change Model'));
        expect(onModelChange).toHaveBeenCalledWith('gpt-4');
    });

    it('shows selected model in header', () => {
        render(<AgentChatPane {...defaultProps} selectedModel="gpt-4" />);
        expect(screen.getByText('gpt-4')).toBeInTheDocument();
    });

    it('shows Auto label when no model selected', () => {
        render(<AgentChatPane {...defaultProps} selectedModel="" />);
        expect(screen.getByText('Auto')).toBeInTheDocument();
    });

    it('does not send message while typing', () => {
        const onSendMessage = vi.fn();
        render(<AgentChatPane {...defaultProps} onSendMessage={onSendMessage} isTyping={true} />);
        const input = screen.getByPlaceholderText('Agent is thinking...');
        fireEvent.change(input, { target: { value: 'test' } });
        fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true });
        expect(onSendMessage).not.toHaveBeenCalled();
    });
});
