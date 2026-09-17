import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');
const SKILL_DIR = path.join(REPO_ROOT, 'skills', 'image-prompt-guide');
const SKILL_FILE = path.join(SKILL_DIR, 'SKILL.md');
const CATALOG_FILE = path.join(SKILL_DIR, 'references', 'patterns.json');
const SEARCH_SCRIPT = path.join(SKILL_DIR, 'scripts', 'search.py');
const PYTHON_TESTS = path.join(SKILL_DIR, 'scripts', 'tests', 'test_search.py');

function resolvePython() {
  for (const candidate of ['python', 'python3', 'py']) {
    const probe = spawnSync(candidate, ['--version'], { encoding: 'utf8' });
    if (probe.status === 0) return candidate;
  }
  return null;
}

function readCatalog() {
  return JSON.parse(fs.readFileSync(CATALOG_FILE, 'utf8'));
}

function runSearch(args) {
  const python = resolvePython();
  assert.ok(python, 'a Python 3 interpreter is required to run the bundled search script');
  const output = execFileSync(python, [SEARCH_SCRIPT, ...args, '--json'], {
    encoding: 'utf8',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  });
  return JSON.parse(output);
}

describe('image-prompt-guide package', () => {
  test('frontmatter, bundled references, and links stay consistent', () => {
    const content = fs.readFileSync(SKILL_FILE, 'utf8');
    const frontmatter = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    assert.ok(frontmatter, 'SKILL.md must carry YAML frontmatter');
    assert.match(frontmatter[1], /name: image-prompt-guide/);
    assert.match(frontmatter[1], /reverse-engineering a prompt from a supplied image/);

    const links = [...content.matchAll(/\]\((references\/[^)]+)\)/g)].map((match) => match[1]);
    assert.ok(links.length > 0, 'SKILL.md must point at its bundled references');
    for (const link of links) {
      assert.ok(
        fs.existsSync(path.join(SKILL_DIR, link)),
        `SKILL.md links ${link} but the file is missing`,
      );
    }
  });

  test('the README lists the skill', () => {
    const readme = fs.readFileSync(path.join(REPO_ROOT, 'README.md'), 'utf8');
    assert.match(readme, /image-prompt-guide/);
  });

  test('every catalog record carries provenance, providers, and modes', () => {
    const catalog = readCatalog();
    const seen = new Set();
    for (const record of catalog.records) {
      assert.ok(!seen.has(record.id), `duplicate record id ${record.id}`);
      seen.add(record.id);
      assert.ok(record.providers.length > 0, `${record.id} has no providers`);
      assert.ok(record.modes.length > 0, `${record.id} has no modes`);
      assert.match(
        record.source,
        /^author$|^[\w.-]+\/[\w.-]+ .+|^https?:\/\/\S+$/,
        `${record.id} source must be "author", "<owner>/<repo> <path>", or a documentation URL`,
      );
    }
  });

  test('search resolves real intents and refuses coincidental token overlap', () => {
    const tattoo = runSearch(['tattoo flash sheet', '-n', '1']);
    assert.equal(tattoo.results[0].id, 'template-tattoo-flash');

    const reverse = runSearch(['reverse prompt from image', '-n', '1']);
    assert.equal(reverse.results[0].id, 'mode-reverse-anchors');
    assert.ok(reverse.results[0].modes.includes('reverse'));

    const noise = runSearch(['menu board restaurant', '-n', '3']);
    assert.equal(noise.count, 0);
    assert.ok(Array.isArray(noise.suggestions));
  });

  test('the CLI translates a non-English query before matching', () => {
    const vietnamese = runSearch(['mẫu A mặc đồ của mẫu B thay background mẫu C']);
    assert.equal(vietnamese.query, 'mẫu A mặc đồ của mẫu B thay background mẫu C');
    assert.ok(
      vietnamese.query_used.includes('wearing outfit') && vietnamese.query_used.includes('replace background'),
      `expected an English query, received ${vietnamese.query_used}`,
    );
    assert.equal(vietnamese.results[0].id, 'mode-multi-reference');
  });

  test('bundled python suite passes', () => {
    const python = resolvePython();
    if (!python) {
      return; // no interpreter in this environment; CI installs one
    }
    execFileSync(python, [PYTHON_TESTS], { encoding: 'utf8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
  });
});
