// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, expect, it } from 'vitest';
import {
    AgentMessageSchema,
    AgentSessionStartSchema,
    FeedbackSubmissionSchema,
    GeneratorStartSchema,
    SynthesisSessionStartSchema,
} from './schemas';

const createFile = (name, content = 'x') => new File([content], name, { type: 'text/plain' });

describe('schemas', () => {
    describe('FeedbackSubmissionSchema', () => {
        it('accepts a valid payload', () => {
            const result = FeedbackSubmissionSchema.safeParse({
                document_id: 'doc-123',
                field: 'title',
                original_value: 'Old title',
                corrected_value: 'New title',
                comments: 'Looks better.',
            });

            expect(result.success).toBe(true);
        });

        it('rejects missing corrected_value', () => {
            const result = FeedbackSubmissionSchema.safeParse({
                document_id: 'doc-123',
                field: 'title',
                corrected_value: '   ',
            });

            expect(result.success).toBe(false);
        });
    });

    describe('AgentSessionStartSchema', () => {
        it('accepts a valid prompt and template', () => {
            const result = AgentSessionStartSchema.safeParse({
                prompt: 'Improve this abstract for clarity',
                template: 'IEEE',
                config: { tone: 'formal' },
            });

            expect(result.success).toBe(true);
        });

        it('rejects empty prompt', () => {
            const result = AgentSessionStartSchema.safeParse({
                prompt: '   ',
                template: 'IEEE',
            });

            expect(result.success).toBe(false);
        });
    });

    describe('AgentMessageSchema', () => {
        it('accepts non-empty message', () => {
            const result = AgentMessageSchema.safeParse({ content: 'Please rewrite section 2.' });
            expect(result.success).toBe(true);
        });

        it('rejects whitespace-only message', () => {
            const result = AgentMessageSchema.safeParse({ content: '   ' });
            expect(result.success).toBe(false);
        });
    });

    describe('SynthesisSessionStartSchema', () => {
        it('accepts 2 files with allowed extensions', () => {
            const result = SynthesisSessionStartSchema.safeParse({
                files: [createFile('paper-a.pdf', 'abc'), createFile('paper-b.docx', 'def')],
                template: 'IEEE',
            });

            expect(result.success).toBe(true);
        });

        it('rejects unsupported extension', () => {
            const result = SynthesisSessionStartSchema.safeParse({
                files: [createFile('paper-a.pdf', 'abc'), createFile('notes.exe', 'def')],
                template: 'IEEE',
            });

            expect(result.success).toBe(false);
        });

        it('rejects fewer than 2 files', () => {
            const result = SynthesisSessionStartSchema.safeParse({
                files: [createFile('paper-a.pdf', 'abc')],
                template: 'IEEE',
            });

            expect(result.success).toBe(false);
        });
    });

    describe('GeneratorStartSchema', () => {
        it('requires metadata.name for resume', () => {
            const valid = GeneratorStartSchema.safeParse({
                doc_type: 'resume',
                template: 'ATS',
                metadata: { name: 'Alex Doe', email: 'alex@example.com' },
            });
            const invalid = GeneratorStartSchema.safeParse({
                doc_type: 'resume',
                template: 'ATS',
                metadata: { email: 'alex@example.com' },
            });

            expect(valid.success).toBe(true);
            expect(invalid.success).toBe(false);
        });

        it('requires metadata.title for non-resume doc types', () => {
            const valid = GeneratorStartSchema.safeParse({
                doc_type: 'academic_paper',
                template: 'IEEE',
                metadata: { title: 'A Strong Baseline' },
            });
            const invalid = GeneratorStartSchema.safeParse({
                doc_type: 'academic_paper',
                template: 'IEEE',
                metadata: {},
            });

            expect(valid.success).toBe(true);
            expect(invalid.success).toBe(false);
        });
    });
});
