'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="rounded-full bg-red-50 p-6 dark:bg-red-900/30">
        <div className="text-4xl">⚠</div>
      </div>
      <h1 className="mt-6 text-2xl font-bold text-slate-900 dark:text-white">
        Something went wrong
      </h1>
      <p className="mt-2 text-slate-600 dark:text-slate-400">
        {error.message || 'An unexpected error occurred'}
      </p>
      <button
        onClick={reset}
        className="mt-6 rounded-lg bg-primary-500 px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary-600"
      >
        Try again
      </button>
    </div>
  );
}
