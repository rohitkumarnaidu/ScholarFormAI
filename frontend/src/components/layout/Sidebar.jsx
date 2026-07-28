// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { memo, useMemo, useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

const APP_GUEST_LINKS = [
  { href: '/upload', label: 'Upload', icon: 'upload_file' },
  { href: '/templates', label: 'Templates', icon: 'grid_view' },
  { href: '/template-editor', label: 'Template Editor', icon: 'edit_document' },
];

const USER_MAIN_LINKS_BY_MODE = {
  formatter: [
    { href: '/dashboard', label: 'Dashboard', icon: 'space_dashboard' },
    { href: '/upload', label: 'Upload', icon: 'upload_file' },
    { href: '/history', label: 'History', icon: 'history' },
    { href: '/templates', label: 'Templates', icon: 'grid_view' },
  ],
  generator: [
    { href: '/dashboard', label: 'Dashboard', icon: 'space_dashboard' },
    { href: '/generate', label: 'Generator', icon: 'magic_button' },
    { href: '/history', label: 'History', icon: 'history' },
    { href: '/templates', label: 'Templates', icon: 'grid_view' },
  ],
};

const USER_SECONDARY_LINKS = [
  { href: '/batch-upload', label: 'Batch Upload', icon: 'upload' },
  { href: '/template-editor', label: 'Template Editor', icon: 'edit_document' },
  { href: '/results', label: 'Validation Results', icon: 'fact_check' },
  { href: '/providers', label: 'Providers', icon: 'cloud' },
  { href: '/api-keys', label: 'API Keys', icon: 'key' },
  { href: '/feedback', label: 'Feedback', icon: 'chat' },
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
      onClick={() => onNavigate(href)}
      title={isCollapsed ? label : undefined}
      aria-label={label}
      className={`active-nav-link flex items-center gap-3 py-2.5 rounded-xl text-[15px] font-semibold active:scale-[0.98] transition-all ${isCollapsed ? 'px-0 justify-center w-11 h-11 mx-auto' : 'px-3 w-full'} ${active ? 'bg-primary/10 text-primary dark:bg-primary/25 dark:text-blue-400 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white'}`}
    >
      <span className={`material-symbols-outlined shrink-0 text-[20px] ${active ? 'fill-current' : ''}`} aria-hidden="true">{icon}</span>
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

  const mainNavLinks = useMemo(() =>
    (uiUser === null) ? APP_GUEST_LINKS : (USER_MAIN_LINKS_BY_MODE[activeMode] ?? USER_MAIN_LINKS_BY_MODE.formatter),
    [uiUser, activeMode]);

  const secondaryNavLinks = useMemo(() => {
    if (uiUser === null) return [];
    const links = [...USER_SECONDARY_LINKS];
    if (isAdminUser) links.push({ href: '/admin-dashboard', label: 'Admin Dashboard', icon: 'admin_panel_settings' });
    return links;
  }, [uiUser, isAdminUser]);

  const actionData = useMemo(() => {
    if (uiUser === null) return { href: '/signup', label: 'Get Started', icon: 'rocket_launch' };
    return activeMode === 'generator'
      ? { href: '/generate', label: 'New Draft', icon: 'edit_square' }
      : { href: '/upload', label: 'New Format', icon: 'add_circle' };
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
          <button onClick={onClose} className="lg:hidden p-1 text-slate-500 hover:text-slate-900 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-white/10 surface-ladder-hover-10" aria-label="Close Sidebar">
            <span className="material-symbols-outlined" aria-hidden="true">close</span>
          </button>
        </div>
      )}

      <div className={`mb-3 ${isCollapsed ? 'px-0' : 'px-1'}`}>
        <div className={`flex flex-col gap-1 rounded-xl bg-[#f0f1f3] dark:bg-white/5 surface-ladder-06 ring-1 ring-black/5 dark:ring-white/10 surface-ladder-border-10 ${isCollapsed ? 'p-1' : 'p-1.5'}`}>
          {['formatter', 'generator'].map(m => (
            <button
              key={m}
              onClick={() => handleModeChange(m)}
              title={isCollapsed ? (m.charAt(0).toUpperCase() + m.slice(1)) : undefined}
              aria-label={m.charAt(0).toUpperCase() + m.slice(1)}
              className={`active-mode-btn flex items-center gap-3 py-2 rounded-xl text-[15px] active:scale-[0.98] transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary ${isCollapsed ? 'px-0 justify-center w-10 h-10 mx-auto' : 'px-3 w-full'} ${activeMode === m ? 'bg-white dark:bg-white/10 shadow-sm text-slate-900 dark:text-white font-bold ring-1 ring-slate-900/5 dark:ring-white/10' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white font-medium hover:bg-slate-200/50 dark:hover:bg-white/5'}`}
            >
              <span className="material-symbols-outlined shrink-0 text-[20px]" aria-hidden="true">{m === 'formatter' ? 'format_align_left' : 'magic_button'}</span>
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
            <NavItem href="/settings" label="Settings" icon="settings" active={isLinkActive(pathname, "/settings")} isCollapsed={isCollapsed} onNavigate={handleNavigation} />
            <NavItem href="/contributing" label="Contributing" icon="code" active={isLinkActive(pathname, "/contributing")} isCollapsed={isCollapsed} onNavigate={handleNavigation} />
          </>
        )}
        <button
          onClick={() => handleNavigation(actionData.href)}
          title={isCollapsed ? actionData.label : undefined}
          className={`h-11 flex items-center justify-center gap-2 rounded-xl bg-primary hover:bg-primary-hover text-white text-[15px] font-bold active:scale-[0.98] transition-all shadow-lg shadow-primary/20 shrink-0 overflow-hidden ${isCollapsed ? 'w-11 px-0' : 'w-full px-4'}`}
        >
          <span className="material-symbols-outlined shrink-0 text-[20px]">{actionData.icon}</span>
          {!isCollapsed && <span className="truncate">{actionData.label}</span>}
        </button>
        {uiUser && (
          <button
            onClick={handleSignOut}
            title={isCollapsed ? 'Sign Out' : undefined}
            className={`h-10 flex items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-white/10 surface-ladder-border-10 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/10 surface-ladder-hover-10 active:scale-[0.98] transition-all ${isCollapsed ? 'w-11 px-0' : 'w-full px-4'}`}
          >
            <span className="material-symbols-outlined shrink-0 text-[20px]">logout</span>
            {!isCollapsed && <span className="truncate font-semibold">Sign Out</span>}
          </button>
        )}
      </div>
    </div>
  );
});

export default Sidebar;
