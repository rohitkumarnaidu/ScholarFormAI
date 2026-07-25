// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    transpilePackages: ['react-resizable-panels'],
    experimental: {
        optimizePackageImports: ['lucide-react', 'framer-motion', '@tanstack/react-query'],
    },
    // CDN configuration for production static assets
    assetPrefix: process.env.CDN_URL || "",
    images: {
        remotePatterns: process.env.CDN_URL
            ? [{ protocol: "https", hostname: new URL(process.env.CDN_URL).hostname }]
            : [],
    },
    async headers() {
        return [
            {
                source: "/(.*)",
                headers: [
                    { key: "X-Content-Type-Options", value: "nosniff" },
                    { key: "X-Frame-Options", value: "DENY" },
                    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
                    { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains; preload" },
                    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), interest-cohort=()" },
                    {
                        key: "Content-Security-Policy",
                        value: [
                            "default-src 'self'",
                            "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://cdn.jsdelivr.net",
                            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                            "font-src 'self' https://fonts.gstatic.com data:",
                            "img-src 'self' data: blob: https://*.supabase.co",
                            "connect-src 'self' https://*.supabase.co wss://*.supabase.co https://scholarform.onrender.com",
                            "frame-src 'none'",
                            "object-src 'none'",
                            "base-uri 'self'",
                            "form-action 'self'",
                        ].join("; "),
                    },
                ],
            },
            {
                source: "/_next/static/(.*)",
                headers: [
                    { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
                ],
            },
            {
                source: "/static/(.*)",
                headers: [
                    { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
                ],
            },
        ];
    },
    async rewrites() {
        return [
            {
                source: '/metrics',
                destination: '/api/metrics',
            },
        ];
    },
};

export default nextConfig;
