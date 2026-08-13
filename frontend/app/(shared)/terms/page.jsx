// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';

export default function Terms() {
    usePageTitle('Terms of Service');

    const sections = [
        {
            title: 'Acceptance of Terms',
            content: 'By accessing or using ScholarForm AI, you agree to be bound by these Terms of Service. If you do not agree, you may not use the service. These terms apply to all users, including visitors, registered users, and institutional accounts.'
        },
        {
            title: 'Use of Service',
            content: 'You may use ScholarForm AI for lawful academic and research workflows. You are responsible for the content you upload and for ensuring you have the rights to process that content. You must not upload content that infringes copyright, contains malware, or violates any applicable law.'
        },
        {
            title: 'Account Responsibility',
            content: 'You are responsible for maintaining the confidentiality of your account credentials. All activity under your account is your responsibility unless unauthorized access is promptly reported to us. We reserve the right to suspend accounts that violate these terms.'
        },
        {
            title: 'Intellectual Property',
            content: 'You retain full ownership of all manuscripts and documents you upload to ScholarForm AI. We do not claim any intellectual property rights over your content. Our formatting and validation services are tools — the output remains your property.'
        },
        {
            title: 'Service Availability & Limits',
            content: 'We strive to maintain high availability but do not guarantee uninterrupted service. Features, templates, processing limits, and pricing may be updated over time. Free-tier users are subject to monthly processing limits as described on our Pricing page.'
        },
        {
            title: 'Limitation of Liability',
            content: 'ScholarForm AI is provided "as is" without warranties of any kind. We are not responsible for formatting errors, missed deadlines, or journal rejections resulting from use of the service. Our total liability is limited to the amount you paid for the service in the preceding 12 months.'
        },
        {
            title: 'Prohibited Activities',
            content: 'You may not: reverse-engineer, decompile, or disassemble the service; use automated tools to scrape or overload our systems; resell or redistribute the service without authorization; or attempt to circumvent usage limits or security measures.'
        },
        {
            title: 'Termination',
            content: 'You may terminate your account at any time through your Profile settings. We may terminate or suspend access for violations of these terms. Upon termination, your data will be handled according to our Privacy Policy retention schedule.'
        },
        {
            title: 'Changes to Terms',
            content: 'We may modify these terms at any time. Material changes will be communicated via email or in-app notification at least 30 days before taking effect. Continued use after changes constitutes acceptance of the updated terms.'
        },
        {
            title: 'Governing Law',
            content: 'These terms are governed by applicable law. Any disputes arising from these terms or use of the service shall be resolved through binding arbitration or in the courts of the jurisdiction where ScholarForm AI is incorporated.'
        }
    ];

    return (
        <div className="flex flex-col">
            <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 sm:py-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-900 dark:text-white">
                    Terms of Service
                </h1>
                <p className="mt-2 text-slate-600 dark:text-slate-400">
                    Last updated: February 2026
                </p>
                <p className="mt-4 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                    Please read these Terms of Service carefully before using ScholarForm AI. By using our service, you agree to these terms.
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
                </div>
            </main>
        </div>
    );
}
