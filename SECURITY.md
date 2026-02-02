# Security / Secrets

**Do not commit credentials.** This repository expects IBM Quantum access tokens to be provided via:
- an environment variable (`QISKIT_IBM_TOKEN`), or
- a local `apikey.json` file (ignored by `.gitignore`).

If you accidentally commit a token, rotate it immediately in your IBM Quantum account and rewrite Git history.
