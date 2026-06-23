// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

// frontend/src/lib/planTier.js

// TEMPORARY OVERRIDE: Set to true when we want to start charging or locking down features
export const ENABLE_PRO_RESTRICTIONS = false;

/**
 * Determines the plan tier of the current user.
 * @param {Object} user - User object from AuthContext
 * @returns {"guest" | "free" | "pro"}
 */
export const getUserTier = (user) => {
  if (!user) return "guest";
  if (user.plan_tier) return user.plan_tier;
  return "free";
};

/**
 * Defines the required tier for specific features.
 */
const FEATURE_TIERS = {
  batch_upload: "pro",
  generator_agent: "pro",
  generator_multi_doc: "pro",
  unlimited_uploads: "pro",
  template_editor: "free",
  formatter_live: "free",
};

/**
 * Evaluates whether a user can access a specific feature.
 * @param {Object} user - User object
 * @param {string} feature - Feature key
 * @returns {boolean}
 */
export const canAccess = (user, feature) => {
  const tier = getUserTier(user);
  const requiredTier = FEATURE_TIERS[feature];

  // If feature doesn't require pro, guests might be able to access if not locked down
  // But generally, free features need login. We'll handle login blocks elsewhere, 
  // or return false if it's a known logged-in feature.
  
  if (tier === "pro") return true;

  if (requiredTier === "pro") {
    if (tier === "free") {
      // Temporary override for free users
      if (!ENABLE_PRO_RESTRICTIONS) return true;
      return false;
    }
    return false; // Guest cannot access pro
  }

  // If required tier is "free", both free and pro can access
  if (requiredTier === "free") {
    // Guest cannot access free-tier features
    return tier === "free" || tier === "pro";
  }

  // Fallback
  return false;
};

/**
 * Defines quota limits for different tiers.
 */
const QUOTA_LIMITS = {
  guest: 5,
  free: 20,
  pro: Infinity,
};

/**
 * Calculates remaining quota based on current usage.
 * @param {Object} user - User object
 * @param {number} usedCount - Current usage count
 * @returns {Object} { used, limit, remaining }
 */
export const getRemainingQuota = (user, usedCount = 0) => {
  const tier = getUserTier(user);
  const limit = QUOTA_LIMITS[tier];

  // If Pro restrictions are temporarily lifted, give Free users Infinity
  let effectiveLimit = limit;
  if (!ENABLE_PRO_RESTRICTIONS && tier === "free") {
    effectiveLimit = Infinity;
  }

  return {
    used: usedCount,
    limit: effectiveLimit,
    remaining: effectiveLimit === Infinity ? Infinity : Math.max(0, effectiveLimit - usedCount),
  };
};
