// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/** @type {import('next').NextConfig} */
import { withSentryConfig } from "@sentry/nextjs";
import withPWAInit from "next-pwa";

const withPWA = withPWAInit({
    dest: "public",
    disable: process.env.NODE_ENV === 'development',
    register: true,
    skipWaiting: true,
});

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

export default withSentryConfig(withPWA(nextConfig), {
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
    silent: !process.env.CI,
    telemetry: false,
    widenClientFileUpload: true,
    hideSourceMaps: true,
    webpack: {
        treeshake: {
            removeDebugLogging: true,
        },
        automaticVercelMonitors: false,
    },
});
