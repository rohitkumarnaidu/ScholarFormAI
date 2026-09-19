import { fetchWithAuth } from "./api.core";

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
  metadata: any;
}

export interface NotificationPreferences {
  dnd_enabled: boolean;
  dnd_start_time: string;
  dnd_end_time: string;
}

export async function getNotifications(): Promise<Notification[]> {
  return fetchWithAuth("/api/v1/notifications");
}

export async function markNotificationAsRead(id: string): Promise<void> {
  return fetchWithAuth(`/api/v1/notifications/${encodeURIComponent(id)}/read`, {
    method: "PATCH",
  });
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  return fetchWithAuth("/api/v1/notifications/preferences");
}

export async function updateNotificationPreferences(
  preferences: Partial<NotificationPreferences>
): Promise<NotificationPreferences> {
  return fetchWithAuth("/api/v1/notifications/preferences", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(preferences),
  });
}
