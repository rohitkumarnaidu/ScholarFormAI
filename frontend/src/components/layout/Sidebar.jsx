// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo, useMemo, useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { AlignLeft, LogOut, Wand2, X, Upload, LayoutGrid, FileEdit, LayoutDashboard, History, ClipboardCheck, Cloud, Key, MessageSquare, Shield, Rocket, PenSquare, PlusCircle, Settings, Code } from 'lucide-react';
import Button from '@/components/ui/Button';

const APP_GUEST_LINKS = [
  { href: '/upload', label: 'Upload', icon: Upload },
  { href: '/templates', label: 'Templates', icon: LayoutGrid },
  { href: '/template-editor', label: 'Template Editor', icon: FileEdit },
];

const SHARED_USER_LINKS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/history', label: 'History', icon: History },
  { href: '/templates', label: 'Templates', icon: LayoutGrid },
];

const MODE_SPECIFIC_LINKS = {
  formatter: { href: '/upload', label: 'Upload', icon: Upload },
  generator: { href: '/generate', label: 'Generator', icon: Wand2 },
};

const USER_SECONDARY_LINKS = [
  { href: '/batch-upload', label: 'Batch Upload', icon: Upload },
  { href: '/template-editor', label: 'Template Editor', icon: FileEdit },
  { href: '/results', label: 'Validation Results', icon: ClipboardCheck },
  { href: '/providers', label: 'Providers', icon: Cloud },
  { href: '/api-keys', label: 'API Keys', icon: Key },
  { href: '/feedback', label: 'Feedback', icon: MessageSquare },
];

const RESULTS_ALIAS_PREFIXES = ['/compare', '/preview', '/edit', '/download'];

const isLinkActive = (pathname, href) => {
  if (!href.startsWith('/') || href.startsWith('//')) return false;
  if (href === '/results') {
    return pathname === '/results'
      || pathname.startsWith('/results/')
      || RESULTS_ALIAS_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  }
  return pathname === href || pathname.startsWith(`${href}/`);
};

const NavItem = memo(function NavItem({ href, label, icon, active, isCollapsed, onNavigate }) {
  return (
    <button
      type="button"
      onClick={() => onNavigate(href)}
      title={isCollapsed ? label : undefined}
      aria-label={label}
      className={`active-nav-link flex items-center gap-3 py-2.5 rounded-xl text-[15px] font-semibold active:scale-[0.98] transition-all ${isCollapsed ? 'px-0 justify-center w-11 h-11 mx-auto' : 'px-3 w-full'} ${active ? 'bg-primary/10 text-primary dark:bg-primary/25 dark:text-blue-400 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white'}`}
    >
      {icon && typeof icon === 'function' ? icon({ className: `shrink-0 w-5 h-5 ${active ? 'fill-current text-current' : ''}`, 'aria-hidden': 'true' }) : (icon && typeof icon === 'object' && 'render' in icon) ? React.createElement(icon, { className: `shrink-0 w-5 h-5 ${active ? 'fill-current text-current' : ''}`, 'aria-hidden': 'true' }) : null}
      {!isCollapsed && <span className="truncate">{label}</span>}
    </button>
  );
});

NavItem.displayName = 'NavItem';

