// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/context/AuthContext';
import { useToast } from '@/src/context/ToastContext';
import { useTheme } from '@/src/context/ThemeContext';
import Footer from '@/src/components/Footer';
import { supabase } from '@/src/lib/supabaseClient';
import { UserProfileSchema } from '@/src/lib/schemas';
import { z } from 'zod';

const NAME_MAX = 80;
const INSTITUTION_MAX = 120;

export default function Profile() {
    usePageTitle('Profile');
    const { theme, toggleTheme } = useTheme();
    const [statusUpdates, setStatusUpdates] = useState(true);
    const [newsletter, setNewsletter] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [editName, setEditName] = useState('');
    const [editInstitution, setEditInstitution] = useState('');
    const [editSaving, setEditSaving] = useState(false);
    const [editError, setEditError] = useState(null);
    const [fieldErrors, setFieldErrors] = useState({});
    const [editSuccess, setEditSuccess] = useState(null);
    const [isDirty, setIsDirty] = useState(false);
    const [showPasswordForm, setShowPasswordForm] = useState(false);
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [passwordSaving, setPasswordSaving] = useState(false);
    const [passwordMessage, setPasswordMessage] = useState('');
    const [verifyStatus, setVerifyStatus] = useState('');
    const [cropImage, setCropImage] = useState(null);
    const canvasRef = useRef(null);
    const fileInputRef = useRef(null);
    const nameInputRef = useRef(null);
    const { user, signOut, refreshSession } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const handleAvatarClick = () => {
        if (fileInputRef.current) fileInputRef.current.value = '';
        fileInputRef.current?.click();
    };

    const handleAvatarChange = (event) => {
        if (!event.target.files || event.target.files.length === 0) return;
        const file = event.target.files[0];
        const reader = new FileReader();
        reader.onload = (e) => setCropImage({ src: e.target.result, fileExt: file.name.split('.').pop() });
        reader.readAsDataURL(file);
    };

    useEffect(() => {
        if (cropImage && canvasRef.current) {
            const img = new Image();
            img.onload = () => {
                const canvas = canvasRef.current;
                const ctx = canvas.getContext('2d');
                const size = Math.min(img.width, img.height);
                const startX = (img.width - size) / 2;
                const startY = (img.height - size) / 2;
                canvas.width = 300;
                canvas.height = 300;
                ctx.clearRect(0, 0, 300, 300);
                ctx.drawImage(img, startX, startY, size, size, 0, 0, 300, 300);
            };
            img.src = cropImage.src;
        }
    }, [cropImage]);

    const handleCropUpload = () => {
        if (!canvasRef.current || !cropImage) return;
        canvasRef.current.toBlob(async (blob) => {
            try {
                setUploading(true);
                setCropImage(null);
                const fileName = `${user.id}/${Math.random()}.${cropImage.fileExt}`;
                const { error: uploadError } = await supabase.storage
                    .from('avatars')
                    .upload(fileName, blob, { contentType: `image/${cropImage.fileExt}` });
                if (uploadError) throw uploadError;
                const { data: { publicUrl } } = supabase.storage.from('avatars').getPublicUrl(fileName);
                const { error: updateError } = await supabase.auth.updateUser({ data: { avatar_url: publicUrl } });
                if (updateError) throw updateError;
                await refreshSession();
            } catch (error) {
                console.error('Error uploading avatar:', error);
                addToast('Error uploading avatar: ' + error.message, 'error');
            } finally {
                setUploading(false);
            }
        });
    };

    const fullName = user?.user_metadata?.full_name || 'Scholar User';
    const email = user?.email || 'user@example.com';
    const avatarUrl = user?.user_metadata?.avatar_url || user?.user_metadata?.picture ||
        'https://lh3.googleusercontent.com/aida-public/AB6AXuCBAnQke1dGWniClQX7rHZBtni1hbRlIpllATyD41NPPw3Br765F9F0vIWQH7I2SezfqlRBNZW0hgkDJ4Kl-Ekd0MVD60AqnPJe_Q0QkDvG2fqpVzmz_HTsQKFKkBIvfvFH26zii0uK7s11gs1bnXmlnWvG6LS6GTXhY6thfBqwRUWqvuAIMWQfqwnAs0DFEX2j3QBP0F7mG913xvhu2iMMo_MIgxF_nqEmviIbI0G3jFBvWtp3KPkAPAxfc4YVXlrDPh_tJJ5ZgnHP';
    const role = user?.user_metadata?.institution || 'Academic Researcher';

    // ── Edit profile ──────────────────────────────────────
    const handleEditProfile = () => {
        setEditName(fullName);
        setEditInstitution(user?.user_metadata?.institution || '');
        setEditSuccess(null);
        setEditError(null);
        setFieldErrors({});
        setIsDirty(false);
        setIsEditing(true);
        setTimeout(() => nameInputRef.current?.focus(), 50);
    };

    const handleCancelEdit = useCallback(() => {
        if (isDirty && !window.confirm('You have unsaved changes. Discard them?')) return;
        setIsEditing(false);
        setIsDirty(false);
    }, [isDirty]);

    const handleSaveProfile = useCallback(async () => {
        setEditSaving(true);
        setEditError(null);
        setFieldErrors({});
        setEditSuccess(null);

        try {
            UserProfileSchema.parse({ name: editName, institution: editInstitution });
        } catch (err) {
            if (err instanceof z.ZodError) {
                const errors = {};
                err.errors.forEach(e => { errors[e.path[0]] = e.message; });
                setFieldErrors(errors);
                setEditSaving(false);
                return;
            }
        }

        try {
            const { error: updateError } = await supabase.auth.updateUser({
                data: { full_name: editName, institution: editInstitution }
            });
            if (updateError) throw updateError;
            await refreshSession();
            setIsDirty(false);
            setIsEditing(false);
            setEditSuccess('Profile updated successfully!');
            setTimeout(() => setEditSuccess(null), 3000);
        } catch (err) {
            console.error('Error updating profile:', err);
            setEditError(err.message || 'Failed to update profile');
        } finally {
            setEditSaving(false);
        }
    }, [editInstitution, editName, refreshSession]);

    // Keyboard shortcuts
    useEffect(() => {
        const onKey = (e) => {
            if (!isEditing) return;
            if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 's' || e.key === 'Enter')) {
                if (!editSaving) { e.preventDefault(); handleSaveProfile(); }
            }
            if (e.key === 'Escape') { handleCancelEdit(); }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [isEditing, editSaving, handleSaveProfile, handleCancelEdit]);

    // Warn on tab/window close with unsaved changes
    useEffect(() => {
        const onBeforeUnload = (e) => {
            if (isDirty) { e.preventDefault(); e.returnValue = ''; }
        };
        window.addEventListener('beforeunload', onBeforeUnload);
        return () => window.removeEventListener('beforeunload', onBeforeUnload);
    }, [isDirty]);

    // ── Institution verify ────────────────────────────────
    const handleVerifyInstitution = async () => {
        setVerifyStatus('sending');
        try {
            const { error } = await supabase.auth.updateUser({
                data: { institution_verified: false, institution_verify_requested: true }
            });
            if (error) throw error;
            setVerifyStatus('sent');
            setTimeout(() => setVerifyStatus(''), 3000);
        } catch (err) {
            console.error('Verify institution error:', err);
            setVerifyStatus('error');
            setTimeout(() => setVerifyStatus(''), 3000);
        }
    };

    // ── Change password ───────────────────────────────────
    const handleChangePassword = async () => {
        if (newPassword.length < 8) { setPasswordMessage('Password must be at least 8 characters'); return; }
        if (newPassword !== confirmPassword) { setPasswordMessage('Passwords do not match'); return; }
        setPasswordSaving(true);
        setPasswordMessage('');
        try {
            const { error } = await supabase.auth.updateUser({ password: newPassword });
            if (error) throw error;
            setPasswordMessage('Password updated successfully!');
            setNewPassword('');
            setConfirmPassword('');
            setTimeout(() => { setShowPasswordForm(false); setPasswordMessage(''); }, 2000);
        } catch (err) {
            setPasswordMessage(err.message || 'Failed to update password');
        } finally {
            setPasswordSaving(false);
        }
    };

    return (
        <div className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 min-h-screen flex flex-col transition-colors duration-300">
            <main className="max-w-[960px] mx-auto px-4 sm:px-6 py-8 sm:py-10 flex flex-col gap-8 w-full animate-in fade-in duration-500">
                <div className="flex flex-col gap-2">
                    <h1 className="text-slate-900 dark:text-white text-3xl sm:text-4xl font-black leading-tight tracking-tight">Account Settings</h1>
                    <p className="text-slate-500 dark:text-slate-400 text-base sm:text-lg font-normal">Manage your academic profile, subscription details, and personal preferences.</p>
                </div>

                <section className="bg-glass-surface backdrop-blur-xl border border-glass-border shadow-xl shadow-primary/5 overflow-hidden">
                    <div className="p-6 md:p-8">
                        <div className="flex flex-col md:flex-row gap-8 items-center md:items-start">
                            {/* Avatar */}
                            <div className="relative group shrink-0">
                                <div
                                    className="bg-center bg-no-repeat aspect-square bg-cover rounded-full h-32 w-32 shadow-inner border-4 border-white dark:border-slate-800 transition-opacity"
                                    style={{ backgroundImage: `url("${avatarUrl}")`, opacity: uploading ? 0.5 : 1 }}
                                />
                                {uploading && (
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <span className="material-symbols-outlined animate-spin text-white drop-shadow-md">refresh</span>
                                    </div>
                                )}
                                <button
                                    onClick={handleAvatarClick}
                                    disabled={uploading}
                                    className="absolute bottom-0 right-0 bg-primary text-white p-2 rounded-full shadow-lg hover:bg-primary-hover transition-all flex items-center justify-center disabled:opacity-50 min-w-[44px] min-h-[44px]"
                                    aria-label="Change avatar"
                                >
                                    <span className="material-symbols-outlined text-[18px]">edit</span>
                                </button>
                                <input type="file" ref={fileInputRef} onChange={handleAvatarChange} accept="image/*" className="hidden" />
                            </div>

                            {/* Profile info / edit form */}
                            <div className="flex-1 flex flex-col gap-4 text-center md:text-left">
                                {isEditing ? (
                                    <div className="flex flex-col gap-3" role="form" aria-label="Edit profile">
                                        {/* Unsaved-changes badge */}
                                        {isDirty && (
                                            <span className="inline-flex items-center gap-1.5 self-start text-[10px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
                                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block animate-pulse" aria-hidden="true" />
                                                Unsaved changes
                                            </span>
                                        )}

                                        {/* Name field */}
                                        <div>
                                            <div className="flex justify-between items-end mb-1 px-0.5">
                                                <label htmlFor="edit-name" className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Full Name</label>
                                                <span className={`text-[10px] font-medium tabular-nums transition-colors ${editName.length > NAME_MAX * 0.9 ? 'text-amber-500' : 'text-slate-400'}`}>
                                                    {editName.length}/{NAME_MAX}
                                                </span>
                                            </div>
                                            <input
                                                id="edit-name"
                                                ref={nameInputRef}
                                                type="text"
                                                value={editName}
                                                maxLength={NAME_MAX}
                                                onChange={(e) => { setEditName(e.target.value); setIsDirty(true); }}
                                                className={`w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border ${fieldErrors.name ? 'border-red-500' : 'border-slate-200 dark:border-slate-700'} focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-sm outline-none`}
                                                placeholder="Enter your name"
                                                aria-describedby={fieldErrors.name ? 'name-error' : undefined}
                                                aria-invalid={!!fieldErrors.name}
                                            />
                                            {fieldErrors.name && <p id="name-error" className="text-[10px] text-red-500 mt-1 px-1 font-medium" role="alert">{fieldErrors.name}</p>}
                                        </div>

                                        {/* Institution field */}
                                        <div>
                                            <div className="flex justify-between items-end mb-1 px-0.5">
                                                <label htmlFor="edit-institution" className="block text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Institution</label>
                                                <span className={`text-[10px] font-medium tabular-nums transition-colors ${editInstitution.length > INSTITUTION_MAX * 0.9 ? 'text-amber-500' : 'text-slate-400'}`}>
                                                    {editInstitution.length}/{INSTITUTION_MAX}
                                                </span>
                                            </div>
                                            <input
                                                id="edit-institution"
                                                type="text"
                                                value={editInstitution}
                                                maxLength={INSTITUTION_MAX}
                                                onChange={(e) => { setEditInstitution(e.target.value); setIsDirty(true); }}
                                                className={`w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border ${fieldErrors.institution ? 'border-red-500' : 'border-slate-200 dark:border-slate-700'} focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-sm outline-none`}
                                                placeholder="University or Organisation"
                                                aria-describedby={fieldErrors.institution ? 'institution-error' : undefined}
                                                aria-invalid={!!fieldErrors.institution}
                                            />
                                            {fieldErrors.institution && <p id="institution-error" className="text-[10px] text-red-500 mt-1 px-1 font-medium" role="alert">{fieldErrors.institution}</p>}
                                        </div>

                                        {editError && <p className="text-sm text-red-500" role="alert">{editError}</p>}
                                        {editSuccess && <p className="text-sm text-green-500" role="status">{editSuccess}</p>}

                                        <div className="flex flex-wrap gap-3">
                                            <button onClick={handleSaveProfile} disabled={editSaving}
                                                title="Save Changes (Ctrl+S or Ctrl+Enter)"
                                                className="px-5 py-2.5 bg-primary text-white rounded-lg text-sm font-bold hover:bg-primary-hover transition-colors disabled:opacity-50 active:scale-95">
                                                {editSaving ? 'Saving…' : 'Save Changes'}
                                            </button>
                                            <button onClick={handleCancelEdit}
                                                className="px-5 py-2.5 bg-white/10 dark:bg-white/10 text-slate-700 dark:text-slate-100 rounded-lg text-sm font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors active:scale-95">
                                                Cancel
                                            </button>
                                        </div>

                                        <p className="text-[10px] text-slate-400 dark:text-slate-600 select-none">
                                            Tip: <kbd className="font-mono bg-slate-100 dark:bg-slate-800 rounded px-1">Ctrl+S</kbd> saves &middot; <kbd className="font-mono bg-slate-100 dark:bg-slate-800 rounded px-1">Esc</kbd> cancels
                                        </p>
                                    </div>
                                ) : (
                                    <>
                                        <div className="flex flex-col gap-1">
                                            <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
                                                <h2 className="text-slate-900 dark:text-white text-2xl font-bold">{fullName}</h2>
                                                <div className="flex h-7 items-center justify-center gap-x-1.5 rounded-full bg-primary/10 px-3 border border-primary/20">
                                                    <span className="material-symbols-outlined text-primary text-[16px] font-bold">star</span>
                                                    <p className="text-primary text-xs font-bold uppercase tracking-wider">Free Plan</p>
                                                </div>
                                            </div>
                                            <p className="text-slate-600 dark:text-slate-400 font-medium text-lg">{role}</p>
                                            <p className="text-slate-500 dark:text-slate-500 text-sm break-all">{email}</p>
                                        </div>
                                        {editSuccess && (
                                            <p className="text-sm text-green-500 font-medium animate-in fade-in duration-300" role="status">
                                                ✓ {editSuccess}
                                            </p>
                                        )}
                                        <div className="flex flex-wrap gap-3 justify-center md:justify-start mt-2">
                                            <button onClick={handleEditProfile}
                                                className="px-5 py-2.5 bg-white/10 dark:bg-white/10 text-slate-700 dark:text-slate-100 rounded-lg text-sm font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors active:scale-95">
                                                Edit Profile
                                            </button>
                                            <button onClick={handleVerifyInstitution} disabled={verifyStatus === 'sending'}
                                                className="px-5 py-2.5 bg-white/10 dark:bg-white/10 text-slate-700 dark:text-slate-100 rounded-lg text-sm font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 active:scale-95">
                                                {verifyStatus === 'sending' ? 'Sending…' : verifyStatus === 'sent' ? '✓ Verification Requested' : verifyStatus === 'error' ? 'Failed — Retry' : 'Verify Institution'}
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="bg-white/5 dark:bg-white/5 border-t border-slate-200 dark:border-slate-800 px-4 sm:px-8 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
                        <p className="text-sm text-slate-500 dark:text-slate-400">Member since <span className="font-bold text-slate-900 dark:text-slate-200">{new Date(user?.created_at || Date.now()).toLocaleDateString()}</span></p>
                        <button onClick={() => router.push('/settings')} className="text-primary text-sm font-bold hover:underline">Upgrade Plan</button>
                    </div>
                </section>

                <section className="flex flex-col gap-4">
                    <h2 className="text-slate-900 dark:text-white text-xl font-bold px-1 tracking-tight">Account Actions</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <button onClick={() => setShowPasswordForm(!showPasswordForm)}
                            className="flex items-center justify-between p-5 bg-glass-surface backdrop-blur-xl border border-glass-border rounded-xl hover:border-primary/50 hover:shadow-md transition-all group text-left min-h-[64px]">
                            <div className="flex items-center gap-4">
                                <div className="p-2.5 bg-white/10 dark:bg-white/10 rounded-xl text-slate-600 dark:text-slate-300 group-hover:bg-primary group-hover:text-white transition-colors">
                                    <span className="material-symbols-outlined">lock</span>
                                </div>
                                <span className="font-bold text-slate-700 dark:text-slate-200">Change Password</span>
                            </div>
                            <span className="material-symbols-outlined text-slate-400 group-hover:text-primary transition-colors">chevron_right</span>
                        </button>
                        <button onClick={() => router.push('/settings')}
                            className="flex items-center justify-between p-5 bg-glass-surface backdrop-blur-xl border border-glass-border rounded-xl hover:border-primary/50 hover:shadow-md transition-all group text-left min-h-[64px]">
                            <div className="flex items-center gap-4">
                                <div className="p-2.5 bg-primary/10 rounded-xl text-primary group-hover:bg-primary group-hover:text-white transition-colors">
                                    <span className="material-symbols-outlined">payments</span>
                                </div>
                                <span className="font-bold text-slate-700 dark:text-slate-200">Manage Subscription</span>
                            </div>
                            <span className="material-symbols-outlined text-slate-400 group-hover:text-primary transition-colors">chevron_right</span>
                        </button>
                        <button onClick={async () => { await signOut({ redirectToLogin: true }); }}
                            className="flex items-center justify-between p-5 bg-white dark:bg-slate-900 border border-red-100 dark:border-red-900/20 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/10 transition-all group text-left min-h-[64px]">
                            <div className="flex items-center gap-4">
                                <div className="p-2.5 bg-red-100 dark:bg-red-900/20 rounded-xl text-red-600 group-hover:bg-red-600 group-hover:text-white transition-colors">
                                    <span className="material-symbols-outlined">logout</span>
                                </div>
                                <span className="font-bold text-red-600">Sign out</span>
                            </div>
                        </button>
                    </div>

                    {showPasswordForm && (
                        <div className="bg-glass-surface backdrop-blur-xl border border-glass-border rounded-xl p-6 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
                            <h3 className="text-slate-900 dark:text-white font-bold text-lg mb-4">Change Password</h3>
                            <div className="flex flex-col gap-3 max-w-md">
                                <input type="password" placeholder="New Password (min 8 chars)" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                                    className="w-full px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none" />
                                <input type="password" placeholder="Confirm New Password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="w-full px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none" />
                                {passwordMessage && <p className={`text-sm ${passwordMessage.includes('success') ? 'text-green-500' : 'text-red-500'}`} role="alert">{passwordMessage}</p>}
                                <div className="flex gap-3">
                                    <button onClick={handleChangePassword} disabled={passwordSaving}
                                        className="px-5 py-2.5 bg-primary text-white rounded-lg text-sm font-bold hover:bg-primary-hover transition-colors disabled:opacity-50 active:scale-95">
                                        {passwordSaving ? 'Updating…' : 'Update Password'}
                                    </button>
                                    <button onClick={() => { setShowPasswordForm(false); setPasswordMessage(''); setNewPassword(''); setConfirmPassword(''); }}
                                        className="px-5 py-2.5 bg-white/10 dark:bg-white/10 text-slate-700 dark:text-slate-100 rounded-lg text-sm font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors active:scale-95">
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </section>

                <section className="flex flex-col gap-4">
                    <h2 className="text-slate-900 dark:text-white text-xl font-bold px-1 tracking-tight">Preferences</h2>
                    <div className="bg-glass-surface backdrop-blur-xl border border-glass-border rounded-xl divide-y divide-slate-100 dark:divide-slate-800 shadow-sm">
                        {[
                            { label: 'Dark Mode', desc: 'Toggle between light and dark themes', value: theme === 'dark', action: toggleTheme },
                            { label: 'Manuscript Status Updates', desc: 'Receive emails when your formatting process completes', value: statusUpdates, action: () => setStatusUpdates(!statusUpdates) },
                            { label: 'Product Updates & Newsletter', desc: 'Get notified about new academic templates and formatting features', value: newsletter, action: () => setNewsletter(!newsletter) },
                        ].map(({ label, desc, value, action }) => (
                            <div key={label} className="flex items-center justify-between p-6">
                                <div className="flex flex-col gap-1">
                                    <p className="font-bold text-slate-800 dark:text-white">{label}</p>
                                    <p className="text-sm text-slate-500 dark:text-slate-400">{desc}</p>
                                </div>
                                <button onClick={action} role="switch" aria-checked={value} aria-label={label}
                                    className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${value ? 'bg-primary' : 'bg-slate-200 dark:bg-slate-700'}`}>
                                    <span className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${value ? 'translate-x-5' : 'translate-x-0'}`} />
                                </button>
                            </div>
                        ))}
                    </div>
                </section>

                <footer className="mt-4 text-center pb-8">
                    <p className="text-xs sm:text-sm text-slate-400 font-medium tracking-wide italic break-words">
                        User ID: <span className="font-mono not-italic font-bold">{user?.id?.slice(0, 8) || 'Unknown'}</span> | Join Date: {new Date(user?.created_at || Date.now()).toLocaleDateString()}
                    </p>
                </footer>
            </main>

            {cropImage && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
                    <div className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-sm overflow-hidden border border-slate-200 dark:border-slate-800 animate-in zoom-in-95 duration-200">
                        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-white/5 dark:bg-white/5">
                            <h3 className="font-bold text-slate-800 dark:text-slate-100">Adjust Avatar</h3>
                            <button onClick={() => setCropImage(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1" aria-label="Close">
                                <span className="material-symbols-outlined text-xl">close</span>
                            </button>
                        </div>
                        <div className="p-6 flex flex-col items-center gap-4">
                            <p className="text-sm text-center text-slate-500 dark:text-slate-400">1:1 square crop from center</p>
                            <div className="rounded-full overflow-hidden border-4 border-slate-100 dark:border-slate-800 shadow-inner w-[200px] h-[200px] flex items-center justify-center bg-slate-50 dark:bg-slate-950">
                                <canvas ref={canvasRef} className="w-full h-full object-cover" />
                            </div>
                            <button onClick={handleCropUpload}
                                className="w-full mt-4 py-2.5 bg-primary text-white rounded-lg font-bold hover:bg-primary-hover transition-colors active:scale-95">
                                Upload Avatar
                            </button>
                        </div>
                    </div>
                </div>
            )}
            <Footer variant="app" />
        </div>
    );
}
