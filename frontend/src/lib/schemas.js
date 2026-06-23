// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { z } from 'zod';

/**
 * User Profile Schema
 * Matches backend UserUpdateRequest in backend/app/schemas/user.py
 */
export const UserProfileSchema = z.object({
    name: z.string()
        .min(1, "Name is required")
        .max(120, "Name must be 120 characters or less")
        .trim(),
    institution: z.string()
        .max(200, "Institution must be 200 characters or less")
        .trim()
        .optional()
        .or(z.literal('')), // Allow empty string
});

/**
 * Authentication Schemas
 * Matches backend SignupRequest and ResetPasswordRequest in backend/app/schemas/auth.py
 */
export const PasswordSchema = z.string()
    .min(8, "Password must be at least 8 characters")
    .max(128, "Password too long")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one digit")
    .regex(/[@$!%*?&_\-#]/, "Password must contain at least one special character (@$!%*?&_-#)");

export const SignupSchema = z.object({
    full_name: z.string()
        .min(1, "Full name is required")
        .max(120, "Full name too long")
        .trim(),
    email: z.string()
        .email("Invalid email address"),
    institution: z.string()
        .max(200, "Institution too long")
        .optional()
        .or(z.literal('')),
    password: PasswordSchema,
    terms_accepted: z.boolean().refine(v => v === true, {
        message: "You must accept the terms and conditions"
    }),
});

export const LoginSchema = z.object({
    email: z.string().email("Invalid email address"),
    password: z.string().min(1, "Password is required"),
});

export const ResetPasswordSchema = z.object({
    email: z.string().email("Invalid email address"),
    otp: z.string().length(6, "OTP must be 6 digits").regex(/^\d+$/, "OTP must be numeric"),
    new_password: PasswordSchema,
});

export const SettingsSchema = z.object({
    defaultTemplate: z.enum(['IEEE', 'Springer', 'APA', 'Nature', 'Vancouver', 'none']),
    defaultPageSize: z.enum(['Letter', 'A4', 'Legal']),
    defaultFastMode: z.boolean(),
    defaultExportFormat: z.enum(['docx', 'pdf']),
    emailNotifications: z.boolean(),
    darkMode: z.boolean(),
});

const isBrowserFile = (value) => {
    if (typeof File === 'undefined') {
        return Boolean(value) && typeof value === 'object' && typeof value.size === 'number';
    }
    return value instanceof File;
};

const MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024;
const SYNTHESIS_ALLOWED_EXTENSIONS = new Set([
    '.docx',
    '.pdf',
    '.txt',
    '.md',
    '.tex',
    '.odt',
    '.html',
    '.rtf',
]);

const hasAllowedSynthesisExtension = (file) => {
    const name = String(file?.name || '');
    const dotIndex = name.lastIndexOf('.');
    if (dotIndex < 0) return false;
    const ext = name.slice(dotIndex).toLowerCase();
    return SYNTHESIS_ALLOWED_EXTENSIONS.has(ext);
};

export const UploadStartSchema = z.object({
    file: z.custom(isBrowserFile, { message: 'Please choose a file before starting upload.' })
        .refine((file) => Number(file?.size || 0) > 0, {
            message: 'Selected file is empty.',
        })
        .refine((file) => Number(file?.size || 0) <= MAX_UPLOAD_SIZE_BYTES, {
            message: 'Selected file exceeds 50MB limit.',
        }),
    template: z.string().trim().min(1, 'Template is required.'),
    formattingOptions: z.object({
        addPageNumbers: z.boolean(),
        addBorders: z.boolean(),
        addCoverPage: z.boolean(),
        generateTOC: z.boolean(),
        pageSize: z.enum(['Letter', 'A4', 'Legal']),
        fastMode: z.boolean(),
    }),
});

/**
 * Feedback form schema.
 * Aligns with backend feedback payload keys: document_id, field, original_value, corrected_value, comments.
 */
export const FeedbackSubmissionSchema = z.object({
    document_id: z.string()
        .trim()
        .min(1, 'Document ID is required.')
        .max(200, 'Document ID is too long.'),
    field: z.string()
        .trim()
        .min(1, 'Field name is required.')
        .max(120, 'Field name is too long.'),
    original_value: z.string()
        .trim()
        .max(1000, 'Original value must be 1000 characters or less.')
        .optional()
        .or(z.literal(''))
        .default(''),
    corrected_value: z.string()
        .trim()
        .min(1, 'Corrected value is required.')
        .max(1000, 'Corrected value must be 1000 characters or less.'),
    comments: z.string()
        .trim()
        .max(500, 'Comment must be 500 characters or less.')
        .optional()
        .or(z.literal(''))
        .default(''),
});

/**
 * Agent session + chat message schemas.
 */
export const AgentSessionStartSchema = z.object({
    prompt: z.string()
        .trim()
        .min(1, 'Prompt is required.')
        .max(4000, 'Prompt must be 4000 characters or less.'),
    template: z.string().trim().min(1, 'Template is required.'),
    config: z.record(z.string(), z.unknown()).optional(),
});

export const AgentMessageSchema = z.object({
    content: z.string()
        .trim()
        .min(1, 'Message cannot be empty.')
        .max(4000, 'Message must be 4000 characters or less.'),
});

/**
 * Multi-document synthesis start schema.
 */
export const SynthesisSessionStartSchema = z.object({
    files: z.array(
        z.custom(isBrowserFile, { message: 'Each uploaded item must be a valid file.' })
            .refine((file) => Number(file?.size || 0) > 0, {
                message: 'One of the selected files is empty.',
            })
            .refine((file) => Number(file?.size || 0) <= MAX_UPLOAD_SIZE_BYTES, {
                message: 'One of the selected files exceeds the 50MB limit.',
            })
            .refine((file) => hasAllowedSynthesisExtension(file), {
                message: 'One of the selected files has an unsupported extension.',
            })
    )
        .min(2, 'Please upload at least 2 files.')
        .max(6, 'You can upload up to 6 files.'),
    template: z.string().trim().min(1, 'Please select a template.'),
    config: z.record(z.string(), z.unknown()).optional(),
});

/**
 * Generator request schema.
 */
const GeneratorDocTypeSchema = z.enum([
    'academic_paper',
    'resume',
    'portfolio',
    'report',
    'thesis',
]);

export const GeneratorStartSchema = z.object({
    doc_type: GeneratorDocTypeSchema,
    template: z.string().trim().min(1, 'Template is required.'),
    metadata: z.record(z.string(), z.unknown()),
}).superRefine((value, ctx) => {
    const metadata = value.metadata || {};
    if (value.doc_type === 'resume') {
        const name = String(metadata.name || '').trim();
        if (!name) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: 'Resume name is required.',
                path: ['metadata', 'name'],
            });
        }
        const email = String(metadata.email || '').trim();
        if (email && !z.string().email().safeParse(email).success) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: 'Resume email is invalid.',
                path: ['metadata', 'email'],
            });
        }
        return;
    }

    const title = String(metadata.title || '').trim();
    if (!title) {
        ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'Document title is required.',
            path: ['metadata', 'title'],
        });
    }
});

export const getFirstZodError = (issues, fallbackMessage = 'Invalid input.') =>
    issues?.[0]?.message || fallbackMessage;

// ── API Response Schemas ─────────────────────────────────────
// These validate incoming server payloads at runtime to catch contract drift early.

/**
 * Schema for /api/v1/documents/{id}/status response.
 */
export const JobStatusResponseSchema = z.object({
    status: z.string().min(1),
    phase: z.string().optional(),
    current_phase: z.string().optional(),
    progress_percentage: z.number().min(0).max(100).optional().default(0),
    message: z.string().optional(),
    output_path: z.string().optional(),
}).passthrough(); // allow additional server fields without failing

/**
 * Schema for /api/v1/documents list response.
 */
export const DocumentListResponseSchema = z.object({
    documents: z.array(z.record(z.string(), z.unknown())).default([]),
    total: z.number().optional(),
    limit: z.number().optional(),
    offset: z.number().optional(),
}).passthrough();

/**
 * Schema for /api/v1/generator/sessions response.
 */
export const GeneratorSessionsResponseSchema = z.object({
    sessions: z.array(z.record(z.string(), z.unknown())).default([]),
}).passthrough();
