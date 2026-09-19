import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  listIssues, getIssue, submitIssue, addComment, getComments, getIssueStats,
  checkSLA, listLabels, createLabel, deleteLabel, listMilestones, createMilestone,
  getIssueSettings, updateIssueSettings,
  type IssueReportRequest
} from "@/lib/issue-api";

export const issueKeys = {
  all: ["issues"] as const,
  lists: () => [...issueKeys.all, "list"] as const,
  list: (params: Record<string, string>) => [...issueKeys.lists(), params] as const,
  details: () => [...issueKeys.all, "detail"] as const,
  detail: (id: string) => [...issueKeys.details(), id] as const,
  comments: (id: string) => [...issueKeys.all, "comments", id] as const,
  stats: () => [...issueKeys.all, "stats"] as const,
  sla: () => [...issueKeys.all, "sla"] as const,
  labels: () => [...issueKeys.all, "labels"] as const,
  milestones: () => [...issueKeys.all, "milestones"] as const,
  settings: () => [...issueKeys.all, "settings"] as const,
};

export type { IssueReportRequest };

export function useIssues(params: Record<string, string>) {
  return useQuery({
    queryKey: issueKeys.list(params),
    queryFn: () => listIssues(params),
  });
}

export function useIssueDetail(id: string | null) {
  return useQuery({
    queryKey: issueKeys.detail(id!),
    queryFn: () => getIssue(id!),
    enabled: Boolean(id),
  });
}

export function useIssueComments(id: string | null) {
  return useQuery({
    queryKey: issueKeys.comments(id!),
    queryFn: () => getComments(id!),
    enabled: Boolean(id),
  });
}

export function useIssueStats() {
  return useQuery({
    queryKey: issueKeys.stats(),
    queryFn: getIssueStats,
  });
}

export function useSLABreaches() {
  return useQuery({
    queryKey: issueKeys.sla(),
    queryFn: checkSLA,
  });
}

export function useLabels() {
  return useQuery({
    queryKey: issueKeys.labels(),
    queryFn: listLabels,
  });
}

export function useMilestones() {
  return useQuery({
    queryKey: issueKeys.milestones(),
    queryFn: listMilestones,
  });
}

export function useIssueSettings() {
  return useQuery({
    queryKey: issueKeys.settings(),
    queryFn: getIssueSettings,
  });
}

export function useSubmitIssue() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IssueReportRequest) => submitIssue(data),
    onSuccess: () => {
      toast.success("Issue reported successfully");
      queryClient.invalidateQueries({ queryKey: issueKeys.lists() });
      queryClient.invalidateQueries({ queryKey: issueKeys.stats() });
    },
    onError: () => {
      toast.error("Failed to submit issue");
    }
  });
}

export function useAddComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body, author }: { id: string; body: string; author: string }) => addComment(id, body, author),
    onSuccess: (_, variables) => {
      toast.success("Comment added");
      queryClient.invalidateQueries({ queryKey: issueKeys.comments(variables.id) });
    },
    onError: () => {
      toast.error("Failed to add comment");
    }
  });
}

export function useCreateLabel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, color, description }: { name: string; color: string; description?: string }) => createLabel(name, color, description),
    onSuccess: () => {
      toast.success("Label created");
      queryClient.invalidateQueries({ queryKey: issueKeys.labels() });
    },
    onError: () => {
      toast.error("Failed to create label");
    }
  });
}

export function useDeleteLabel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => deleteLabel(key),
    onSuccess: () => {
      toast.success("Label deleted");
      queryClient.invalidateQueries({ queryKey: issueKeys.labels() });
    },
    onError: () => {
      toast.error("Failed to delete label");
    }
  });
}

export function useCreateMilestone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ title, description, dueDate }: { title: string; description?: string; dueDate?: string }) => createMilestone(title, description, dueDate),
    onSuccess: () => {
      toast.success("Milestone created");
      queryClient.invalidateQueries({ queryKey: issueKeys.milestones() });
    },
    onError: () => {
      toast.error("Failed to create milestone");
    }
  });
}

export function useUpdateIssueSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings: Record<string, unknown>) => updateIssueSettings(settings),
    onSuccess: () => {
      toast.success("Settings updated");
      queryClient.invalidateQueries({ queryKey: issueKeys.settings() });
    },
    onError: () => {
      toast.error("Failed to update settings");
    }
  });
}
