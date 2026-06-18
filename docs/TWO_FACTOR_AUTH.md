# Two-Factor Authentication (2FA) Policy

## Requirement

All developers with commit access to the ScholarForm AI repository MUST have two-factor authentication (2FA) enabled on their GitHub account.

## Scope

This policy applies to:

- Core Team members
- Committers
- Anyone with write access to `main` branch
- Anyone with access to sensitive repository data (including private vulnerability reports)

## Implementation

### GitHub 2FA

GitHub supports multiple 2FA methods. We require **TOTP (Time-based One-Time Password)** or hardware security key (WebAuthn), as these provide cryptographic verification. SMS-based 2FA, while permitted by GitHub, does not meet our cryptographic 2FA requirement due to known security weaknesses.

### Requirement Level

| Requirement | OpenSSF Level |
|-------------|---------------|
| 2FA for all developers with write access | Gold (MUST) |
| Cryptographic 2FA (TOTP or hardware key) | Gold (SHOULD) |

### Enforcement

2FA compliance is enforced through GitHub organization settings:

1. **Organization-level**: GitHub requires 2FA for all members of the organization.
2. **Repository-level**: Branch protection rules require all committers to have verified accounts.
3. **New members**: Must enable 2FA before receiving write access.

## How to Enable 2FA

1. Go to GitHub Settings → Password and authentication → Two-factor authentication.
2. Click "Enable two-factor authentication".
3. Choose **Set up using an app** (TOTP) or **Security key** (WebAuthn).
4. Scan the QR code with your authenticator app (e.g., Google Authenticator, Authy, 1Password).
5. Enter the verification code to confirm setup.
6. Download and store your recovery codes in a secure location.

## Recovery

If you lose access to your 2FA device:

1. Use one of your recovery codes (saved during initial setup).
2. Contact a GitHub organization owner to request a 2FA reset.
3. Re-enable 2FA immediately after regaining access.

--- 

*Last updated: June 2026*