const Sidebar = memo(function Sidebar({ section = 'shared', onClose, isCollapsed = false }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, signOut, loading } = useAuth();

  const forceGuestMode = useMemo(() => searchParams?.get('guest') === '1', [searchParams]);
  const uiUser = forceGuestMode ? null : (loading ? undefined : user);

  const isAdminUser = useMemo(() => Boolean(
    uiUser?.is_admin
    || uiUser?.app_metadata?.role === 'admin'
    || uiUser?.user_metadata?.role === 'admin'
    || uiUser?.role === 'admin'
  ), [uiUser]);

  const activeMode = useMemo(() => {
    if (section === 'generator' || section === 'formatter') return section;
    return pathname.startsWith('/generate') ? 'generator' : 'formatter';
  }, [section, pathname]);

  const mainNavLinks = useMemo(() => {
    if (uiUser === null) return APP_GUEST_LINKS;
    const modeLink = MODE_SPECIFIC_LINKS[activeMode] || MODE_SPECIFIC_LINKS.formatter;
    return [
      SHARED_USER_LINKS[0],
      modeLink,
      SHARED_USER_LINKS[1],
      SHARED_USER_LINKS[2]
    ];
  }, [uiUser, activeMode]);

  const secondaryNavLinks = useMemo(() => {
    if (uiUser === null) return [];
    const links = [...USER_SECONDARY_LINKS];
    if (isAdminUser) links.push({ href: '/admin-dashboard', label: 'Admin Dashboard', icon: Shield });
    return links;
  }, [uiUser, isAdminUser]);

  const actionData = useMemo(() => {
    if (uiUser === null) return { href: '/signup', label: 'Get Started', icon: Rocket };
    return activeMode === 'generator'
      ? { href: '/generate', label: 'New Draft', icon: PenSquare }
      : { href: '/upload', label: 'New Format', icon: PlusCircle };
  }, [uiUser, activeMode]);

  const handleNavigation = useCallback((href) => {
    router.push(href);
    if (onClose) onClose();
  }, [router, onClose]);

  const handleModeChange = useCallback((newMode) => {
    if (!uiUser) {
      router.push('/signup');
    } else {
      router.push(newMode === 'generator' ? '/generate' : '/upload');
    }
    if (onClose) onClose();
  }, [uiUser, router, onClose]);

  const handleSignOut = useCallback(async () => {
    await signOut({ redirectToLogin: true });
    if (onClose) onClose();
  }, [signOut, onClose]);

  return (
    <div className={`flex flex-col h-full py-4 w-full ${isCollapsed ? 'px-2' : 'px-3'}`}>
      {onClose && (
        <div className="flex justify-end mb-4 pr-1">
          <Button variant="ghost" size="icon" onClick={onClose} className="lg:hidden size-8 text-slate-500 rounded-lg hover:bg-slate-100 dark:hover:bg-white/10" aria-label="Close Sidebar">
            <X />
          </Button>
        </div>
      )}

      <div className={`mb-3 ${isCollapsed ? 'px-0' : 'px-1'}`}>
        <div className={`flex flex-col gap-1 rounded-xl bg-[#f0f1f3] dark:bg-white/5 ring-1 ring-black/5 dark:ring-white/10 ${isCollapsed ? 'p-1' : 'p-1.5'}`}>
          {['formatter', 'generator'].map(m => (
            <button
              type="button"
              key={m}
              onClick={() => handleModeChange(m)}
              title={isCollapsed ? (m.charAt(0).toUpperCase() + m.slice(1)) : undefined}
              aria-label={m.charAt(0).toUpperCase() + m.slice(1)}
              className={`active-mode-btn flex items-center gap-3 py-2 rounded-xl text-[15px] active:scale-[0.98] transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${isCollapsed ? 'px-0 justify-center w-10 h-10 mx-auto' : 'px-3 w-full'} ${activeMode === m ? 'bg-white dark:bg-white/10 shadow-sm text-slate-900 dark:text-white font-bold ring-1 ring-slate-900/5 dark:ring-white/10' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white font-medium hover:bg-slate-200/50 dark:hover:bg-white/5'}`}
            >
              {m === 'formatter' ? <AlignLeft className="shrink-0 text-[20px]" /> : <Wand2 className="shrink-0 text-[20px]" />}
              {!isCollapsed && <span className="truncate capitalize">{m}</span>}
            </button>
          ))}
        </div>
      </div>

      <nav className="flex-1 flex flex-col gap-1.5 overflow-y-auto overflow-x-hidden custom-scrollbar">
        {mainNavLinks.map(link => (
          <NavItem
            key={link.href}
            href={link.href}
            label={link.label}
            icon={link.icon}
            active={isLinkActive(pathname, link.href)}
            isCollapsed={isCollapsed}
            onNavigate={handleNavigation}
          />
        ))}
        {secondaryNavLinks.map(link => (
          <NavItem
            key={link.href}
            href={link.href}
            label={link.label}
            icon={link.icon}
            active={isLinkActive(pathname, link.href)}
            isCollapsed={isCollapsed}
            onNavigate={handleNavigation}
          />
        ))}
      </nav>

      <div className={`pt-4 flex flex-col gap-2 ${isCollapsed ? 'items-center' : ''}`}>
        {uiUser && (
          <>
            <NavItem href="/settings" label="Settings" icon={Settings} active={isLinkActive(pathname, "/settings")} isCollapsed={isCollapsed} onNavigate={handleNavigation} />
            <NavItem href="/contributing" label="Contributing" icon={Code} active={isLinkActive(pathname, "/contributing")} isCollapsed={isCollapsed} onNavigate={handleNavigation} />
          </>
        )}
        <Button
          onClick={() => handleNavigation(actionData.href)}
          title={isCollapsed ? actionData.label : undefined}
          aria-label={actionData.label}
          className={`h-11 shadow-lg shadow-primary/20 shrink-0 overflow-hidden ${isCollapsed ? 'w-11 px-0' : 'w-full px-4'}`}
        >
          {actionData.icon && typeof actionData.icon === 'function' ? actionData.icon({ className: "shrink-0 w-5 h-5" }) : (actionData.icon && typeof actionData.icon === 'object' && 'render' in actionData.icon) ? React.createElement(actionData.icon, { className: "shrink-0 w-5 h-5" }) : null}
          {!isCollapsed && <span className="truncate">{actionData.label}</span>}
        </Button>
        {uiUser && (
          <Button
            variant="outline"
            onClick={handleSignOut}
            title={isCollapsed ? 'Sign Out' : undefined}
            aria-label="Sign Out"
            className={`h-10 border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/10 ${isCollapsed ? 'w-11 px-0' : 'w-full px-4'}`}
          >
            <LogOut className="shrink-0 text-[20px]" />
            {!isCollapsed && <span className="truncate font-semibold">Sign Out</span>}
          </Button>
        )}
      </div>
    </div>
  );
});

export default Sidebar;
