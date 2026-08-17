import React from 'react';

export default function AdminIssuesPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Issues Dashboard</h1>
        <p className="text-slate-600 dark:text-slate-400">View and triage user reports, bugs, and crashes.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-medium text-slate-500 uppercase">Open Issues</h3>
          <p className="text-3xl font-bold mt-2">--</p>
        </div>
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-medium text-slate-500 uppercase">Avg SLA Response</h3>
          <p className="text-3xl font-bold mt-2">--</p>
        </div>
        <div className="bg-white dark:bg-slate-800 p-6 rounded-lg shadow border border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-medium text-slate-500 uppercase">AI Automated Fixes</h3>
          <p className="text-3xl font-bold mt-2">--</p>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg shadow border border-slate-200 dark:border-slate-700">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
          <h2 className="text-lg font-semibold">Recent Reports</h2>
          <div className="flex gap-2">
            <select className="border-slate-300 rounded text-sm p-1">
              <option>All Categories</option>
              <option>Bugs</option>
              <option>Crashes</option>
            </select>
          </div>
        </div>
        <div className="p-8 text-center text-slate-500">
          <p>The issue list component will be rendered here, fetching from /api/v1/issues.</p>
        </div>
      </div>
    </div>
  );
}
