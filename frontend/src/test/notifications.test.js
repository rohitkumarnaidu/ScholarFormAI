import { describe, it, expect, beforeEach } from 'vitest';
import { createNotification, loadNotifications, saveNotifications, STORAGE_KEY } from '../utils/notifications';

describe('notifications', () => {
    beforeEach(() => {
        localStorage.clear();
    });

    describe('createNotification', () => {
        it('creates a notification with given type and message', () => {
            const n = createNotification('info', 'Hello world');
            expect(n.type).toBe('info');
            expect(n.message).toBe('Hello world');
            expect(n.read).toBe(false);
            expect(n.timestamp).toBeDefined();
            expect(n.id).toBeDefined();
        });

        it('includes meta properties', () => {
            const n = createNotification('success', 'Done', { jobId: '123' });
            expect(n.jobId).toBe('123');
        });

        it('generates unique ids', () => {
            const a = createNotification('info', 'a');
            const b = createNotification('info', 'b');
            expect(a.id).not.toBe(b.id);
        });
    });

    describe('loadNotifications', () => {
        it('returns empty array when no saved data', () => {
            expect(loadNotifications()).toEqual([]);
        });

        it('returns parsed notifications from localStorage', () => {
            const data = [{ id: '1', message: 'test' }];
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
            expect(loadNotifications()).toEqual(data);
        });

        it('returns empty array on corrupt data', () => {
            localStorage.setItem(STORAGE_KEY, 'not-json');
            expect(loadNotifications()).toEqual([]);
        });
    });

    describe('saveNotifications', () => {
        it('saves notifications to localStorage', () => {
            const data = [{ id: '1', message: 'test' }];
            saveNotifications(data);
            expect(JSON.parse(localStorage.getItem(STORAGE_KEY))).toEqual(data);
        });

        it('overwrites existing data', () => {
            saveNotifications([{ id: '1' }]);
            saveNotifications([{ id: '2' }]);
            expect(loadNotifications()).toEqual([{ id: '2' }]);
        });
    });
});
