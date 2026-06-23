// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/* eslint-env node */
module.exports = {
  ci: {
    collect: {
      url: [
        'http://localhost:3000/',
        'http://localhost:3000/dashboard',
        'http://localhost:3000/upload',
        'http://localhost:3000/settings',
        'http://localhost:3000/live',
        'http://localhost:3000/agent'
      ],
      startServerCommand: 'npm run start',
    },
    upload: {
      target: 'temporary-public-storage',
    },
    assert: {
      preset: 'lighthouse:no-pwa',
      assertions: {
        'categories:performance': ['error', { minScore: 0.8 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
        'categories:seo': ['error', { minScore: 0.9 }],
      }
    }
  },
};
