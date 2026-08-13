'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileText, Menu, X, Github } from 'lucide-react';

const links = [
  { href: '/', label: 'Home' },
  { href: '/format', label: 'Format' },
  { href: '/styles', label: 'Styles' },
  { href: '/issues', label: 'Issues' },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200 bg-white/90 backdrop-blur-sm dark:border-slate-800 dark:bg-primary-950/90">
      <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="rounded-lg bg-primary-500 p-1.5">
            <FileText className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-bold text-primary-800 dark:text-white">
            AMF
          </span>
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
                pathname === link.href
                  ? 'bg-primary-50 text-primary-700 dark:bg-primary-800 dark:text-primary-200'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-primary-800 dark:hover:text-white'
              }`}
            >
              {link.label}
            </Link>
          ))}
          <a
            href="https://github.com/amf/automated-manuscript-formatter"
            target="_blank"
            rel="noopener noreferrer"
            className="ml-2 rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-primary-800"
          >
            <Github className="h-5 w-5" />
          </a>
          
          <div className="ml-4 flex items-center gap-2 border-l border-slate-200 pl-4 dark:border-slate-800">
            <Link
              href="/login"
              className="rounded-lg px-3.5 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-primary-800 dark:hover:text-white"
            >
              Login
            </Link>
            <Link
              href="/signup"
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
            >
              Sign Up
            </Link>
          </div>
        </div>

        <button
          onClick={() => setOpen(!open)}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 md:hidden dark:text-slate-400 dark:hover:bg-primary-800"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-slate-200 px-4 pb-4 md:hidden dark:border-slate-800">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                pathname === link.href
                  ? 'text-primary-700 dark:text-primary-200'
                  : 'text-slate-600 dark:text-slate-400'
              }`}
            >
              {link.label}
            </Link>
          ))}
          <div className="mt-4 flex flex-col gap-2 border-t border-slate-200 pt-4 dark:border-slate-800">
            <Link
              href="/login"
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2 text-center text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-primary-800"
            >
              Login
            </Link>
            <Link
              href="/signup"
              onClick={() => setOpen(false)}
              className="block rounded-lg bg-primary-600 px-3 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-primary-700"
            >
              Sign Up
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
