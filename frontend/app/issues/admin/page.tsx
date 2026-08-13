"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft, Bug, CheckCircle, AlertTriangle, BarChart3,
  PieChart, Clock, Plus, X, Loader2, Save, Trash2,
  Flag, Tag, Settings,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import {
  getIssueStats, checkSLA, listLabels, createLabel, deleteLabel,
  listMilestones, createMilestone, getIssueSettings, updateIssueSettings,
  type IssueStats, type SLABreach,
} from "@/lib/issue-api";

type Tab = "overview" | "labels" | "milestones" | "settings";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<IssueStats | null>(null);
  const [slaBreaches, setSlaBreaches] = useState<SLABreach[]>([]);
  const [labels, setLabels] = useState<Record<string, { name: string; color: string; description: string }>>({});
  const [milestones, setMilestones] = useState<Record<string, unknown>[]>([]);
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);

  // Label form
  const [newLabelName, setNewLabelName] = useState("");
  const [newLabelColor, setNewLabelColor] = useState("#6366f1");
  const [newLabelDesc, setNewLabelDesc] = useState("");
  const [creatingLabel, setCreatingLabel] = useState(false);

  // Milestone form
  const [newMsTitle, setNewMsTitle] = useState("");
  const [newMsDesc, setNewMsDesc] = useState("");
  const [newMsDue, setNewMsDue] = useState("");
  const [creatingMs, setCreatingMs] = useState(false);

  // Settings
  const [savingSettings, setSavingSettings] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [s, sla, l, m, set] = await Promise.all([
          getIssueStats().catch(() => null),
          checkSLA().catch(() => []),
          listLabels().catch(() => ({})),
          listMilestones().catch(() => []),
          getIssueSettings().catch(() => ({})),
        ]);
        if (s) setStats(s);
        setSlaBreaches(sla);
        setLabels(l);
        setMilestones(m);
        setSettings(set);
      } catch {
        toast.error("Failed to load admin data");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleCreateLabel = async () => {
    if (!newLabelName.trim()) return;
    setCreatingLabel(true);
    try {
      await createLabel(newLabelName.trim(), newLabelColor, newLabelDesc || undefined);
      const updated = await listLabels();
      setLabels(updated);
      setNewLabelName("");
      setNewLabelDesc("");
      toast.success(`Label "${newLabelName}" created`);
    } catch {
      toast.error("Failed to create label");
    } finally {
      setCreatingLabel(false);
    }
  };

  const handleDeleteLabel = async (key: string) => {
    try {
      await deleteLabel(key);
      const updated = await listLabels();
      setLabels(updated);
      toast.success("Label deleted");
    } catch {
      toast.error("Failed to delete label");
    }
  };

  const handleCreateMilestone = async () => {
    if (!newMsTitle.trim()) return;
    setCreatingMs(true);
    try {
      await createMilestone(newMsTitle.trim(), newMsDesc || undefined, newMsDue || undefined);
      const updated = await listMilestones();
      setMilestones(updated);
      setNewMsTitle("");
      setNewMsDesc("");
      setNewMsDue("");
      toast.success(`Milestone "${newMsTitle}" created`);
    } catch {
      toast.error("Failed to create milestone");
    } finally {
      setCreatingMs(false);
    }
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      const updated = await updateIssueSettings(settings);
      setSettings(updated);
      toast.success("Settings saved");
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSavingSettings(false);
    }
  };

  const tabs: { id: Tab; label: string; icon: typeof BarChart3 }[] = [
    { id: "overview", label: "Overview", icon: BarChart3 },
    { id: "labels", label: "Labels", icon: Tag },
    { id: "milestones", label: "Milestones", icon: Flag },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400 dark:text-slate-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <Link href="/issues" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:text-slate-300">
            <ArrowLeft className="h-4 w-4" />
            Back to Issues
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Issue Admin</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Manage issue tracking, labels, milestones, and settings</p>
        </div>

        {/* Tabs */}
        <div className="mb-6 flex border-b border-slate-200 dark:border-slate-700">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-accent-500 text-accent-500"
                  : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:text-slate-300 hover:border-slate-200 dark:border-slate-700"
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Stats cards */}
            {stats && (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-accent-100 dark:bg-accent-500/20 p-2"><Bug className="h-4 w-4 text-accent-500" /></div>
                    <div>
                      <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{stats.total_issues}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">Total Issues</p>
                    </div>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-green-100 p-2"><CheckCircle className="h-4 w-4 text-green-600" /></div>
                    <div>
                      <p className="text-2xl font-bold text-green-600">{stats.open_issues}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">Open</p>
                    </div>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-emerald-100 p-2"><CheckCircle className="h-4 w-4 text-emerald-600" /></div>
                    <div>
                      <p className="text-2xl font-bold text-emerald-600">{stats.resolved_issues}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">Resolved</p>
                    </div>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-red-100 p-2"><AlertTriangle className="h-4 w-4 text-red-600" /></div>
                    <div>
                      <p className="text-2xl font-bold text-red-600">{stats.critical_issues}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">Critical</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {stats && (
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* By Category chart */}
                <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
                  <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                    <BarChart3 className="h-4 w-4" />
                    Issues by Category
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(stats.by_category || {}).map(([key, count]) => {
                      const maxVal = Math.max(...Object.values(stats.by_category || {}), 1);
                      const pct = (count / maxVal) * 100;
                      return (
                        <div key={key}>
                          <div className="flex items-center justify-between text-xs text-slate-600 dark:text-slate-400 mb-0.5">
                            <span className="capitalize">{key.replace("-", " ")}</span>
                            <span>{count}</span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-800">
                            <div
                              className="h-2 rounded-full bg-blue-500 transition-all"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* By Status chart */}
                <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
                  <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                    <PieChart className="h-4 w-4" />
                    Issues by Status
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(stats.by_status || {}).map(([key, count]) => {
                      const total = Object.values(stats.by_status || {}).reduce((a, b) => a + b, 0) || 1;
                      const pct = Math.round((count / total) * 100);
                      return (
                        <div key={key} className="flex items-center gap-3">
                          <span className="w-24 text-xs capitalize text-slate-600 dark:text-slate-400">{key.replace("-", " ")}</span>
                          <div className="flex-1 h-2 rounded-full bg-slate-100 dark:bg-slate-800">
                            <div
                              className="h-2 rounded-full bg-indigo-500 transition-all"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="w-10 text-right text-xs text-slate-500 dark:text-slate-400">{count} ({pct}%)</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* SLA Breaches */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
              <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                <Clock className="h-4 w-4" />
                SLA Breaches
              </h3>
              {slaBreaches.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">No SLA breaches detected.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-xs text-slate-500 dark:text-slate-400">
                        <th className="pb-2 font-medium">Tracking #</th>
                        <th className="pb-2 font-medium">Severity</th>
                        <th className="pb-2 font-medium">Elapsed</th>
                        <th className="pb-2 font-medium">SLA</th>
                        <th className="pb-2 font-medium">Breach</th>
                      </tr>
                    </thead>
                    <tbody>
                      {slaBreaches.map((breach) => (
                        <tr key={breach.issue_id} className="border-b border-slate-100 dark:border-slate-800">
                          <td className="py-2 font-mono text-xs">{breach.tracking_number}</td>
                          <td className="py-2">
                            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                              breach.severity === "critical" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                            }`}>
                              {breach.severity}
                            </span>
                          </td>
                          <td className="py-2 text-slate-600 dark:text-slate-400">{breach.elapsed_hours.toFixed(1)}h</td>
                          <td className="py-2 text-slate-600 dark:text-slate-400">{breach.sla_hours}h</td>
                          <td className="py-2 text-red-600 font-medium">{breach.breach_hours.toFixed(1)}h over</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Labels */}
        {activeTab === "labels" && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Labels</h2>

            {/* Create */}
            <div className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 p-4">
              <div className="flex-1 min-w-[150px]">
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Name</label>
                <input
                  value={newLabelName}
                  onChange={(e) => setNewLabelName(e.target.value)}
                  placeholder="Label name"
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Color</label>
                <input
                  type="color"
                  value={newLabelColor}
                  onChange={(e) => setNewLabelColor(e.target.value)}
                  className="h-9 w-12 rounded-lg border border-slate-200 dark:border-slate-700 cursor-pointer"
                />
              </div>
              <div className="flex-1 min-w-[200px]">
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Description</label>
                <input
                  value={newLabelDesc}
                  onChange={(e) => setNewLabelDesc(e.target.value)}
                  placeholder="Optional description"
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
              <button
                onClick={handleCreateLabel}
                disabled={creatingLabel || !newLabelName.trim()}
                className="inline-flex items-center gap-1 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
              >
                {creatingLabel ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Add
              </button>
            </div>

            {/* List */}
            <div className="space-y-2">
              {Object.keys(labels).length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">No labels yet.</p>
              ) : (
                Object.entries(labels).map(([key, label]) => (
                  <div key={key} className="flex items-center justify-between rounded-lg border border-slate-100 dark:border-slate-800 bg-white p-3">
                    <div className="flex items-center gap-3">
                      <span
                        className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
                        style={{ backgroundColor: label.color }}
                      >
                        {label.name}
                      </span>
                      <span className="text-xs text-slate-500 dark:text-slate-400">{label.description}</span>
                    </div>
                    <button
                      onClick={() => handleDeleteLabel(key)}
                      className="rounded-lg p-1.5 text-slate-400 dark:text-slate-500 hover:bg-red-50 hover:text-red-600 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Milestones */}
        {activeTab === "milestones" && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Milestones</h2>

            {/* Create */}
            <div className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 p-4">
              <div className="flex-1 min-w-[150px]">
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Title</label>
                <input
                  value={newMsTitle}
                  onChange={(e) => setNewMsTitle(e.target.value)}
                  placeholder="Milestone title"
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
              <div className="flex-1 min-w-[150px]">
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Description</label>
                <input
                  value={newMsDesc}
                  onChange={(e) => setNewMsDesc(e.target.value)}
                  placeholder="Optional description"
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Due date</label>
                <input
                  type="date"
                  value={newMsDue}
                  onChange={(e) => setNewMsDue(e.target.value)}
                  className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2 text-sm"
                />
              </div>
              <button
                onClick={handleCreateMilestone}
                disabled={creatingMs || !newMsTitle.trim()}
                className="inline-flex items-center gap-1 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
              >
                {creatingMs ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Add
              </button>
            </div>

            {/* List */}
            <div className="space-y-2">
              {milestones.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">No milestones yet.</p>
              ) : (
                milestones.map((ms, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg border border-slate-100 dark:border-slate-800 bg-white p-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{String(ms.title || "")}</p>
                      {ms.description ? <p className="text-xs text-slate-500 dark:text-slate-400">{String(ms.description)}</p> : null}
                    </div>
                    <div className="flex items-center gap-3">
                      {ms.due_date ? (
                        <span className="text-xs text-slate-400 dark:text-slate-500">Due: {new Date(String(ms.due_date)).toLocaleDateString()}</span>
                      ) : null}
                      {ms.status ? (
                        <span className="inline-flex items-center rounded-full bg-accent-100 dark:bg-accent-500/20 px-2 py-0.5 text-[10px] font-medium text-accent-600 dark:text-accent-400">
                          {String(ms.status)}
                        </span>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Settings */}
        {activeTab === "settings" && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-5">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Issue Settings</h2>

            <div className="space-y-4">
              {Object.entries(settings).length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">No configurable settings available.</p>
              ) : (
                Object.entries(settings).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between py-2">
                    <div>
                      <p className="text-sm font-medium text-slate-900 dark:text-slate-100 capitalize">
                        {key.replace(/_/g, " ")}
                      </p>
                    </div>
                    {typeof value === "boolean" ? (
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={value as boolean}
                          onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-gray-200 rounded-full peer peer-checked:bg-accent-500 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all" />
                      </label>
                    ) : typeof value === "number" ? (
                      <input
                        type="number"
                        value={value as number}
                        onChange={(e) => setSettings({ ...settings, [key]: parseInt(e.target.value) || 0 })}
                        className="w-24 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-right"
                      />
                    ) : (
                      <input
                        type="text"
                        value={String(value || "")}
                        onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
                        className="w-48 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm"
                      />
                    )}
                  </div>
                ))
              )}

              <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                <button
                  onClick={handleSaveSettings}
                  disabled={savingSettings}
                  className="inline-flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50 transition-colors"
                >
                  {savingSettings ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {savingSettings ? "Saving..." : "Save Settings"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
