'use client';

import Link from 'next/link';
import { motion, useMotionValue, useTransform, animate, useInView, Variants, useMotionValueEvent } from 'framer-motion';
import { useRef, useEffect, useState } from 'react';

const features = [
  {
    icon: 'description',
    title: 'Multiple Input Formats',
    description: 'Write in Markdown, LaTeX, or plain text. AMF handles the conversion to beautifully formatted DOCX.',
    className: 'md:col-span-2 lg:col-span-2',
  },
  {
    icon: 'palette',
    title: 'Academic Style Library',
    description: 'Built-in support for APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard, Vancouver, and more.',
    className: 'md:col-span-1 lg:col-span-1',
  },
  {
    icon: 'bolt',
    title: 'Instant Formatting',
    description: 'Format your entire manuscript in seconds. Real-time preview with iterative refinement.',
    className: 'md:col-span-1 lg:col-span-1',
  },
  {
    icon: 'shield',
    title: 'Validation Engine',
    description: 'Automatic validation checks for structure, citations, references, and style compliance.',
    className: 'md:col-span-2 lg:col-span-2',
  },
  {
    icon: 'menu_book',
    title: 'Citation Management',
    description: 'Automatic citation formatting and reference list generation in your chosen style.',
    className: 'md:col-span-2 lg:col-span-2',
  },
  {
    icon: 'auto_awesome',
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
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 100, damping: 20 } },
};

function Counter({ from, to, duration = 2, suffix = '' }: { from: number; to: number; duration?: number; suffix?: string }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-50px' });
  const count = useMotionValue(from);
  const rounded = useTransform(count, (latest) => Math.round(latest) + suffix);
  const [display, setDisplay] = useState(from + suffix);

  useMotionValueEvent(rounded, "change", (latest) => {
    setDisplay(latest);
  });

  useEffect(() => {
    if (isInView) {
      animate(count, to, { duration, ease: 'easeOut' });
    }
  }, [isInView, count, to, duration]);

  return <span ref={ref}>{display}</span>;
}

