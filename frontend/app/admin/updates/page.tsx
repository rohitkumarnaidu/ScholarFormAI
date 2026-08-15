"use client";

import { useEffect, useState } from "react";
import { Shield, Server, ArrowLeft, RefreshCw, Layers } from "lucide-react";
import Link from "next/link";
import { getAdminApplications, getAdminReleases, type AdminApplication, type AdminRelease } from "@/lib/admin-api";

export default function AdminUpdatesDashboard() {
  const [apps, setApps] = useState<AdminApplication[]>([]);
  const [releases, setReleases] = useState<AdminRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [appsData, releasesData] = await Promise.all([
        getAdminApplications(),
        getAdminReleases()
      ]);
      setApps(appsData);
      setReleases(releasesData);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <div>
            <Link href="/" className="inline-flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:text-slate-300 mb-4">
              <ArrowLeft className="h-4 w-4" />
              Back to App
            </Link>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Shield className="h-6 w-6 text-accent-500" />
              Enterprise Update Center
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Manage global software releases, policies, and rollout telemetry</p>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-800">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <div className="rounded-lg bg-blue-100 p-2"><Layers className="h-5 w-5 text-blue-600" /></div>
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">Applications</h3>
            </div>
            <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{apps.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <div className="rounded-lg bg-green-100 p-2"><Server className="h-5 w-5 text-green-600" /></div>
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">Total Releases</h3>
            </div>
            <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">{releases.length}</p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Global Release Registry</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600 dark:text-slate-400">
              <thead className="bg-slate-50 dark:bg-slate-900 text-xs uppercase text-slate-500 dark:text-slate-400">
                <tr>
                  <th className="px-6 py-3 font-medium">Version</th>
                  <th className="px-6 py-3 font-medium">Application</th>
                  <th className="px-6 py-3 font-medium">Tags</th>
                  <th className="px-6 py-3 font-medium">Published</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-slate-500">Loading releases...</td>
                  </tr>
                ) : releases.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-slate-500">No releases registered in the system.</td>
                  </tr>
                ) : releases.map((release) => (
                  <tr key={release.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="px-6 py-4 font-medium text-slate-900 dark:text-slate-100">
                      v{release.version}
                    </td>
                    <td className="px-6 py-4">
                      {apps.find(a => a.id === release.app_id)?.name || "Unknown App"}
                    </td>
                    <td className="px-6 py-4 space-x-2">
                      {release.is_mandatory && (
                        <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                          Mandatory
                        </span>
                      )}
                      {release.is_security_update && (
                        <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">
                          Security
                        </span>
                      )}
                      {!release.is_mandatory && !release.is_security_update && (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-800">
                          Standard
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {new Date(release.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
