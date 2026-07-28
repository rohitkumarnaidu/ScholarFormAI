'use client';

import { ArrowRight, FileText, Palette, Shield, Zap, BookOpen, Github, Sparkles } from 'lucide-react';
import Link from 'next/link';

const features = [
  {
    icon: FileText,
    title: 'Multiple Input Formats',
    description: 'Write in Markdown, LaTeX, or plain text. AMF handles the conversion to beautifully formatted DOCX.',
  },
  {
    icon: Palette,
    title: 'Academic Style Library',
    description: 'Built-in support for APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard, Vancouver, and more.',
  },
  {
    icon: Zap,
    title: 'Instant Formatting',
    description: 'Format your entire manuscript in seconds. Real-time preview with iterative refinement.',
  },
  {
    icon: Shield,
    title: 'Validation Engine',
    description: 'Automatic validation checks for structure, citations, references, and style compliance.',
  },
  {
    icon: BookOpen,
    title: 'Citation Management',
    description: 'Automatic citation formatting and reference list generation in your chosen style.',
  },
  {
    icon: Sparkles,
    title: 'AI-Powered Assistance',
    description: 'Smart suggestions for section structure, citation fixes, and formatting improvements.',
  },
];

const styles = [
  'APA 7th Edition',
  'MLA 9th Edition',
  'Chicago 17th Edition',
  'IEEE',
  'Harvard',
  'Vancouver',
  'Turabian',
  'ACS',
  'AMA',
];

export default function Home() {
  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-accent-500/20 via-transparent to-transparent" />
        <div className="container relative mx-auto max-w-6xl px-4 py-24 md:py-32">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm text-white/80">
              <Sparkles className="h-4 w-4" />
              Enterprise-Grade Academic Formatting
            </div>
            <h1 className="mb-6 text-4xl font-bold tracking-tight md:text-6xl lg:text-7xl">
              Automated Manuscript
              <span className="block text-accent-300">Formatter</span>
            </h1>
            <p className="mb-8 text-lg text-white/70 md:text-xl">
              Transform academic manuscripts into professionally styled DOCX documents.
              Supports major citation styles, validation, and real-time preview.
            </p>
            <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/format"
                className="inline-flex items-center gap-2 rounded-lg bg-accent-500 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-accent-600"
              >
                Start Formatting
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/docs"
                className="inline-flex items-center gap-2 rounded-lg border border-white/30 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-white/10"
              >
                Read Documentation
                <BookOpen className="h-4 w-4" />
              </Link>
            </div>
          </div>
          <div className="mt-16 grid grid-cols-3 gap-4 text-center text-sm text-white/50">
            <div>
              <div className="text-2xl font-bold text-white">9+</div>
              <div>Citation Styles</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-white">3</div>
              <div>Input Formats</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-white">100%</div>
              <div>Style Compliant</div>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white py-24 dark:bg-primary-950">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="mb-16 text-center">
            <h2 className="mb-4 text-3xl font-bold text-primary-800 dark:text-white md:text-4xl">
              Why AMF?
            </h2>
            <p className="mx-auto max-w-2xl text-slate-600 dark:text-slate-400">
              Academic formatting should be about content, not wrestling with style guides.
              AMF automates the entire formatting pipeline.
            </p>
          </div>
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="group rounded-xl border border-slate-200 bg-white p-6 transition-all hover:border-accent-300 hover:shadow-lg dark:border-slate-700 dark:bg-primary-900"
              >
                <div className="mb-4 inline-flex rounded-lg bg-accent-50 p-3 text-accent-600 dark:bg-accent-900/30 dark:text-accent-400">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="mb-2 font-semibold text-primary-800 dark:text-white">
                  {feature.title}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-slate-50 py-24 dark:bg-primary-900">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-bold text-primary-800 dark:text-white md:text-4xl">
              Supported Citation Styles
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              Comprehensive style support for every academic discipline
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            {styles.map((style) => (
              <span
                key={style}
                className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-primary-700 dark:border-slate-600 dark:bg-primary-800 dark:text-white"
              >
                {style}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-gradient-to-br from-accent-900 to-accent-800 py-24 text-white">
        <div className="container mx-auto max-w-4xl px-4 text-center">
          <h2 className="mb-6 text-3xl font-bold md:text-4xl">
            Ready to Simplify Your Academic Formatting?
          </h2>
          <p className="mb-8 text-lg text-white/70">
            Get started in minutes. No registration required. Open source and free.
          </p>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/format"
              className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-accent-900 transition-all hover:bg-white/90"
            >
              Get Started
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="https://github.com/amf/automated-manuscript-formatter"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-white/30 px-6 py-3 text-sm font-semibold text-white transition-all hover:bg-white/10"
            >
              <Github className="h-4 w-4" />
              Star on GitHub
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
