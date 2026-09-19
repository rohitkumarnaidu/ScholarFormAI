import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  getBuiltinProviders,
  getCustomProviders,
  createCustomProvider,
  updateCustomProvider,
  deleteCustomProvider,
  discoverModels,
  testProvider,
  syncModels,
} from "@/src/services/api.providers";

export const providerKeys = {
  all: ["providers"] as const,
  builtin: () => [...providerKeys.all, "builtin"] as const,
  custom: () => [...providerKeys.all, "custom"] as const,
};

export function useBuiltinProviders() {
  return useQuery({
    queryKey: providerKeys.builtin(),
    queryFn: getBuiltinProviders,
  });
}

export function useCustomProviders() {
  return useQuery({
    queryKey: providerKeys.custom(),
    queryFn: getCustomProviders,
  });
}

export function useCreateCustomProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Parameters<typeof createCustomProvider>[0]) => createCustomProvider(data),
    onSuccess: (data, variables) => {
      toast.success(`Provider "${variables.name}" added`);
      queryClient.invalidateQueries({ queryKey: providerKeys.custom() });
    },
    onError: (e: any) => {
      toast.error(e?.message || "Failed to add provider");
    },
  });
}

export function useUpdateCustomProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateCustomProvider(id, data),
    onSuccess: () => {
      toast.success("Provider updated");
      queryClient.invalidateQueries({ queryKey: providerKeys.custom() });
    },
    onError: (e: any) => {
      toast.error(e?.message || "Failed to update provider");
    },
  });
}

export function useDeleteCustomProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCustomProvider(id),
    onSuccess: () => {
      toast.success("Provider deleted");
      queryClient.invalidateQueries({ queryKey: providerKeys.custom() });
    },
    onError: (e: any) => {
      toast.error(e?.message || "Failed to delete provider");
    },
  });
}

export function useDiscoverModels() {
  return useMutation({
    mutationFn: ({ providerId, baseUrl }: { providerId: string; baseUrl?: string }) => discoverModels(providerId, baseUrl),
    onSuccess: (data, variables) => {
      if (data?.models?.length > 0) {
        toast.success(`Found ${data.models.length} models for ${variables.providerId}`);
      } else {
        toast.info("No models discovered");
      }
    },
    onError: () => {
      toast.error("Failed to discover models");
    },
  });
}

export function useTestProvider() {
  return useMutation({
    mutationFn: ({ providerId, baseUrl, apiKey }: { providerId: string; baseUrl?: string; apiKey?: string }) => 
        testProvider(providerId, baseUrl, apiKey),
  });
}

export function useSyncModels() {
  return useMutation({
    mutationFn: ({ providerId, models }: { providerId: string; models: string[] }) => syncModels(providerId, models),
    onSuccess: (data, variables) => {
      const num = variables.models.length;
      toast.success(`${num} model${num !== 1 ? 's' : ''} synced — now available in chat`);
    },
    onError: () => {
      toast.error("Failed to sync models");
    },
  });
}
