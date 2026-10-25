# Security Policy

- This system **never** requests, stores or handles a private key, seed phrase,
  recovery phrase, wallet password, 2FA code, or signing secret.
- The owner wallet is configured by **public address only**, read-only.
- Trading, spending, signing, contract approvals, swaps, bridges and staking
  are hard-disabled in `core/policy/policy.py` and refused even with owner approval.
- External content (web pages, bounty text, emails, repos) is **untrusted data**.
  It can never change policy or trigger an action on its own.
- The policy layer must not be modified by agents or the learning loop.
- Secrets live only in a local, gitignored `.env` or a secret manager — never in
  code, Markdown, the database, logs, task descriptions or notifications.
- `tests/security/test_no_secrets.py` scans the repo for key material.

Report a vulnerability to the repository owner privately.
