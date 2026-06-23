// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

const Configuration = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "build",
        "ci",
        "chore",
        "revert",
        "security",
      ],
    ],
    "scope-enum": [
      2,
      "always",
      [
        "backend",
        "frontend",
        "pipeline",
        "auth",
        "api",
        "templates",
        "docs",
        "ci",
        "deps",
        "release",
        "docker",
      ],
    ],
    "scope-empty": [2, "never"],
    "subject-case": [2, "always", "lower-case"],
    "subject-full-stop": [2, "never", "."],
    "header-max-length": [2, "always", 100],
    "body-max-line-length": [2, "always", 100],
  },
  helpUrl:
    "https://github.com/scholarform/scholarform/blob/main/CONTRIBUTING.md#commit-message-guidelines",
};

export default Configuration;
