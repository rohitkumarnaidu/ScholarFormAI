// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect } from 'vitest';
import { 
    UserProfileSchema, 
    JobStatusResponseSchema 
} from '../lib/schemas';

describe('API Contract Tests', () => {
    it('should validate a correct User Profile payload', () => {
        const payload = {
            name: 'John Doe',
            institution: 'University of Mars'
        };
        const result = UserProfileSchema.safeParse(payload);
        expect(result.success).toBe(true);
    });

    it('should fail on invalid User Profile (missing name)', () => {
        const payload = {
            institution: 'University of Mars'
        };
        const result = UserProfileSchema.safeParse(payload);
        expect(result.success).toBe(false);
    });

    it('should validate a correct Job Status response', () => {
        const payload = {
            status: 'completed',
            progress_percentage: 100,
            message: 'All good'
        };
        const result = JobStatusResponseSchema.safeParse(payload);
        expect(result.success).toBe(true);
    });

    it('should allow passthrough of unknown fields in Job Status', () => {
        const payload = {
            status: 'processing',
            unknown_server_field: 'value'
        };
        const result = JobStatusResponseSchema.safeParse(payload);
        expect(result.success).toBe(true);
        expect(result.data.unknown_server_field).toBe('value');
    });
});
