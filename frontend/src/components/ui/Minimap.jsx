// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { useEffect, useState, useRef } from 'react';

export default function Minimap({ content, targetRef }) {
    const [scrollRatio, setScrollRatio] = useState(0);
    const [viewportRatio, setViewportRatio] = useState(1);
    const mapRef = useRef(null);

    useEffect(() => {
        const target = targetRef.current;
        if (!target) return;

        const handleScroll = () => {
            const { scrollTop, scrollHeight, clientHeight } = target;
            const maxScroll = Math.max(0, scrollHeight - clientHeight);

            if (maxScroll > 0) {
                setScrollRatio(scrollTop / maxScroll);
                setViewportRatio(Math.min(1, clientHeight / scrollHeight));
            } else {
                setScrollRatio(0);
                setViewportRatio(1);
            }
        };

        target.addEventListener('scroll', handleScroll);
        window.addEventListener('resize', handleScroll);

        // Initial setup
        // Delay slightly to ensure layout is computed
        const to = setTimeout(handleScroll, 100);

        return () => {
            target.removeEventListener('scroll', handleScroll);
            window.removeEventListener('resize', handleScroll);
            clearTimeout(to);
        };
    }, [targetRef, content]);

    const handleMapClick = (e) => {
        const target = targetRef.current;
        if (!target || !mapRef.current) return;

        const rect = mapRef.current.getBoundingClientRect();
        const y = e.clientY - rect.top;
        const clickRatio = y / rect.height;

        const { scrollHeight, clientHeight } = target;
        const maxScroll = scrollHeight - clientHeight;

        // Target scroll top based on click ratio
        target.scrollTop = clickRatio * maxScroll;
    };

    const lines = content.split('\n');

    return (
        <div
            ref={mapRef}
            onClick={handleMapClick}
            className="hidden lg:block w-12 sm:w-16 bg-slate-50 dark:bg-slate-900/50 border-l border-slate-200 dark:border-slate-800 relative select-none cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors"
            title="Minimap (Click to scroll)"
        >
            <div className="absolute inset-0 overflow-hidden p-1 opacity-40 pointer-events-none mix-blend-multiply dark:mix-blend-lighten">
                {lines.map((line, i) => (
                    <div
                        key={i}
                        className={`h-[2px] mb-[2px] rounded-full ${line.trim() === '' ? 'w-0' : 'bg-slate-400 dark:bg-slate-500'}`}
                        style={{ width: `${Math.max(10, Math.min(100, line.length / 1.5))}%` }}
                    />
                ))}
            </div>

            {/* Viewport Tracker */}
            {viewportRatio < 1 && (
                <div
                    className="absolute left-0 right-0 bg-primary/20 dark:bg-primary/30 border-y border-primary/40 pointer-events-none transition-transform duration-75"
                    style={{
                        height: `${Math.max(5, viewportRatio * 100)}%`,
                        top: `${scrollRatio * (100 - Math.max(5, viewportRatio * 100))}%`
                    }}
                />
            )}
        </div>
    );
}
