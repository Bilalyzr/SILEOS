# Sasha AI Provider Vault

SashaInfinity stores administrator-managed GLM and Gemini credentials in the
`ai_provider_credentials` table. Plaintext keys are encrypted with Fernet before
commit and are never returned by the API. The UI receives only a last-four hint.

## Production setup

1. Generate an independent high-entropy `AI_CREDENTIAL_ENCRYPTION_KEY` and add it
   to the backend deployment secret manager.
2. Keep that value stable across replicas, deploys, and restarts. Changing it
   makes existing ciphertext unreadable; re-encrypt stored credentials before a
   planned rotation.
3. Run Alembic revision `0048` before the application rollout.
4. Sign in as Admin or SuperAdmin and open `/admin/ai-providers`.
5. Add at least two active keys, assign unique labels, and use lower priority
   numbers for the preferred route.
6. Run the health check for every key. A health check makes one minimal provider
   request and may incur provider usage.

The server tries active database credentials in priority order and then legacy
`GLM_API_KEY` / `GEMINI_API_KEY` environment fallbacks. Provider failures update
health state without logging or returning the secret. Administrative create,
update, test, and delete operations are written to `platform_audit_events` using
masked metadata only.

## Supported providers

| Provider | Default model | Server API |
|---|---|---|
| Zhipu GLM | `glm-5.2` | OpenAI-compatible chat completions |
| Google Gemini | `gemini-2.5-flash` | Gemini `generateContent` REST API |

The administrator chooses a supported model per key and can change it without
re-entering the secret. GLM Coding Plan keys use a separate, restricted coding
endpoint and are not appropriate for the learner tutor; use a standard Zhipu
Open Platform server API key for Sasha learning features.

Provider health checks preserve a safe, actionable reason such as invalid
model, rejected key, missing model access, exhausted billing/quota, rate limit,
timeout, or network failure. Secrets, authorization headers, prompts and AI
replies are never included in these diagnostics.
