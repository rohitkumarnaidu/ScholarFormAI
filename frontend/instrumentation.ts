// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    // We only instrument in nodejs environment
    const { NodeSDK } = await import('@opentelemetry/sdk-node');
    const { OTLPTraceExporter } = await import('@opentelemetry/exporter-trace-otlp-http');
    const { Resource } = await import('@opentelemetry/resources');
    const { SemanticResourceAttributes } = await import('@opentelemetry/semantic-conventions');

    // Only start if explicitly enabled
    if (process.env.ENABLE_TRACING !== 'true') {
      console.log('OpenTelemetry tracing is disabled (ENABLE_TRACING != true)');
      return;
    }

    const endpoint = process.env.OTLP_ENDPOINT || 'http://localhost:4318/v1/traces';

    const sdk = new NodeSDK({
      resource: new Resource({
        [SemanticResourceAttributes.SERVICE_NAME]: 'scholarform-frontend',
      }),
      traceExporter: new OTLPTraceExporter({
        url: endpoint,
      }),
    });

    sdk.start();
    console.log(`OpenTelemetry tracing initialized for Next.js (endpoint: ${endpoint})`);
  }
}
