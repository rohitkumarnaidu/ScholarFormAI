import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Navbar } from '@/components/Navbar';
import Footer from '@/components/Footer';
import { Toaster } from 'sonner';
import UpdateBanner from '@/components/UpdateBanner';
import FeedbackWidget from '@/components/FeedbackWidget';
import ClientProviders from '@/components/layout/ClientProviders';
import { ConditionalNavbar, ConditionalFooter } from '@/components/layout/ConditionalWrappers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: {
    default: 'ScholarForm AI - Automated Manuscript Formatter',
    template: '%s | ScholarForm AI',
  },
  description:
    'Enterprise-grade automated formatting of academic manuscripts into professionally styled DOCX documents. Supports APA, MLA, Chicago, IEEE, and more.',
  keywords: [
    'academic formatting',
    'manuscript formatter',
    'APA',
    'MLA',
    'Chicago',
    'IEEE',
    'DOCX',
    'academic writing',
    'thesis formatting',
  ],
  openGraph: {
    title: 'Automated Manuscript Formatter',
    description: 'Format academic manuscripts into professionally styled DOCX documents',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth" suppressHydrationWarning>

      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <ClientProviders>
          <ConditionalNavbar>
            <Navbar />
          </ConditionalNavbar>
          <main className="min-h-screen">{children}</main>
          <UpdateBanner />
          <FeedbackWidget />
          <ConditionalFooter>
            <Footer />
          </ConditionalFooter>
          <Toaster position="top-right" richColors />
        </ClientProviders>
      </body>
    </html>
  );
}
