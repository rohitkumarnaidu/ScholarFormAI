'use client';

import { ArrowRight, FileText, Palette, Shield, Zap, BookOpen, Github, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { motion, useMotionValue, useTransform, animate, useInView, Variants } from 'framer-motion';
import { useRef, useEffect } from 'react';

const features = [
  {
    icon: FileText,
    title: 'Multiple Input Formats',
    description: 'Write in Markdown, LaTeX, or plain text. AMF handles the conversion to beautifully formatted DOCX.',
    className: 'md:col-span-2 lg:col-span-2',
  },
  {
    icon: Palette,
    title: 'Academic Style Library',
    description: 'Built-in support for APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard, Vancouver, and more.',
    className: 'md:col-span-1 lg:col-span-1',
  },
  {
    icon: Zap,
    title: 'Instant Formatting',
    description: 'Format your entire manuscript in seconds. Real-time preview with iterative refinement.',
    className: 'md:col-span-1 lg:col-span-1',
  },
  {
    icon: Shield,
    title: 'Validation Engine',
    description: 'Automatic validation checks for structure, citations, references, and style compliance.',
    className: 'md:col-span-2 lg:col-span-2',
  },
  {
    icon: BookOpen,
    title: 'Citation Management',
    description: 'Automatic citation formatting and reference list generation in your chosen style.',
    className: 'md:col-span-2 lg:col-span-2',
  },
  {
    icon: Sparkles,
    title: 'AI-Powered Assistance',
    description: 'Smart suggestions for section structure, citation fixes, and formatting improvements.',
    className: 'md:col-span-1 lg:col-span-1',
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

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 100, damping: 20 } },
};

function Counter({ from, to, duration = 2, suffix = '' }: { from: number; to: number; duration?: number; suffix?: string }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });
  const count = useMotionValue(from);
  const rounded = useTransform(count, (latest) => Math.round(latest) + suffix);

  useEffect(() => {
    if (isInView) {
      animate(count, to, { duration, ease: 'easeOut' });
    }
  }, [isInView, count, to, duration]);

  return <motion.span ref={ref}>{rounded}</motion.span>;
}

