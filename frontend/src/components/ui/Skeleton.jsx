// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { forwardRef } from 'react';

const cx = (...classes) => classes.filter(Boolean).join(' ');

const Skeleton = forwardRef(function Skeleton(
    {
        className,
        width,
        height,
        shimmer = true,
        rounded = 'rounded-lg',
        ...props
    },
    ref
) {
    const style = {
        width: width ?? undefined,
        height: height ?? undefined,
        ...props.style,
    };

    return (
        <div
            ref={ref}
            className={cx(
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
});

export default Skeleton;
