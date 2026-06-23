// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import Footer from '@/src/components/Footer';

export default function Privacy() {
    usePageTitle('Privacy Policy');

    const sections = [
        {
            title: 'Information We Collect',
            content: 'We collect information you provide directly: account details (name, email, institution), uploaded manuscript files, and formatting preferences. We also collect usage data such as browser type, access timestamps, and feature interactions to improve the service.'
        },
        {
            title: 'How We Use Your Data',
            content: 'Your manuscripts are processed solely to provide formatting, validation, and export services. Account metadata is used for authentication, history tracking, and service personalization. We do not use your manuscript content for AI training or share it with third parties.'
        },
        {
            title: 'Data Storage & Security',
            content: 'All data is encrypted in transit (TLS 1.3) and at rest (AES-256). Uploaded manuscripts are stored temporarily during processing and are automatically purged within 30 days of completion unless you choose to retain them. Account data is stored in Supabase with row-level security policies.'
        },
        {
            title: 'Third-Party Services',
            content: 'We use Supabase for authentication and database services, and standard cloud infrastructure for document processing. We do not sell, rent, or share your personal information or manuscript content with advertisers or data brokers.'
        },
        {
            title: 'Cookies & Analytics',
            content: 'We use essential cookies for authentication session management. We may use privacy-respecting analytics to understand aggregate usage patterns. No third-party advertising trackers are used on our platform.'
        },
        {
            title: 'Your Rights',
            content: 'You may request access to, correction of, or deletion of your personal data at any time through your Profile settings or by contacting us. You can export your document history and delete your account permanently. We comply with GDPR, CCPA, and applicable data protection regulations.'
        },
        {
            title: 'Data Retention',
            content: 'Active account data is retained for the duration of your account. Processed manuscripts are retained for 30 days by default (configurable in Settings). Upon account deletion, all associated data is permanently removed within 14 business days.'
        },
        {
            title: 'Changes to This Policy',
            content: 'We may update this policy periodically. Significant changes will be communicated via email or in-app notification. Continued use of the service after changes constitutes acceptance of the updated policy.'
        }
    ];

    return (
        <div className="flex flex-col">
            <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 sm:py-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-900 dark:text-white">
                    Privacy Policy
                </h1>
                <p className="mt-2 text-slate-600 dark:text-slate-400">
                    Last updated: February 2026
                </p>
                <p className="mt-4 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                    ScholarForm AI ({'"'}we{'"'}, {'"'}our{'"'}, or {'"'}us{'"'}) is committed to protecting your privacy. This policy explains how we collect, use, store, and protect your information when you use our academic manuscript formatting platform.
                </p>

                <div className="mt-8 space-y-4 stagger-children">
                    {sections.map((section, i) => (
                        <section key={i} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 sm:p-6">
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white">{section.title}</h2>
                            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                                {section.content}
                            </p>
                        </section>
                    ))}

                    <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 sm:p-6">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Contact Us</h2>
                        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                            For privacy-related questions or data requests, contact us at{' '}
                            <a className="text-primary hover:underline" href="mailto:support@scholarform.ai">support@scholarform.ai</a>.
                        </p>
                    </section>
                </div>
            </main>
            <Footer variant="app" />
        </div>
    );
}
