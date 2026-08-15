# Privacy Policy & Data Handling

**ScholarForm AI** takes data privacy and intellectual property protection seriously. Because our platform processes unpublished, highly sensitive academic research, we have designed our architecture to minimize data retention and ensure compliance with global privacy regulations (e.g., GDPR, CCPA).

## 1. Data Collection and Usage

When utilizing the ScholarForm AI platform:

- **Manuscript Data:** Uploaded documents (DOCX, PDF, LaTeX) are processed in memory and written to ephemeral storage. By default, manuscripts and generated outputs are **automatically purged** from our servers within 24 hours of processing.
- **AI Processing:** Document content is securely transmitted to configured LLM providers (e.g., Groq, OpenAI). We strictly configure these API integrations with "zero-data retention" policies where available, ensuring your research is **never used to train third-party models**.
- **Telemetry and Analytics:** We collect basic, anonymized telemetry (e.g., error rates, processing time, template usage) to improve the open-source project. This telemetry contains no PII or manuscript content.

## 2. Self-Hosted Deployments

As an open-source project, ScholarForm AI is designed to be self-hosted. When deployed in your own environment (via Docker/Kubernetes):

- **You retain 100% control** over your data.
- The platform does not phone home or transmit manuscript data back to the core maintainers.
- Administrators can fully disable anonymous telemetry via the `DISABLE_TELEMETRY=true` environment variable.

## 3. Compliance & Security

- **Data in Transit:** All traffic must be secured via TLS (HTTPS/WSS).
- **Data at Rest:** If persistence is enabled (e.g., for collaborative editing workflows in future versions), database records are encrypted at rest.
- **Access Control:** Role-Based Access Control (RBAC) ensures only authorized users can access specific formatting pipelines.

## 4. User Rights

Users of hosted instances of ScholarForm AI have the right to request immediate deletion of their accounts and any associated cached data. Please contact the instance administrator or refer to our [Support](SUPPORT.md) channels.

*Note: This privacy document applies to the core open-source software. Third-party hosted versions or forks of this software may have different privacy policies.*
