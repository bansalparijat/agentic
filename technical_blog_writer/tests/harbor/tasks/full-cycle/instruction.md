# Full local workflow regression (synthetic operator)

This task tests the **harness's local implementation**, not an agent's writing ability.
Run the deterministic scenario, without changing the installed harness:

```sh
python3 /opt/harness/tests/scenarios/run.py --scenario full-cycle --workspace /workspace/full-cycle
```

It must validate/prefill a simple brief without writes, then exercise COLLECTION →
DRAFT → REVISE → PREPARE and completion gates. Check evidence registration, two
drafts, fresh sequential-review reports, stale-review refusals, immutable approved
body, PREPARE-only title choice, title-change invalidation and refreshed delivery.
Expected refusals must not mutate workflow state. Preserve scenario artifacts.

Every user response/approval is an explicitly synthetic scripted-operator fixture.
HTML/PDF rendering and Google Doc readback are **test doubles**. The fake PDF is
not a rendered publication and the Google URL is not a real document. Do not call
MCP, fetch evidence, upload/publish anything, install packages or contact a model.
Do not reuse these attestations for real content. No credentials are needed.

A separate verifier inspects the resulting states, source/body/export hashes,
quality dependencies/archives, delivery files and refusal trace. Missing results
must fail, not be treated as a skipped/pass evaluation.
