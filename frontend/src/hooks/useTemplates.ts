import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  getBuiltinTemplates,
  searchCSLStyles,
  fetchCSLStyle,
  getCustomTemplates,
  saveCustomTemplate,
} from "@/src/services/api.templates";

export const templateKeys = {
  all: ["templates"] as const,
  builtin: () => [...templateKeys.all, "builtin"] as const,
  custom: () => [...templateKeys.all, "custom"] as const,
};

export function useBuiltinTemplates() {
  return useQuery({
    queryKey: templateKeys.builtin(),
    queryFn: getBuiltinTemplates,
  });
}

export function useCustomTemplates() {
  return useQuery({
    queryKey: templateKeys.custom(),
    queryFn: getCustomTemplates,
  });
}

export function useSearchCSLStyles() {
  return useMutation({
    mutationFn: (query: string) => searchCSLStyles(query),
  });
}

export function useFetchCSLStyle() {
  return useMutation({
    mutationFn: (slug: string) => fetchCSLStyle(slug),
  });
}

export function useSaveCustomTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => saveCustomTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.custom() });
      toast.success("Template saved successfully");
    },
    onError: () => {
      toast.error("Failed to save template");
    },
  });
}