export default function Home() {
  return (
    <>
      <section className="relative overflow-hidden bg-slate-50 text-slate-900 selection:bg-primary/20">
        
        {/* Navigation Bar */}
        <nav className="absolute top-0 w-full z-50 border-b border-slate-200 bg-white/70 backdrop-blur-md">
          <div className="container mx-auto px-4 max-w-6xl h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="bg-primary w-8 h-8 rounded-lg flex items-center justify-center shadow-sm">
                <span className="material-symbols-outlined text-white text-[20px]">description</span>
              </div>
              <span className="font-extrabold text-xl tracking-tight text-slate-900">ScholarForm<span className="text-primary">AI</span></span>
            </div>
            <div className="flex items-center gap-4">
              <Link href="/login" className="text-sm font-semibold text-slate-600 hover:text-slate-900 transition-colors">
                Log in
              </Link>
              <Link href="/signup" className="text-sm font-bold bg-slate-900 text-white px-5 py-2 rounded-lg hover:bg-slate-800 transition-colors shadow-sm hover:scale-105 active:scale-95">
                Sign up
              </Link>
            </div>
          </div>
        </nav>

        <div className="container relative mx-auto max-w-6xl px-4 pt-32 pb-24 md:pt-40 md:pb-32 lg:pt-48 lg:pb-40">
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="mx-auto max-w-4xl text-center"
          >
            <motion.div variants={itemVariants} className="mb-6 flex justify-center">
              <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary shadow-sm backdrop-blur-sm">
                <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
                Enterprise-Grade Academic Formatting
              </span>
            </motion.div>
            
            <motion.h1 variants={itemVariants} className="mb-8 text-5xl font-extrabold tracking-tight md:text-7xl lg:text-8xl text-slate-900">
              Automated Manuscript
              <span className="block text-primary pb-2 mt-2">
                Formatter
              </span>
            </motion.h1>
            
            <motion.p variants={itemVariants} className="mx-auto mb-10 max-w-2xl text-lg font-medium text-slate-600 md:text-xl leading-relaxed">
              Transform academic manuscripts into professionally styled DOCX documents.
              Supports major citation styles, strict validation, and real-time preview for high-impact research.
            </motion.p>
            
            <motion.div variants={itemVariants} className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/upload"
                className="group relative inline-flex items-center gap-2 overflow-hidden rounded-xl bg-primary px-8 py-4 text-base font-bold text-white transition-all hover:bg-blue-700 hover:scale-[1.02] active:scale-95 shadow-lg shadow-primary/25"
              >
                <span className="relative z-10 flex items-center gap-2">
                  Start Formatting
                  <span className="material-symbols-outlined text-[20px] transition-transform group-hover:translate-x-1">arrow_forward</span>
                </span>
                <div className="absolute inset-0 z-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 ease-out group-hover:translate-x-full" />
              </Link>
              <Link
                href="/docs"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-8 py-4 text-base font-bold text-slate-700 transition-all hover:bg-slate-50 hover:border-slate-400 hover:scale-[1.02] active:scale-95 shadow-sm"
              >
                Read Documentation
                <span className="material-symbols-outlined text-[20px]">menu_book</span>
              </Link>
            </motion.div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.8, ease: "easeOut" }}
            className="mt-24 grid grid-cols-3 gap-8 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm shadow-sm md:text-base lg:text-lg"
          >
            <div>
              <div className="mb-2 text-4xl font-black text-slate-900 md:text-5xl lg:text-6xl"><Counter from={0} to={9} suffix="+" /></div>
              <div className="font-medium text-slate-500 uppercase tracking-wider text-xs">Citation Styles</div>
            </div>
            <div className="border-x border-slate-200">
              <div className="mb-2 text-4xl font-black text-slate-900 md:text-5xl lg:text-6xl"><Counter from={0} to={3} /></div>
              <div className="font-medium text-slate-500 uppercase tracking-wider text-xs">Input Formats</div>
            </div>
            <div>
              <div className="mb-2 text-4xl font-black text-primary md:text-5xl lg:text-6xl"><Counter from={0} to={100} suffix="%" /></div>
              <div className="font-medium text-slate-500 uppercase tracking-wider text-xs">Style Compliant</div>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-white py-32 border-t border-slate-200">
        <div className="container relative mx-auto max-w-6xl px-4">
          <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={containerVariants}
            className="mb-20 text-center"
          >
            <motion.h2 variants={itemVariants} className="mb-6 text-4xl font-extrabold text-slate-900 md:text-5xl tracking-tight">
              Why Choose AMF?
            </motion.h2>
            <motion.p variants={itemVariants} className="mx-auto max-w-3xl text-lg text-slate-600 font-medium">
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
                className={`group relative overflow-hidden rounded-3xl border border-slate-200 bg-slate-50/50 p-8 shadow-sm transition-all hover:shadow-lg ${feature.className}`}
              >
                <div className="relative z-10">
                  <div className="mb-6 inline-flex rounded-xl bg-white p-3 text-primary border border-slate-200 shadow-sm transition-colors group-hover:bg-primary group-hover:text-white group-hover:border-primary">
                    <span className="material-symbols-outlined text-[28px]">{feature.icon}</span>
                  </div>
                  <h3 className="mb-3 text-xl font-bold text-slate-900 tracking-tight">
                    {feature.title}
                  </h3>
                  <p className="text-base leading-relaxed text-slate-600">
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="overflow-hidden bg-slate-50 py-32 border-t border-slate-200">
        <div className="container mx-auto max-w-6xl px-4">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="mb-16 text-center"
          >
            <h2 className="mb-6 text-3xl font-extrabold text-slate-900 md:text-4xl tracking-tight">
              Supported Citation Styles
            </h2>
            <p className="text-lg text-slate-600 font-medium">
              Comprehensive compliance across every major academic discipline
            </p>
          </motion.div>
          
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="flex flex-wrap justify-center gap-4 max-w-4xl mx-auto"
          >
            {styles.map((style) => (
              <motion.span
                variants={itemVariants}
                whileHover={{ scale: 1.05, y: -2 }}
                key={style}
                className="cursor-default rounded-xl border border-slate-300 bg-white px-6 py-3 text-base font-bold text-slate-700 shadow-sm transition-colors hover:border-primary hover:text-primary"
              >
                {style}
              </motion.span>
            ))}
          </motion.div>
        </div>
      </section>

      <section className="relative overflow-hidden bg-slate-900 py-32 text-white">
        <div className="container relative mx-auto max-w-4xl px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="mb-8 text-4xl font-extrabold md:text-5xl lg:text-6xl tracking-tight text-white">
              Ready to Simplify Your Academic Formatting?
            </h2>
            <p className="mb-12 text-xl text-slate-400 font-medium">
              Get started in minutes. Open source and free for individual researchers.
            </p>
            <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-center">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-3 rounded-xl bg-primary px-10 py-5 text-lg font-bold text-white shadow-lg shadow-primary/20 transition-all hover:bg-blue-700 hover:shadow-xl"
                >
                  Start Now for Free
                  <span className="material-symbols-outlined text-[24px]">arrow_forward</span>
                </Link>
              </motion.div>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <a
                  href="https://github.com/amf/automated-manuscript-formatter"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-3 rounded-xl border-2 border-slate-700 bg-transparent px-10 py-5 text-lg font-bold text-white transition-all hover:border-slate-500 hover:bg-slate-800"
                >
                  <span className="material-symbols-outlined text-[24px]">code</span>
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
