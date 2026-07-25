import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Toaster } from 'sonner';
import dynamic from 'next/dynamic';

const UpdateBanner = dynamic(() => import('@/components/UpdateBanner'), { ssr: false });
const FeedbackWidget = dynamic(() => import('@/components/FeedbackWidget'), { ssr: false });
const CrashScreen = dynamic(() => import('@/components/CrashScreen'), { ssr: false });

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
    default: 'AMF - Automated Manuscript Formatter',
    template: '%s | AMF',
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
    <html lang="en" className="scroll-smooth">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <Navbar />
        <main className="min-h-screen">{children}</main>
        <UpdateBanner />
        <FeedbackWidget />
        <Footer />
        <Toaster position="top-right" richColors />
        <CrashScreen />
      </body>
    </html>
  );
}
