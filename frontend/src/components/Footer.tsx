import Link from 'next/link';
import { FileText, Github } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-primary-950">
      <div className="container mx-auto max-w-7xl px-4 py-12">
        <div className="grid gap-8 md:grid-cols-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="rounded-lg bg-primary-500 p-1.5">
                <FileText className="h-5 w-5 text-white" />
              </div>
              <span className="font-bold text-primary-800 dark:text-white">AMF</span>
            </div>
            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
              Enterprise-grade automated formatting of academic manuscripts into professionally styled DOCX documents.
            </p>
          </div>
          <div>
            <h4 className="mb-4 text-sm font-semibold text-primary-800 dark:text-white">Product</h4>
            <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li><Link href="/format" className="hover:text-primary-600">Format</Link></li>
              <li><Link href="/styles" className="hover:text-primary-600">Styles</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="mb-4 text-sm font-semibold text-primary-800 dark:text-white">Documentation</h4>
            <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li><Link href="/docs" className="hover:text-primary-600">Getting Started</Link></li>
              <li><Link href="/docs" className="hover:text-primary-600">API Reference</Link></li>
              <li><Link href="/docs" className="hover:text-primary-600">CLI Guide</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="mb-4 text-sm font-semibold text-primary-800 dark:text-white">Community</h4>
            <ul className="space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li>
                <a href="https://github.com/amf/automated-manuscript-formatter" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 hover:text-primary-600">
                  <Github className="h-4 w-4" /> GitHub
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-8 border-t border-slate-200 pt-8 text-center text-sm text-slate-400 dark:border-slate-800">
          &copy; {new Date().getFullYear()} Automated Manuscript Formatter. Open source under MIT License.
        </div>
      </div>
    </footer>
  );
}