export default function Home() {
  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 text-white selection:bg-accent-500/30">
        <motion.div 
          animate={{ scale: [1, 1.05, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute -right-[20%] -top-[20%] h-[800px] w-[800px] rounded-full bg-accent-500/20 blur-[120px]" 
        />
        <motion.div 
          animate={{ scale: [1, 1.1, 1], opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
          className="absolute -bottom-[20%] -left-[10%] h-[600px] w-[600px] rounded-full bg-primary-500/30 blur-[100px]" 
        />
        
        <div className="container relative mx-auto max-w-6xl px-4 py-24 md:py-32 lg:py-40">
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="mx-auto max-w-4xl text-center"
          >
            <motion.div variants={itemVariants} className="mb-6 flex justify-center">
              <span className="inline-flex items-center gap-2 rounded-full border border-accent-400/30 bg-accent-500/10 px-4 py-2 text-sm font-medium text-accent-300 backdrop-blur-sm">
                <Sparkles className="h-4 w-4" />
                Enterprise-Grade Academic Formatting
              </span>
            </motion.div>
            
            <motion.h1 variants={itemVariants} className="mb-8 text-5xl font-extrabold tracking-tight md:text-7xl lg:text-8xl">
              Automated Manuscript
              <span className="block bg-gradient-to-r from-accent-300 to-accent-500 bg-clip-text text-transparent pb-2">
                Formatter
              </span>
            </motion.h1>
            
            <motion.p variants={itemVariants} className="mx-auto mb-10 max-w-2xl text-lg font-light text-white/70 md:text-xl leading-relaxed">
              Transform academic manuscripts into professionally styled DOCX documents.
              Supports major citation styles, strict validation, and real-time preview for high-impact research.
            </motion.p>
            
            <motion.div variants={itemVariants} className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/format"
                className="group relative inline-flex items-center gap-2 overflow-hidden rounded-full bg-accent-500 px-8 py-4 text-base font-semibold text-white transition-all hover:bg-accent-600 hover:scale-105 active:scale-95 hover:shadow-[0_0_40px_rgba(45,106,79,0.4)]"
              >
                <span className="relative z-10 flex items-center gap-2">
                  Start Formatting
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </span>
                <div className="absolute inset-0 z-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 ease-out group-hover:translate-x-full" />
              </Link>
              <Link
                href="/docs"
                className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-8 py-4 text-base font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/10 hover:border-white/40 hover:scale-105 active:scale-95"
              >
                Read Documentation
                <BookOpen className="h-4 w-4" />
              </Link>
            </motion.div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.8, ease: "easeOut" }}
            className="mt-24 grid grid-cols-3 gap-8 rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-sm backdrop-blur-md md:text-base lg:text-lg"
          >
            <div>
              <div className="mb-2 text-4xl font-black text-white md:text-5xl lg:text-6xl"><Counter from={0} to={9} suffix="+" /></div>
              <div className="font-medium text-white/60">Citation Styles</div>
            </div>
            <div className="border-x border-white/10">
              <div className="mb-2 text-4xl font-black text-white md:text-5xl lg:text-6xl"><Counter from={0} to={3} /></div>
              <div className="font-medium text-white/60">Input Formats</div>
            </div>
            <div>
              <div className="mb-2 text-4xl font-black text-accent-400 md:text-5xl lg:text-6xl"><Counter from={0} to={100} suffix="%" /></div>
              <div className="font-medium text-white/60">Style Compliant</div>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-slate-50 py-32 dark:bg-primary-950">
        <div className="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] opacity-50 [background-size:20px_20px] dark:bg-[radial-gradient(#1e293b_1px,transparent_1px)]" />
        <div className="container relative mx-auto max-w-6xl px-4">
          <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={containerVariants}
            className="mb-20 text-center"
          >
            <motion.h2 variants={itemVariants} className="mb-6 text-4xl font-extrabold text-primary-900 dark:text-white md:text-5xl">
              Why Choose AMF?
            </motion.h2>
            <motion.p variants={itemVariants} className="mx-auto max-w-3xl text-lg text-slate-600 dark:text-slate-400">
              Academic formatting should be about content, not wrestling with style guides.
              We've engineered an enterprise-grade platform to automate the entire manuscript pipeline.
            </motion.p>
          </motion.div>
          
          <div className="grid gap-6 md:grid-cols-3 md:grid-rows-2">
            {features.map((feature, idx) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                whileHover={{ y: -5, transition: { duration: 0.2 } }}
                className={`group relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-8 shadow-sm transition-all hover:shadow-xl dark:border-slate-800 dark:bg-primary-900/50 dark:backdrop-blur-xl ${feature.className}`}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-accent-500/5 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
                <div className="relative z-10">
                  <div className="mb-6 inline-flex rounded-2xl bg-accent-100 p-4 text-accent-700 transition-colors group-hover:bg-accent-500 group-hover:text-white dark:bg-accent-900/40 dark:text-accent-400 dark:group-hover:bg-accent-500 dark:group-hover:text-white">
                    <feature.icon className="h-8 w-8" />
                  </div>
                  <h3 className="mb-3 text-xl font-bold text-primary-900 dark:text-white">
                    {feature.title}
                  </h3>
                  <p className="text-base leading-relaxed text-slate-600 dark:text-slate-400">
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="overflow-hidden bg-white py-32 dark:bg-primary-900">
        <div className="container mx-auto max-w-6xl px-4">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="mb-16 text-center"
          >
            <h2 className="mb-6 text-3xl font-extrabold text-primary-900 dark:text-white md:text-4xl">
              Supported Citation Styles
            </h2>
            <p className="text-lg text-slate-600 dark:text-slate-400">
              Comprehensive compliance across every major academic discipline
            </p>
          </motion.div>
          
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="flex flex-wrap justify-center gap-4"
          >
            {styles.map((style) => (
              <motion.span
                variants={itemVariants}
                whileHover={{ scale: 1.05, y: -2 }}
                key={style}
                className="cursor-default rounded-full border border-slate-200 bg-slate-50 px-6 py-3 text-base font-semibold text-primary-700 shadow-sm transition-colors hover:border-accent-300 hover:text-accent-700 dark:border-slate-700 dark:bg-primary-800 dark:text-slate-200 dark:hover:border-accent-500 dark:hover:text-accent-300"
              >
                {style}
              </motion.span>
            ))}
          </motion.div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-primary-950 py-32 text-white">
        <div className="absolute inset-0 bg-gradient-to-t from-accent-900/40 to-transparent" />
        <div className="container relative mx-auto max-w-4xl px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="mb-8 text-4xl font-extrabold md:text-5xl lg:text-6xl">
              Ready to Simplify Your Academic Formatting?
            </h2>
            <p className="mb-12 text-xl text-white/70">
              Get started in minutes. No registration required. Open source and free.
            </p>
            <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-center">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Link
                  href="/format"
                  className="inline-flex items-center gap-3 rounded-full bg-white px-10 py-5 text-lg font-bold text-primary-950 shadow-lg shadow-white/10 transition-all hover:bg-slate-100 hover:shadow-xl hover:shadow-white/20"
                >
                  Start Now for Free
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </motion.div>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <a
                  href="https://github.com/amf/automated-manuscript-formatter"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-3 rounded-full border-2 border-white/20 bg-transparent px-10 py-5 text-lg font-bold text-white transition-all hover:border-white/40 hover:bg-white/10"
                >
                  <Github className="h-5 w-5" />
                  Star on GitHub
                </a>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>
    </>
  );
}
