// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Check, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function UpgradeModal({ isOpen, onClose, title = "Upgrade to Pro" }) {
  const router = useRouter();

  if (!isOpen) return null;

  const handleUpgrade = () => {
    onClose();
    router.push("/settings?tab=billing");
  };

  const features = [
    "Unlimited document uploads",
    "AI Agent chat assistance",
    "Multi-document synthesis",
    "Batch upload processing",
    "Priority fast processing",
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="upgrade-modal-title"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-2xl dark:bg-gray-900 border border-gray-100 dark:border-gray-800"
          >
            <button
              onClick={onClose}
              aria-label="Close upgrade modal"
              className="absolute right-4 top-4 rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="mb-6 flex flex-col items-center text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg">
                <Sparkles className="h-8 w-8" />
              </div>
              <h2 className="mb-2 text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400">
                {title}
              </h2>
              <p className="text-gray-500 dark:text-gray-400">
                Unlock the full power of ScholarForm AI to accelerate your academic workflow.
              </p>
            </div>

            <div className="mb-8 space-y-3">
              {features.map((feature, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400">
                    <Check className="h-4 w-4" />
                  </div>
                  <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3">
              <button
                onClick={handleUpgrade}
                className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 py-3 font-semibold text-white shadow-md hover:shadow-lg hover:from-indigo-700 hover:to-purple-700 transition-all active:scale-95"
              >
                Upgrade Now
              </button>
              <button
                onClick={onClose}
                className="w-full rounded-xl py-3 font-medium text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 transition-colors active:scale-95"
              >
                Maybe Later
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
