// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React from 'react';

export default function Loading() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[400px]">
            <div className="w-8 h-8 border-4 border-slate-200 border-t-primary rounded-full animate-spin mb-4" />
            <p className="text-slate-500 font-medium">Loading job details...</p>
        </div>
    );
}
