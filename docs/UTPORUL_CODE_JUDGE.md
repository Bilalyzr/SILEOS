# Utporul code judge

Utporul coding assessments use three separate trust zones:

1. The LMS API stores challenge definitions, keeps expected outputs private,
   enforces enrollment and attempt policy, leases jobs, and calculates scores.
2. `code-judge-worker/` carries source and stdin between the LMS and Judge0. It
   never executes learner code and never receives expected outputs.
3. A separately isolated Judge0 CE installation compiles and executes source
   with CPU, memory, file-size, and `enable_network=false` limits.

The separation is intentional. Never add `subprocess`, `eval`, an interpreter,
or a compiler to the LMS API or worker.

## Production setup

Deploy Judge0 CE on a dedicated Linux host or private cluster by following the
[official Judge0 deployment release](https://github.com/judge0/judge0/releases).
Judge0's official API supports sandboxed execution, per-submission resource
limits, and disabling network access. Its API contract is documented in the
[official submissions reference](https://github.com/judge0/judge0/blob/master/docs/api/submissions/submissions.md).

Keep port 2358 private. Allow only the code-judge worker to reach it. Configure:

```dotenv
CODE_RUNNER_TOKEN=<independent random secret of at least 32 characters>
JUDGE0_URL=http://private-judge0:2358
JUDGE0_AUTH_TOKEN=<Judge0 authentication token when enabled>
```

Then start the opt-in profile:

```bash
docker compose --profile coding up -d code-judge-worker
```

The worker discovers installed language IDs from `/languages`, so compiler
upgrades do not require application code changes. Supported product language
keys are `python`, `javascript`, `typescript`, `java`, `cpp`, and `c`.

## Failure and privacy behavior

- Submission calls are idempotent per learner and client key.
- A judge lease expires after 90 seconds and can be reclaimed.
- Transient failures back off and retry five times before becoming terminal.
- The worker never receives hidden expected output.
- The learner response never exposes hidden input, expected output, stdout, or
  stderr. Instructors and platform admins may inspect complete results.
- Judge0 callbacks are disabled from this integration; the worker polls the
  private API and reports through a lease token.
