<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — API Key Quick-Start Tutorial
description: Add your own LLM provider keys to ScholarForm AI
sidebar_position: 51
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — API Key Quick-Start Tutorial

**Audience:** Users who want to add their own LLM provider API keys  
**Time:** 5 minutes

> **See also:** [API Reference](API.md), [Security](Security.md), [Secret Rotation](SECRET_ROTATION.md)

---

## Table of Contents

- [Why Add Your Own API Key?](#why-add-your-own-api-key)
- [Step 1: Get Your API Key](#step-1-get-your-api-key)
- [Step 2: Add Key to ScholarForm](#step-2-add-key-to-scholarform)
- [Step 3: Verify It Works](#step-3-verify-it-works)
- [Step 4: Monitor Usage](#step-4-monitor-usage)
- [Rate Limits Explained](#rate-limits-explained)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Supported Providers](#supported-providers)

## Why Add Your Own API Key?

| Benefit | Description |
| --------- | ------------- |
| **Faster Processing** | Direct connection to LLM providers, no queue |
| **Higher Limits** | Use your own rate limits instead of shared pool |
| **Cost Control** | Only pay for what you use via your provider account |
| **Model Choice** | Access to latest models as soon as providers release them |

---

## Step 1: Get Your API Key

### OpenAI

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-...`)

### Anthropic

1. Go to https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Copy the key (starts with `sk-ant-...`)

### DeepSeek

1. Go to https://platform.deepseek.com/api-keys
2. Create a new API key
3. Copy the key

### Groq

1. Go to https://console.groq.com/keys
2. Create API key
3. Copy the key (starts with `gsk_...`)

---

## Step 2: Add Key to ScholarForm

1. Log in to ScholarForm
2. Navigate to **Settings → API Keys** (or `/api-keys`)
3. Click **"+ Add Key"**
4. Select your **Provider** from the dropdown
5. (Optional) Add a **Label** (e.g., "My OpenAI Key")
6. Paste your **API Key**
7. Click **"Test Connection"** to verify
8. Click **"Save Key"**

---

## Step 3: Verify It Works

After saving, you'll see your key in the list with:

- ✅ **Active** status indicator
- 🔑 Masked key preview (`sk-...abcd`)
- 📊 Request counter (starts at 0)
- ⚡ Rate limits (per minute, per hour, per day)

---

## Step 4: Monitor Usage

Navigate to **API Keys → Usage** (or `/api-keys/usage`) to see:

- **Total requests** in the last 24 hours / 7 days / 30 days
- **Token consumption** per provider
- **Average response times**
- **Rate limit status** with visual progress bars

---

## Rate Limits Explained

When you add a key, you can set custom rate limits:

| Limit | Default | Description |
| ------- | --------- | ------------- |
| Per Minute | 60 | Max requests per 60-second window |
| Per Hour | 1,000 | Max requests per 60-minute window |
| Per Day | 10,000 | Max requests per 24-hour period |

If you exceed a limit, you'll get a **429 Too Many Requests** response with:

- `Retry-After` header (seconds to wait)
- `X-RateLimit-Remaining` (how many requests left)
- `X-RateLimit-Reset` (when the limit resets)

---

## Troubleshooting

### "Test Connection" Fails

- Verify your API key is correct (no extra spaces)
- Check your provider account has available credits
- Ensure the provider's API is not experiencing an outage

### 429 Rate Limit Errors

- Check your usage dashboard for current consumption
- Increase your rate limits in the API key settings
- Wait for the `Retry-After` period before retrying

### Key Not Working in Processing

- Ensure the key is marked as **Active**
- Check that the provider matches the model being used
- Verify your provider account hasn't been suspended

---

## Security Notes

🔒 **Your keys are encrypted** using Fernet symmetric encryption before storage  
🔒 **We never expose full keys** — only masked previews are shown  
🔒 **You can delete keys anytime** — deletion is immediate and irreversible  
🔒 **Keys are scoped to your account** — other users cannot access them

---

## Supported Providers

| Provider | Models | Rate Limit (default) |
| ---------- | -------- | --------------------- |
| OpenAI | GPT-4, GPT-4o, o1, o3 | 60/min, 1000/hr |
| Anthropic | Claude 3.5, Claude 4 | 50/min, 800/hr |
| DeepSeek | DeepSeek-V3, R1 | 60/min, 1000/hr |
| Groq | Llama 3, Mixtral | 30/min, 600/hr |
| Google AI | Gemini 1.5, 2.0 | 60/min, 1000/hr |
| Cohere | Command R+ | 40/min, 800/hr |
| Mistral | Mistral Large, Codestral | 60/min, 1000/hr |
