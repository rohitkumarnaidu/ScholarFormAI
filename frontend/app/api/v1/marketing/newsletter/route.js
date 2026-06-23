// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { NextResponse } from 'next/server';

export async function POST(request) {
    try {
        const { email } = await request.json();
        
        if (!email || !email.includes('@')) {
            return NextResponse.json(
                { error: 'Valid email is required' },
                { status: 400 }
            );
        }

        // Simulating external API call or database insert
        await new Promise(resolve => setTimeout(resolve, 800));
        
        return NextResponse.json(
            { message: 'Successfully subscribed' },
            { status: 200 }
        );
    } catch (error) {
        return NextResponse.json(
            { error: 'Something went wrong' },
            { status: 500 }
        );
    }
}
