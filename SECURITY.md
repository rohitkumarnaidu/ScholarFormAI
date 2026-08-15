# Security Policy

ScholarForm AI takes the security of our platform and user data extremely seriously. We employ enterprise-grade security practices and adhere to SLSA Level 3 standards for our build and release processes.

## Supported Versions

Our security updates follow semantic versioning. We actively provide security patches for the latest major release and the immediate prior major release.

| Version | Supported          | Security Patch SLA |
| ------- | ------------------ | ------------------ |
| 1.x     | :white_check_mark: | Active             |
| < 1.0   | :x:                | End of Life        |

*(Note: See [SUPPORTED_VERSIONS.md](SUPPORTED_VERSIONS.md) for full lifecycle details.)*

## Reporting a Vulnerability

We deeply appreciate the efforts of security researchers and our community in keeping ScholarForm AI safe. 

If you discover a security vulnerability, **please do not report it through public GitHub issues or discussions.**

Instead, please report it via one of the following methods:
1. **Email:** Send a detailed report to [security@scholarform.ai](mailto:security@scholarform.ai).
2. **GitHub Security Advisory:** Use the "Report a vulnerability" feature in the GitHub Security tab.

### Expected Response Timeline

*   **Acknowledgment:** Within 24 hours of submission.
*   **Initial Triage & Assessment:** Within 72 hours.
*   **Resolution & Patch Delivery:** Dependent on severity (Critical: < 48 hours, High: < 7 days).

## SLSA Level 3 & Supply Chain Security

ScholarForm AI is built with Supply-chain Levels for Software Artifacts (SLSA) Level 3 compliance in mind:
*   All builds are verifiable and hermetic.
*   Source code history is immutable and protected (see [BRANCH_PROTECTION.md](docs/BRANCH_PROTECTION.md)).
*   All dependencies are scanned automatically via automated workflows.

## Safe Harbor

We will not initiate legal action against individuals who discover and report vulnerabilities in good faith, provided they adhere to responsible disclosure guidelines and do not exploit the vulnerability beyond what is necessary to confirm its existence.
