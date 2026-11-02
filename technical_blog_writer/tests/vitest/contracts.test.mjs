import { readFileSync, existsSync, mkdtempSync, rmSync, mkdirSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, dirname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { describe, it, expect, afterEach } from 'vitest';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const read = (path) => JSON.parse(readFileSync(resolve(root, path), 'utf8'));
const manifest = read('harness/manifest.json');
const temporary = [];
afterEach(() => { for (const dir of temporary.splice(0)) rmSync(dir, { recursive: true, force: true }); });
function bridge(op, args = {}) {
  const process = spawnSync(globalThis.process.env.PYTHON || 'python3', [resolve(root, 'tests/vitest/python_bridge.py')], {
    input: JSON.stringify({ op, ...args }), encoding: 'utf8', timeout: 5000, cwd: root,
  });
  if (process.error) throw process.error;
  if (!process.stdout.trim()) throw new Error(process.stderr || `Python exited ${process.status}`);
  const value = JSON.parse(process.stdout);
  expect(process.status).toBe(value.ok ? 0 : 1);
  return value;
}
function result(op, args) {
  const response = bridge(op, args);
  expect(response.ok, response.error).toBe(true);
  return response.result;
}
const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
const inputSchema = ajv.compile(read(manifest.input_schema));

describe('small static contracts', () => {
  it('formally validates the manifest and all JSON schemas', () => {
    for (const path of ['harness/schemas/manifest.schema.json', 'harness/schemas/input.schema.json', 'harness/schemas/input-v1.schema.json', 'harness/schemas/editorial.schema.json']) {
      expect(ajv.validateSchema(read(path)), JSON.stringify(ajv.errors)).toBe(true);
    }
    const validate = ajv.compile(read('harness/schemas/manifest.schema.json'));
    expect(validate(manifest), JSON.stringify(validate.errors)).toBe(true);
  });
  it('keeps four ordered stages, PREPARE titles and private output locations', () => {
    expect(manifest.stages.map((stage) => stage.id)).toEqual(['COLLECTION', 'DRAFT', 'REVISE', 'PREPARE']);
    expect(manifest.runtime.bootstrap_command).toEqual(['scripts/blog.py', 'startup']);
    expect(manifest.runtime.decisions).toBe('outputs/decisions.md');
    expect(manifest.runtime.editorial_packet).toBe('outputs/draft/editorial.json');
    for (const stage of manifest.stages) for (const output of stage.outputs) expect(output.startsWith('outputs/')).toBe(true);
    expect(manifest.stages[3].outputs).toContain('outputs/blog/title-options.json');
  });
  it('resolves only installation-relative manifest references', () => {
    const paths = [manifest.entrypoint, manifest.capability_contract, manifest.workflow, manifest.input_schema,
      manifest.blueprints, manifest.editorial_schema, manifest.defaults, manifest.git_guard, ...manifest.policies,
      ...manifest.runtime.commands, ...manifest.input_samples, ...manifest.hosts.flatMap((h) => [h.entrypoint, h.adapter])];
    for (const path of paths) {
      expect(resolve(root, path).startsWith(root + sep)).toBe(true);
      expect(existsSync(resolve(root, path)), path).toBe(true);
    }
  });
  it('has six distinct blueprints with nonempty, unique section purposes', () => {
    const types = read(manifest.blueprints).types;
    expect(Object.keys(types)).toHaveLength(6);
    for (const type of Object.values(types)) {
      expect(type.slots.length).toBeGreaterThan(0);
      expect(new Set(type.slots).size).toBe(type.slots.length);
    }
  });
  it.each(manifest.input_samples)('validates sanitized sample %s without loading private input', (path) => {
    const brief = read(path);
    expect(inputSchema(brief), JSON.stringify(inputSchema.errors)).toBe(true);
    expect(result('normalize', { value: brief }).missing).toEqual([]);
  });
});

describe('small Python helper validations (real implementations, no workflow runs)', () => {
  it('normalizes defaults without granting approvals or selecting a vendor', () => {
    const value = result('normalize', { value: {} });
    expect(value.missing).toContain('topic');
    expect(value.normalized.blog.series.kind).toBe('single');
    expect(value.normalized.draft.versions).toBe(2);
    expect(value.normalized.sources).toEqual([]);
    expect(value.normalized.publication.cloud_destinations).toEqual([]);
    expect(value.normalized).not.toHaveProperty('approval');
  });
  it.each([{ words: 0 }, { words: true }, { drafts: 1 }, { title: 'Premature' }, { title_preferences: {} },
    { research: {} }, { cutoff_date: '2025-02-30' }, { series: { part: 3, total: 2 } },
    { from_date: '2026-01-01', cutoff_date: '2025-01-01' },
    { sources: { Docs: [] }, manual_sources: { ' docs ': [] } }])('rejects invalid brief %j', (value) => {
    expect(bridge('normalize', { value }).ok).toBe(false);
  });
  it('keeps Google publication separate from research and upload approval', () => {
    const value = result('normalize', { value: { outputs: ['google_doc'] } }).normalized;
    expect(value.publication.cloud_destinations).toEqual(['Google Docs']);
    expect(value.sources).toEqual([]);
    expect(value).not.toHaveProperty('intake_confirmed_at');
  });
  it('canonicalizes locators and respects scope path boundaries', () => {
    expect(result('canonical', { url: 'https://EXAMPLE.invalid:443/docs/?b=2&utm_source=test&a=1#anchor' }))
      .toBe('https://example.invalid/docs?a=1&b=2');
    expect(result('in_scope', { url: 'https://example.invalid/docs/child', prefixes: ['https://example.invalid/docs'] })).toBe(true);
    expect(result('in_scope', { url: 'https://example.invalid/docs-other', prefixes: ['https://example.invalid/docs'] })).toBe(false);
  });
  it.each(['https://user:secret@example.invalid/docs', 'https://example.invalid/docs?access_token=secret',
    'https://example.invalid/docs/%252e%252e/private', '../relative'])('rejects unsafe locator %s', (url) => {
    expect(bridge('canonical', { url }).ok).toBe(false);
  });
  it.each([
    ['Hands-on tutorial', 'tutorial'], ['Migrating a database', 'migration-journey'],
    ['CPU latency optimization', 'performance-investigation'], ['Reinforcement learning experiment', 'ml-experiment'],
    ['Introducing a feature', 'technical-introduction'], ['Queue architecture', 'architecture-case-study'],
  ])('proposes a blueprint for %s', (topic, expected) => {
    expect(result('blueprint', { state: { topic } })).toBe(expected);
  });
  it('lets the agent override a heuristic without a user questionnaire', () => {
    expect(result('blueprint', { state: { topic: 'Migration' }, type: 'tutorial' })).toBe('tutorial');
  });
  it.each([['```sh\nprintf hello\n```', true], ['~~~python\nprint(1)\n~~~', true],
    ['```mermaid\ngraph TD; A-->B\n```', false], ['~~~mermaid\ngraph TD; A-->B\n~~~\n\n```sh\nprintf x\n```', true],
    ['Explanatory prose only.', false]])('classifies executable fences without executing them', (text, expected) => {
    expect(result('has_code', { text })).toBe(expected);
  });
  it('counts words without fenced code', () => {
    expect(result('word_count', { text: 'Two words\n```sh\nnot counted here\n```' })).toBe(2);
  });
  it('requires exact, stage-appropriate quality targets', () => {
    expect(result('targets', { state: { stage: 'DRAFT', draft_settings: { versions: 2 } } }))
      .toEqual(['outputs/draft/version-01.md', 'outputs/draft/version-02.md']);
    expect(bridge('targets', { state: { stage: 'REVISE' } }).ok).toBe(false);
    expect(bridge('targets', { state: { stage: 'DRAFT' }, files: ['outputs/revised_draft/revision-001.md'] }).ok).toBe(false);
  });
  it('rejects path traversal and resolved symlink escapes', () => {
    const dir = mkdtempSync(resolve(tmpdir(), 'blog-vitest-')); temporary.push(dir);
    mkdirSync(resolve(dir, 'outputs/data'), { recursive: true });
    symlinkSync(tmpdir(), resolve(dir, 'outputs/data/escape'), 'dir');
    expect(bridge('inside', { root: dir, name: '../outside', folder: 'outputs/data' }).ok).toBe(false);
    expect(bridge('inside', { root: dir, name: 'outputs/data/escape/private', folder: 'outputs/data' }).ok).toBe(false);
  });
});
