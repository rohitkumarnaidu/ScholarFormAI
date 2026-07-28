#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

/**
 * ScholarForm API JavaScript Client Example (Node.js)
 *
 * Usage:
 *     node scholarform_client.js paper.docx --template ieee
 *     node scholarform_client.js paper.docx --template springer --api-key YOUR_KEY
 */

const fs = require('fs');
const path = require('path');

class ScholarFormClient {
  constructor(apiUrl = 'http://localhost:8000', apiKey = null) {
    this.apiUrl = apiUrl.replace(/\/+$/, '');
    this.apiKey = apiKey;
  }

  _getHeaders(extraHeaders = {}) {
    const headers = { Accept: 'application/json', ...extraHeaders };
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  async health() {
    const res = await fetch(`${this.apiUrl}/api/v1/health`, {
      method: 'GET',
      headers: this._getHeaders(),
    });
    const body = await res.json();
    if (!res.ok) {
      throw new Error(body.error?.message || `Health check failed with HTTP ${res.status}`);
    }
    return body.data || body;
  }

  async listTemplates() {
    const res = await fetch(`${this.apiUrl}/api/v1/templates`, {
      method: 'GET',
      headers: this._getHeaders(),
    });
    const body = await res.json();
    if (!res.ok) {
      throw new Error(body.error?.message || `List templates failed with HTTP ${res.status}`);
    }
    return body.data || body;
  }

  async upload(filePath, template = 'ieee') {
    const absolutePath = path.resolve(filePath);
    if (!fs.existsSync(absolutePath)) {
      throw new Error(`File not found: ${absolutePath}`);
    }

    const fileBuffer = fs.readFileSync(absolutePath);
    const fileName = path.basename(absolutePath);

    // Node 18+ native Blob and FormData
    const blob = new Blob([fileBuffer], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    const formData = new FormData();
    formData.append('file', blob, fileName);
    formData.append('template', template);

    const headers = {};
    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const res = await fetch(`${this.apiUrl}/api/v1/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    const body = await res.json();
    if (!res.ok) {
      throw new Error(body.error?.message || `Upload failed with HTTP ${res.status}`);
    }
    // Handle api_envelope response
    return body.data || body;
  }

  async status(jobId) {
    const res = await fetch(`${this.apiUrl}/api/v1/documents/${jobId}/status`, {
      method: 'GET',
      headers: this._getHeaders(),
    });
    const body = await res.json();
    if (!res.ok) {
      throw new Error(body.error?.message || `Status query failed with HTTP ${res.status}`);
    }
    // Handle api_envelope response
    return body.data || body;
  }

  async download(jobId, outputPath, fmt = 'docx') {
    const url = `${this.apiUrl}/api/v1/documents/${jobId}/download?format=${encodeURIComponent(fmt)}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: this._getHeaders(),
    });

    if (!res.ok) {
      const text = await res.text();
      let errorMsg = `Download failed with HTTP ${res.status}`;
      try {
        const body = JSON.parse(text);
        errorMsg = body.error?.message || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    const arrayBuffer = await res.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    fs.writeFileSync(outputPath, buffer);
    return outputPath;
  }

  async waitForCompletion(jobId, pollIntervalMs = 1000) {
    while (true) {
      const data = await this.status(jobId);
      const status = data.status || 'unknown';
      const progress = data.progress || 0;
      process.stdout.write(`  [${String(progress).padStart(3, ' ')}%] ${status}\r`);

      if (status === 'completed' || status === 'COMPLETED') {
        console.log(`\n  Done! Processing complete.`);
        return data;
      }
      if (status === 'failed' || status === 'FAILED') {
        console.log('');
        throw new Error(data.error || 'Formatting job failed');
      }

      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log('ScholarForm API Node.js Client Example');
    console.log('Usage: node scholarform_client.js <file> [--template <name>] [--output <path>] [--api-url <url>] [--api-key <key>]');
    process.exit(args.length === 0 ? 1 : 0);
  }

  let file = null;
  let template = 'ieee';
  let output = null;
  let apiUrl = 'http://localhost:8000';
  let apiKey = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--template' && i + 1 < args.length) {
      template = args[++i];
    } else if (args[i] === '--output' && i + 1 < args.length) {
      output = args[++i];
    } else if (args[i] === '--api-url' && i + 1 < args.length) {
      apiUrl = args[++i];
    } else if (args[i] === '--api-key' && i + 1 < args.length) {
      apiKey = args[++i];
    } else if (!args[i].startsWith('-') && !file) {
      file = args[i];
    }
  }

  if (!file) {
    console.error('Error: Please specify input file.');
    process.exit(1);
  }

  const parsedPath = path.parse(file);
  const outPath = output || path.join(parsedPath.dir, `formatted_${parsedPath.name}.docx`);

  const client = new ScholarFormClient(apiUrl, apiKey);

  try {
    console.log(`Checking API health at ${apiUrl}...`);
    const health = await client.health();
    console.log(`  OK: API status is ${health.status || 'healthy'}`);

    console.log(`Uploading ${file} with template '${template}'...`);
    const uploadRes = await client.upload(file, template);
    const jobId = uploadRes.job_id || uploadRes.jobId;
    if (!jobId) {
      throw new Error('Upload response did not contain job_id');
    }
    console.log(`  Job ID: ${jobId}`);

    console.log('Waiting for formatting job completion...');
    await client.waitForCompletion(jobId);

    console.log(`Downloading formatted document to ${outPath}...`);
    await client.download(jobId, outPath);

    const stats = fs.statSync(outPath);
    console.log(`  Saved: ${outPath} (${stats.size.toLocaleString()} bytes)`);
    console.log('Done.');
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { ScholarFormClient };
