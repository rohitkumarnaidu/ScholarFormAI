import js from "@eslint/js";
import reactPlugin from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default [
  js.configs.recommended,
  reactPlugin.configs.flat.recommended,
  {
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/static-components": "off",
      "react-hooks/refs": "off",
      "react-hooks/purity": "off",
      "react-hooks/immutability": "off",
      "react-hooks/preserve-manual-memoization": "off",
      "react-hooks/incompatible-library": "off",
    },
  },
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      ".next/**",
      "playwright-report/**",
      "test-results/**",
      "src/_vite_pages/**",
      "_legacy_vite_archive/**",
      "coverage/**",
      ".eslintrc.cjs",
    ],
  },
  {
    files: ["**/*.{js,jsx,mjs,cjs}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
        process: "readonly",
      },
    },
    settings: {
      react: { version: "detect" },
    },
    rules: {
      "react/prop-types": "off",
      "react/react-in-jsx-scope": "off",
      "no-unused-vars": ["warn", { caughtErrors: "none" }],
    },
  },
  {
    files: ["src/test/**/*.{js,jsx,ts,tsx}", "src/**/*.{test,spec}.{js,jsx,ts,tsx}"],
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.jest,
        vi: "readonly",
      },
    },
  },
  {
    files: [
      "playwright.config.js",
      "vitest.config.js",
      "next.config.mjs",
      "tailwind.config.js",
      "postcss.config.js",
      "middleware.js",
      "migrate_*.js",
      "lighthouserc.js",
      "eslint.config.js",
      "generate-tests.cjs",
    ],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
  {
    files: ["e2e/**/*.js"],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^page$" }],
    },
  },
];
