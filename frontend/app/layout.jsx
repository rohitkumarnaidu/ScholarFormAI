// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { Manrope } from 'next/font/google';
import './globals.css';
import ClientProviders from '@/src/components/layout/ClientProviders';

const manrope = Manrope({
    subsets: ['latin'],
    weight: ['400', '500', '600', '700', '800'],
    variable: '--font-manrope',
    display: 'swap',
});

export const metadata = {
    title: 'ScholarForm AI',
    description: 'AI-powered academic manuscript formatting for IEEE, APA, Springer, Nature, and 1000+ journals. Upload your paper, get publication-ready output in seconds.',
    manifest: '/manifest.json',
    openGraph: {
        title: 'ScholarForm AI - Automated Academic Manuscript Formatter',
        description: 'Format your research paper for any journal in seconds. Supports IEEE, APA, Springer, Nature, Elsevier, and 1000+ templates.',
        type: 'website',
        url: 'https://scholarform.ai',
    },
    twitter: {
        card: 'summary_large_image',
        title: 'ScholarForm AI',
        description: 'AI-powered academic manuscript formatting for 1000+ journals.',
    },
};

export const viewport = {
    themeColor: '#2563EB',
};

export default function RootLayout({ children }) {
    return (
        <html lang="en" className={manrope.variable} suppressHydrationWarning>
            <head>
                <script
                    dangerouslySetInnerHTML={{
                        __html: `
                            (function () {
                                try {
                                    var link = document.createElement('link');
                                    link.rel = 'stylesheet';
                                    link.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap';
                                    link.media = 'print';
                                    link.onload = function () { this.media = 'all'; };
                                    document.head.appendChild(link);
                                } catch (e) {
                                    // ignore
                                }
                            })();
                        `,
                    }}
                />
                <noscript>
                    <link
                        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
                        rel="stylesheet"
                    />
                </noscript>
            </head>
            <body className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 min-h-screen relative overflow-x-hidden selection:bg-primary selection:text-white">
                <style
                    dangerouslySetInnerHTML={{
                        __html: `
                            .material-symbols-outlined {
                                font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
                            }
                        `,
                    }}
                />
                <a
                    href="#main-content"
                    className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:bg-primary focus:text-white focus:px-4 focus:py-2 focus:rounded-lg focus:text-sm focus:font-bold focus:shadow-lg"
                >
                    Skip to main content
                </a>
                <ClientProviders>
                    {children}
                </ClientProviders>
            </body>
        </html>
    );
}
