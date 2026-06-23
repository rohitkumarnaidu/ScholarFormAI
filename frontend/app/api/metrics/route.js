// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { NextResponse } from 'next/server';
import registry from '@/src/lib/metrics';

export const runtime = 'nodejs';

export async function GET() {
    try {
        const metrics = await registry.metrics();
        return new NextResponse(metrics, {
            status: 200,
            headers: {
                'Content-Type': registry.contentType,
                'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
            },
        });
    } catch (error) {
        return new NextResponse('Error generating metrics', { status: 500 });
    }
}
