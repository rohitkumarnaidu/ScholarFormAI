// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { NextResponse } from 'next/server';
import { httpRequestDurationMicroseconds } from '@/src/lib/metrics';

export const runtime = 'nodejs';

export async function POST(request) {
    try {
        const { method, route, status, duration } = await request.json();
        
        if (duration) {
            httpRequestDurationMicroseconds.observe(
                { method, route, status_code: status },
                duration / 1000 // Convert ms to s
            );
        }
        
        return NextResponse.json({ ok: true });
    } catch (error) {
        return NextResponse.json({ ok: false }, { status: 500 });
    }
}
