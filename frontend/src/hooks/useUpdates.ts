import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  checkForUpdates, getUpdateSettings, getUpdateHistory, getChannels,
  updateSettings, downloadUpdate, installUpdate, rollbackUpdate, getVersionInfo,
  type UpdateSettings
} from "@/lib/update-api";

export const updateKeys = {
  all: ["updates"] as const,
  settings: () => [...updateKeys.all, "settings"] as const,
  history: () => [...updateKeys.all, "history"] as const,
  channels: () => [...updateKeys.all, "channels"] as const,
  version: () => [...updateKeys.all, "version"] as const,
};

export function useUpdateSettings() {
  return useQuery({
    queryKey: updateKeys.settings(),
    queryFn: getUpdateSettings,
  });
}

export function useUpdateChannels() {
  return useQuery({
    queryKey: updateKeys.channels(),
    queryFn: () => getChannels().then(c => c.channels),
  });
}

export function useUpdateHistory(limit = 10) {
  return useQuery({
    queryKey: [...updateKeys.history(), limit],
    queryFn: () => getUpdateHistory(limit).then(h => h.history),
  });
}

export function useVersionInfo() {
  return useQuery({
    queryKey: updateKeys.version(),
    queryFn: getVersionInfo,
  });
}

export function useSaveUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings: Partial<UpdateSettings>) => updateSettings(settings),
    onSuccess: (data) => {
      toast.success("Settings saved successfully");
      queryClient.setQueryData(updateKeys.settings(), data);
    },
    onError: (e) => {
      toast.error(`Failed to save settings: ${e instanceof Error ? e.message : "Unknown error"}`);
    }
  });
}

export function useCheckForUpdates() {
  return useMutation({
    mutationFn: (channel?: string) => checkForUpdates(channel),
    onError: (e) => {
      toast.error(`Check failed: ${e instanceof Error ? e.message : "Unknown error"}`);
    }
  });
}

export function useDownloadUpdate() {
  return useMutation({
    mutationFn: (version?: string) => downloadUpdate(version),
  });
}

export function useInstallUpdate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => installUpdate(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: updateKeys.history() });
    }
  });
}

export function useRollbackUpdate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (version?: string) => rollbackUpdate(version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: updateKeys.history() });
    }
  });
}
