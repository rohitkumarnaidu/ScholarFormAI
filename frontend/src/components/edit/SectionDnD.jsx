// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo, useState, useCallback, useRef } from 'react';

const DragHandle = memo(() => (
    <span
        className="cursor-grab active:cursor-grabbing text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors flex items-center px-2"
        aria-label="Drag to reorder"
        data-drag-handle
    >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <circle cx="5" cy="4" r="1.5" />
            <circle cx="11" cy="4" r="1.5" />
            <circle cx="5" cy="8" r="1.5" />
            <circle cx="11" cy="8" r="1.5" />
            <circle cx="5" cy="12" r="1.5" />
            <circle cx="11" cy="12" r="1.5" />
        </svg>
    </span>
));

DragHandle.displayName = 'DragHandle';

const SectionDnD = memo(function SectionDnD({ sections = [], onReorder, renderSection, className = '' }) {
    const [dragIndex, setDragIndex] = useState(null);
    const [dropIndex, setDropIndex] = useState(null);
    const dragNode = useRef(null);

    const handleDragStart = useCallback((e, index) => {
        dragNode.current = index;
        setDragIndex(index);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', String(index));
        e.target.closest('[data-dnd-section]')?.classList.add('opacity-50');
    }, []);

    const handleDragOver = useCallback((e, index) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (dragNode.current !== index) {
            setDropIndex(index);
        }
    }, []);

    const handleDragLeave = useCallback(() => {
        setDropIndex(null);
    }, []);

    const handleDrop = useCallback((e, index) => {
        e.preventDefault();
        const fromIndex = Number(e.dataTransfer.getData('text/plain'));
        if (!isNaN(fromIndex) && fromIndex !== index) {
            onReorder?.(fromIndex, index);
        }
        setDragIndex(null);
        setDropIndex(null);
        dragNode.current = null;
    }, [onReorder]);

    const handleDragEnd = useCallback(() => {
        document.querySelectorAll('[data-dnd-section]').forEach((el) => el.classList.remove('opacity-50'));
        setDragIndex(null);
        setDropIndex(null);
        dragNode.current = null;
    }, []);

    if (sections.length === 0) {
        return (
            <div className={`text-center py-8 text-slate-400 dark:text-slate-500 text-sm ${className}`}>
                No sections to reorder
            </div>
        );
    }

    return (
        <div className={`flex flex-col gap-1 ${className}`} role="list" aria-label="Reorderable sections">
            {sections.map((section, index) => {
                const isOver = dropIndex === index && dragIndex !== index;
                const isDragging = dragIndex === index;

                return (
                    <div
                        key={section.id ?? index}
                        data-dnd-section
                        draggable
                        onDragStart={(e) => handleDragStart(e, index)}
                        onDragOver={(e) => handleDragOver(e, index)}
                        onDragLeave={handleDragLeave}
                        onDrop={(e) => handleDrop(e, index)}
                        onDragEnd={handleDragEnd}
                        role="listitem"
                        aria-roledescription="draggable section"
                        aria-grabbed={isDragging}
                        className={`
                            flex items-center rounded-lg border
                            ${isDragging
                                ? 'border-primary/40 bg-primary/5 shadow-sm'
                                : isOver
                                ? 'border-primary border-dashed bg-primary/5'
                                : 'border-slate-200 dark:border-slate-700/70 bg-white dark:bg-slate-900'
                            }
                            ${isDragging ? 'opacity-70' : ''}
                            transition-all duration-200
                        `}
                        style={isOver ? { transform: 'translateY(2px)' } : undefined}
                    >
                        <DragHandle />
                        <div className="flex-1 min-w-0 py-3 pr-3">
                            {renderSection ? renderSection(section, index) : (
                                <span className="text-sm font-medium text-slate-900 dark:text-white truncate block">
                                    {section.title || section.label || `Section ${index + 1}`}
                                </span>
                            )}
                        </div>
                        {isOver && (
                            <div className="absolute inset-x-0 -bottom-1 h-0.5 bg-primary rounded-full" />
                        )}
                    </div>
                );
            })}
        </div>
    );
});

SectionDnD.displayName = 'SectionDnD';

export default SectionDnD;
