import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationPreferences,
} from "@/services/api.notifications";

export const notificationKeys = {
  all: ["notifications"] as const,
  preferences: () => [...notificationKeys.all, "preferences"] as const,
};

export function useNotificationPreferences(enabled = true) {
  return useQuery({
    queryKey: notificationKeys.preferences(),
    queryFn: getNotificationPreferences,
    enabled,
  });
}

export function useUpdateNotificationPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (preferences: Partial<NotificationPreferences>) =>
      updateNotificationPreferences(preferences),
    onSuccess: (data) => {
      queryClient.setQueryData(notificationKeys.preferences(), data);
      toast.success("Notification preferences updated");
    },
    onError: (e) => {
      toast.error(
        `Failed to update preferences: ${
          e instanceof Error ? e.message : "Unknown error"
        }`
      );
    },
  });
}
