# Security Policy

## Supported Versions

The following versions of Automated Manuscript Formatter currently receive active security support:

| Version | Supported          | End of Support       |
|---------|--------------------|----------------------|
| 1.x     | ✅ Active support  | TBD                  |
| 0.x     | ❌ End of life     | 2025-01-01           |

## Reporting a Vulnerability

We take the security of AMF seriously. If you believe you have found a security vulnerability, please **do not** open a public issue.

### Private Reporting Process

1. **Email**: Send a detailed report to **security@amf.dev**
2. **PGP Encryption**: Encrypt sensitive reports using our PGP key:

```
-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBGPw....[full PGP key block here].....
-----END PGP PUBLIC KEY BLOCK-----
```

3. **Alternative**: Submit via our private vulnerability reporting form at **https://amf.dev/security/report**

### What to Include

- **Type of issue** (e.g., XSS, SQL injection, remote code execution, privilege escalation)
- **Full paths** of source files related to the issue
- **Step-by-step reproduction** instructions
- **Proof-of-concept** or exploit code (if available and safe to share)
- **Impact assessment** — what an attacker could achieve
- **Affected versions** and environments

### Response Timeline

| Step                    | Expected Timeframe     |
|-------------------------|------------------------|
| Acknowledgment          | Within 24 hours        |
| Initial triage          | Within 48 hours        |
| Validation & risk assessment | Within 5 business days |
| Fix development         | Based on severity      |
| Coordinated disclosure  | Within 90 days of fix  |

### Coordinated Disclosure Process

1. **Report received** — acknowledgment sent within 24 hours
2. **Analysis and validation** — team assesses severity and impact
3. **Fix development** — patch is developed and tested internally
4. **Release** — fix is deployed to all supported versions
5. **Public disclosure** — advisory published after users have had time to update (typically 14 days post-release)

We aim to release fixes for **critical** vulnerabilities within 7 days and **high** severity within 30 days.

## Bug Bounty Program

AMF participates in a private bug bounty program. Rewards are offered for qualifying vulnerabilities based on severity:

| Severity | Reward Range      |
|----------|-------------------|
| Critical | $5,000 - $15,000 |
| High     | $1,000 - $5,000  |
| Medium   | $250 - $1,000    |
| Low      | $50 - $250       |

To qualify:
- Vulnerability must be in the latest supported release
- The report must include a clear reproduction
- Previously reported or known issues are excluded
- Automated tool outputs without manual validation are not accepted

For more details, see our full bug bounty policy: **https://amf.dev/security/bounty**

## Security Best Practices

### For Users

- **Keep AMF updated** — always run the latest supported version
- **Use HTTPS** in all production deployments
- **Set `AMF_ENVIRONMENT=production`** in production environments
- **Restrict API access** — use firewalls, VPNs, or API keys
- **Rotate API keys** regularly (every 90 days recommended)
- **Audit access logs** — monitor `AMF_LOG_LEVEL=info` output for anomalies
- **Use a reverse proxy** (nginx, Caddy, Traefik) in front of the API

### For Developers

- **Never commit secrets** or API keys to the repository
- **Use environment variables** for all sensitive configuration
- **Validate all user inputs** server-side — never trust client data
- **Run security checks** locally: `make lint`, `make test`, `make security-scan`
- **Use pre-commit hooks**: `pre-commit install` (configured in `.pre-commit-config.yaml`)
- **Enable 2FA** on your GitHub account
- **Sign commits** with GPG or SSH keys
- **Use branch protection** on `main` requiring review and CI passing
- **Audit dependencies** with `pip-audit` and `npm audit` before PRs

### API Security

- **Rate limiting**: Enforced on `/api/v1/format` and `/api/v1/validate`
- **File uploads**: Validated for type (`.docx` only), size (max 50MB), and content
- **CORS**: Configurable via `AMF_ALLOWED_ORIGINS` — restrict in production
- **Request tracking**: Every API call receives a unique `X-Request-ID` header
- **Authentication**: API keys with scoped permissions (read/write/admin)
- **TLS 1.2+**: Required for all production API traffic
- **Input sanitization**: All document content is sanitized before processing

### Infrastructure Security

- **Container scanning**: All Docker images are scanned for vulnerabilities
- **Base images**: Minimal distroless images used in production
- **Secrets management**: HashiCorp Vault or environment-specific secrets
- **Network isolation**: Backend services run in isolated network segments
- **Audit logging**: All administrative actions are logged with user attribution

## Past Security Advisories

| ID           | Date       | Severity | Description                          | Affected Versions | Status       |
|--------------|------------|----------|--------------------------------------|-------------------|--------------|
| AMF-SEC-2025-001 | 2025-03-15 | High     | XXE vulnerability in document parser | < 1.0.2           | Patched 1.0.2 |
| AMF-SEC-2025-002 | 2025-06-01 | Medium   | Path traversal in file output        | < 1.0.4           | Patched 1.0.4 |

For a complete list, see: **https://amf.dev/security/advisories**

## Dependencies

We continuously monitor dependencies for known vulnerabilities:

- **Automated scanning**: Dependabot and CodeQL run on every PR and commit
- **SBOM generation**: SPDX SBOMs are generated for each release
- **License compliance**: All dependencies must use approved licenses (MIT, Apache-2.0, BSD, ISC, etc.)
- **Dependency pinning**: All production dependencies are pinned to specific versions
- **Vulnerability database**: Snyk, GitHub Advisory Database, and OSV.dev are monitored daily

If you discover a vulnerable dependency, please report it via the process above.

## Contact

- **Security team**: security@amf.dev (PGP encrypted preferred)
- **Bug bounty**: https://amf.dev/security/bounty
- **Advisories**: https://amf.dev/security/advisories
- **Security policy**: https://amf.dev/security/policy

We appreciate your help in keeping AMF and its users safe.
