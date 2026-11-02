# Testing the technical-blog harness

Testing does **not** start/resume the real blog. Never point scenarios at an existing
workspace, copy private evidence into fixtures, or probe production MCPs for tests.
Ask before installing dependencies, browsers or container images.

## Test layers

| Layer | Command | Purpose |
| --- | --- | --- |
| Vitest unit/contract | `npm run test:unit` | Small schema/manifest/reference checks and actual pure Python helper validations via a JSON bridge. No workflow runs. |
| Python regression | `python3 -m unittest discover -s tests -v` | Existing workflow, safety, editorial, collection, adapter and test-tooling regressions. Retained, not replaced. |
| Integration, local | `python3 tests/scenarios/run.py` | Two longer journeys across separate CLI processes, isolated temporary workspaces and independent artifact verification. No new dependencies. |
| Integration, Harbor | `python3 scripts/run_harbor.py` | The same journeys as Harbor tasks, Docker sandboxes, a separate verifier container and numerical rewards. |

`npm test` runs **Vitest only**. Expensive/container tests are opt-in, never silently
started by unit tests. These are deterministic implementation regressions, **not**
a benchmark proving an LLM writes correctly or follows every instruction. Live-host
checks remain in [the adapter smoke checklist](../harness/adapters/README.md).

## 1. Vitest: small validations

Requirements: Node **22.12+ in the 22.x line**, **24.x**, or **26+**, npm, and
Python **3.10+** on PATH. `PYTHON=/path/to/python` selects the JSON-bridge interpreter.
The exact Node range is declared in [package.json](../package.json).

After approval to install development dependencies:

```sh
npm ci --ignore-scripts
npm run test:unit
npm run test:unit:watch
```

Vitest, Ajv and Ajv formats are development-only dependencies pinned in
`package.json`/`package-lock.json`. Ajv validates JSON Schema 2020-12; the bridge
calls the real `intake`, `collection`, `editorial` and `blog` helpers rather than
reimplementing their logic in JavaScript. It accepts only named test operations,
not arbitrary Python expressions. The suite reads only registered sanitized
samples and contract files, never `input/blog.json`, `project.json` or `outputs/`.

