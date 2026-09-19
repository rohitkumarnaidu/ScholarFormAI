import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  listApiKeys,
  createApiKey,
  deleteApiKey,
  testApiKey,
  getUsageStats,
  getSupportedProviders,
} from "@/src/services/api.keys";

export const apiKeyKeys = {
  all: ["api-keys"] as const,
  lists: () => [...apiKeyKeys.all, "list"] as const,
  list: (provider?: string) => [...apiKeyKeys.lists(), { provider }] as const,
  usageStats: (hours: number) => [...apiKeyKeys.all, "usageStats", hours] as const,
  supportedProviders: () => [...apiKeyKeys.all, "supportedProviders"] as const,
};

export function useApiKeys(provider?: string) {
  return useQuery({
    queryKey: apiKeyKeys.list(provider),
    queryFn: () => listApiKeys(provider),
  });
}

export function useApiKeyUsageStats(hours = 24) {
  return useQuery({
    queryKey: apiKeyKeys.usageStats(hours),
    queryFn: () => getUsageStats(hours),
  });
}

export function useSupportedProviders() {
  return useQuery({
    queryKey: apiKeyKeys.supportedProviders(),
    queryFn: getSupportedProviders,
  });
}

export interface CreateApiKeyData {
  provider: string;
  api_key: string;
  key_label: string | undefined;
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
  daily_quota?: number;
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateApiKeyData) => createApiKey(data as any),
    onSuccess: () => {
      toast.success("API key added successfully");
      queryClient.invalidateQueries({ queryKey: apiKeyKeys.lists() });
    },
    onError: (e: any) => {
      toast.error(e?.message || "Failed to add API key");
    },
  });
}

export function useDeleteApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => deleteApiKey(keyId),
    onSuccess: () => {
      toast.success("API key deleted");
      queryClient.invalidateQueries({ queryKey: apiKeyKeys.lists() });
    },
    onError: (e: any) => {
      toast.error(e?.message || "Failed to delete API key");
    },
  });
}

export function useTestApiKey() {
  return useMutation({
    mutationFn: ({ provider, apiKey }: { provider: string; apiKey: string }) =>
      testApiKey(provider, apiKey),
  });
}
