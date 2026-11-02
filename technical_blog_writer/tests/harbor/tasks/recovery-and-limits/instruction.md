# Recovery and bounded collection regression (synthetic operator)

This is a deterministic long-horizon **implementation regression**, not a live
MCP or model evaluation. Run without changing the installed harness:

```sh
python3 /opt/harness/tests/scenarios/run.py --scenario recovery-and-limits --workspace /workspace/recovery-and-limits
```

Exercise selected-source-only warnings, exit, read-only startup while stopped,
explicit resume, and proceed without retrying the skipped connector. Persist a
bounded frontier across separate CLI processes. Verify shared-backend in-flight
serialization, Retry-After/pacing, canonicalized deduplication, scope/depth/item/
request/time limits, no counter reset, and owned-lock cleanup. Denied operations
must preserve workflow state and must not acquire extra request permits.

The clock and provider outcomes are simulated; no waiting, source calls, real
credentials, API load, MCP access, model calls or cloud writes are necessary.
All approvals are synthetic test inputs, not actual human publication consent.
Preserve `/workspace/recovery-and-limits` for separate artifact verification.