## 2. Existing Python regression suite

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py tests/scenarios/*.py tests/vitest/python_bridge.py
```

Core helpers still require only Python 3.10+. Optional export tests can skip when
Markdown dependencies are absent; report skips rather than calling them passes.
`test_test_tooling.py` checks staging privacy, symlinks, task policies, fail-closed
verifiers and job-result parsing. Its TOML inspection needs Python 3.11+ and skips
on 3.10. Synthetic JSON result fixtures do **not** certify a real Harbor job.

## 3. Longer integration journeys without Docker

```sh
python3 tests/scenarios/run.py
python3 tests/scenarios/run.py --scenario full-cycle
python3 tests/scenarios/run.py --scenario recovery-and-limits
```

By default, temporary directories are cleaned after each run. To inspect artifacts,
use a **new, nonexistent path outside the installation**:

```sh
python3 tests/scenarios/run.py --scenario full-cycle --workspace /tmp/blog-cycle-check
```

The runner refuses existing workspaces. Traces/results are under that workspace's
`outputs/data/`; state remains `project.json`. Run the read-only verifier again:

```sh
python3 tests/scenarios/verify.py --scenario full-cycle \
  --workspace /tmp/blog-cycle-check --installation /absolute/path/to/this/harness
```

### `full-cycle`

Exercises brief validation/prefilling without writes, original input snapshots,
evidence hashes, COLLECTION → DRAFT → REVISE → PREPARE, two draft variants,
missing/stale quality-report refusals and refreshes, exact revision/body pinning,
PREPARE-only title selection, explicit hero skip, four-format completion gates,
title reselection invalidating prior exports/cloud metadata, and refreshed delivery.

**Important boundary:** scripted operator answers and review attestations are
synthetic. The export adapter invokes the real `blog.export` path but replaces
HTML/browser rendering with labelled test doubles. Its PDF bytes are **not a
rendered publication**. The Google Doc URL/readback is explicitly fake and never
fetched or created. This tests local delivery/integrity gates, not visual quality,
real publication permission or live cloud success. Never use these fixtures for a
real article or weaken production gates to make tests pass.

### `recovery-and-limits`

Exercises selected-source-only MCP warnings, exit, saved/stopped startup precedence
over missing input, explicit resume/proceed, and no retry of the skipped connector.
A persistent frontier crosses process boundaries while shared-backend permits
honor in-flight serialization, Retry-After/pacing, URL deduplication and scope/depth/
item/request/time limits. Denials preserve workflow state/counters; an explicitly
owned test lock checks contention/cleanup. A **test-only clock** advances simulated
time; no sleeps or real source calls occur.

## 4. Harbor: isolated full-cycle/longer tests

This means [Harbor, the agent-evaluation framework](https://docs.harborframework.com/),
not the container registry product. The suite pins **Harbor 0.25.0**, task format
**1.4**, and uses its deterministic **oracle** runner (no model API keys/cost).
Harbor requires its own **Python 3.12+** environment; the blog runtime does not.
Docker Engine/Desktop **with Compose** must be available/running.

After approval to install tooling and fetch images, choose one setup:

```sh
# Isolated virtualenv; requires an existing Python 3.12+ interpreter.
python3.12 -m venv .venv-harbor
.venv-harbor/bin/python -m pip install -r requirements-test-harbor.txt
python3 scripts/run_harbor.py --harbor .venv-harbor/bin/harbor

# Alternatively, uv can manage the isolated tool (may download Python 3.12).
uv tool install --python 3.12 harbor==0.25.0
python3 scripts/run_harbor.py
```

Select one task with `--scenario full-cycle` or `--scenario recovery-and-limits`.
The npm equivalent is `npm run test:harbor -- --harbor .venv-harbor/bin/harbor`.

The wrapper:

1. Checks installed Harbor version and Docker; **never auto-installs** anything.
2. Stages fresh self-contained tasks under ignored `build/harbor/dataset-*` using
   a public-file allowlist. Personal inputs, real state/outputs, credentials,
   arbitrary extra template files and symlinked sources are excluded/rejected.
3. Runs both tasks serially: oracle, concurrency 1, one attempt, zero retries.
   Task/agent/verifier runtime networking is disabled; build/helper-image downloads
   can still need network access. The wrapper disables Harbor host telemetry.
4. Uses a **separate verifier sandbox** with declared synthetic workspace artifacts.
   Verifiers inspect artifacts rather than running the scenario to manufacture a
   result; initialize reward to **0**, and write **1** only after all checks pass.
   Missing results, stale hashes or failed checks cannot count as a skipped pass.
   This binary reward is a contract-test result, not an editorial quality score.
5. Retains dataset snapshots and job logs under ignored `build/harbor/`. A zero
   Harbor process exit alone is insufficient: the wrapper requires every expected
   trial to finish without errors and earn reward 1, with no missing/duplicate tasks.

The base image pins the Python 3.12/Debian family, not an immutable digest. Pin an
approved image digest if byte-identical environment reproduction is required.
No credentials are declared/passed into tasks. Do not publish/upload these jobs,
add a paid model runner, or enable live MCP/cloud access without explicit approval.
This is not a hardened adversarial-agent/reward-hacking evaluation.

### Stage or inspect tasks without installing Harbor

```sh
python3 scripts/run_harbor.py --prepare-only
# Or choose a new external dataset directory explicitly:
python3 scripts/prepare_harbor.py --destination /tmp/blog-harbor-tasks
```

Source templates in `tests/harbor/tasks/` are intentionally not standalone Docker
contexts: they must be staged first. Never use `COPY .` with this repository as a
Docker context. Staged tasks contain `instruction.md`, `task.toml`, a bounded
`environment/`, `solution/solve.sh`, and `tests/test.sh` plus copied verification
contracts. See the official [task configuration](https://docs.harborframework.com/tasks/configuration.md)
and [verifier](https://docs.harborframework.com/tasks/verifier.md) references.

For a manual Harbor invocation after staging (the wrapper's result checks are then
**your responsibility**):

```sh
HARBOR_TELEMETRY=0 harbor run -p /tmp/blog-harbor-tasks -a oracle \
  -n 1 -k 1 -r 0 -o build/harbor/jobs --job-name manual-check
```

## Privacy and interpretation

- No real blog is initialized/adopted/resumed by test tooling. All scenario
  approvals are test fixtures, never evidence of actual human consent.
- Never stage/commit `outputs/`, even inside copied test runs. Generated test
  dependencies, datasets/jobs and reports are also ignored; do not force-add them.
- Local unit/scenario success is not a successful Vitest/Harbor invocation unless
  that runner was actually executed. Record missing tools/failed builds honestly.
- Passing tests cannot prove source relevance, factual/legal correctness, live
  MCP authentication, user permission, LLM behavior, browser layout or real cloud
  document creation. Those require separate authorized checks.
