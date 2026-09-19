// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef } from 'react';

import { cn } from '@/src/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
    width?: string | number;
    height?: string | number;
    shimmer?: boolean;
    rounded?: string;
}

const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
    (
        {
            className,
            width,
            height,
            shimmer = true,
            rounded = 'rounded-lg',
            ...props
        },
        ref
    ) => {
        const style = {
            width: width ?? undefined,
            height: height ?? undefined,
            ...props.style,
        };

        return (
            <div
                ref={ref}
                className={cn(
                    'bg-slate-200 dark:bg-slate-800',
                    shimmer ? 'animate-pulse' : '',
                    rounded,
                    className
                )}
                style={style}
                aria-hidden="true"
                {...props}
            />
        );
    }
);

export default Skeleton;
