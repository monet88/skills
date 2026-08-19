import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

import {
  BM25,
  CSV_CONFIG,
  STACK_CONFIG,
  AVAILABLE_STACKS,
  detect_domain,
  search,
  search_stack,
  parseCSV,
  loadCSV
} from '../skills/ask-impeccable/research/core.mjs';

import { format_output, parseArgs } from '../skills/ask-impeccable/research/search.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');

const REQUIRED_ROOT_CSVS = [
  'app-interface.csv',
  'charts.csv',
  'colors.csv',
  'google-fonts.csv',
  'icons.csv',
  'landing.csv',
  'products.csv',
  'react-performance.csv',
  'styles.csv',
  'typography.csv',
  'ux-guidelines.csv'
];

const REQUIRED_STACKS = [
  'angular', 'astro', 'avalonia', 'flutter', 'html-tailwind',
  'javafx', 'jetpack-compose', 'laravel', 'nextjs', 'nuxt-ui',
  'nuxtjs', 'react-native', 'react', 'shadcn', 'svelte',
  'swiftui', 'threejs', 'uno', 'uwp', 'vue', 'winui', 'wpf'
];

describe('Ask Impeccable UI Research Parity & Security Suite', () => {
  let tempTestDir;
  let installedSkillDir;

  before(() => {
    tempTestDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ask-impeccable-research-test-'));

    // Install skill into an isolated environment
    execSync(`npx skills add "${REPO_ROOT}" --agent antigravity --copy -y`, {
      cwd: tempTestDir,
      encoding: 'utf8',
      timeout: 30000,
    });

    installedSkillDir = path.join(tempTestDir, '.agents', 'skills', 'ask-impeccable');
  });

  after(() => {
    if (tempTestDir && fs.existsSync(tempTestDir)) {
      fs.rmSync(tempTestDir, { recursive: true, force: true });
    }
  });

  test('Criterion 1: Approved research datasets exist in source and installed artifact', () => {
    const sourceDataDir = path.join(REPO_ROOT, 'skills', 'ask-impeccable', 'research', 'data');
    const installedDataDir = path.join(installedSkillDir, 'research', 'data');

    for (const csvName of REQUIRED_ROOT_CSVS) {
      assert.ok(fs.existsSync(path.join(sourceDataDir, csvName)), `Source missing ${csvName}`);
      assert.ok(fs.existsSync(path.join(installedDataDir, csvName)), `Installed missing ${csvName}`);
    }

    for (const stackName of REQUIRED_STACKS) {
      const stackFile = `${stackName}.csv`;
      assert.ok(fs.existsSync(path.join(sourceDataDir, 'stacks', stackFile)), `Source missing stack ${stackFile}`);
      assert.ok(fs.existsSync(path.join(installedDataDir, 'stacks', stackFile)), `Installed missing stack ${stackFile}`);
    }
  });

  test('Criterion 2: BM25 algorithm preserves exact tokenization, IDF, and scoring formulas', () => {
    const bm25 = new BM25(1.5, 0.75);

    // Test tokenization
    assert.deepEqual(bm25.tokenize('Hello, World! A quick test.'), ['hello', 'world', 'quick', 'test']);
    assert.deepEqual(bm25.tokenize('Special-characters & _underscore_!'), ['special', 'characters', '_underscore_']);
    assert.deepEqual(bm25.tokenize('Single letters a b c are filtered out'), ['single', 'letters', 'are', 'filtered', 'out']);
    assert.deepEqual(bm25.tokenize(''), []);

    // Fit with sample corpus
    const docs = [
      'minimal dark mode design for dashboard',
      'dark mode color palette with high contrast',
      'light mode typography and heading styles'
    ];
    bm25.fit(docs);

    assert.equal(bm25.N, 3);
    assert.equal(bm25.corpus.length, 3);
    assert.equal(bm25.doc_lengths.length, 3);
    assert.equal(bm25.avgdl, (6 + 7 + 6) / 3);

    // Verify IDF formula: log((N - freq + 0.5) / (freq + 0.5) + 1)
    // 'dark' appears in doc 0 and doc 1 -> freq = 2
    // expected IDF = Math.log((3 - 2 + 0.5)/(2 + 0.5) + 1) = Math.log(1.5 / 2.5 + 1) = Math.log(1.6)
    const darkIdf = bm25.idf.get('dark');
    assert.ok(darkIdf !== undefined);
    assert.ok(Math.abs(darkIdf - Math.log(1.6)) < 1e-9);

    // Score against query 'dark' (present in doc 0 and 1, absent in doc 2)
    const darkScores = bm25.score('dark');
    assert.equal(darkScores.length, 3);
    assert.ok(darkScores[0].score > 0);
    assert.ok(darkScores[1].score > 0);
    assert.equal(darkScores[2].score, 0); // doc 2 does not contain 'dark'

    // Score against query absent from all docs
    const absentScores = bm25.score('cyberpunk');
    assert.equal(absentScores.length, 3);
    assert.equal(absentScores[0].score, 0);
    assert.equal(absentScores[1].score, 0);
    assert.equal(absentScores[2].score, 0);
  });

  test('CSV parser trailing fields produce null for missing and empty string for present-but-empty', () => {
    const shortCsv = 'a,b,c\n1,2';
    const parsedShort = parseCSV(shortCsv);
    assert.deepEqual(parsedShort, [{ a: '1', b: '2', c: null }]);

    const emptyFieldCsv = 'a,b,c\n1,2,';
    const parsedEmpty = parseCSV(emptyFieldCsv);
    assert.deepEqual(parsedEmpty, [{ a: '1', b: '2', c: '' }]);
  });

  test('Criterion 3: Stable structured output contract for detect_domain, search, and search_stack', () => {
    // detect_domain
    assert.equal(detect_domain('landing hero page cta'), 'landing');
    assert.equal(detect_domain('color hex palette accent'), 'color');
    assert.equal(detect_domain('unknown text without any keywords'), 'style');

    // search
    const searchRes = search('minimalist', 'style', 2);
    assert.equal(typeof searchRes.domain, 'string');
    assert.equal(typeof searchRes.query, 'string');
    assert.equal(typeof searchRes.file, 'string');
    assert.equal(typeof searchRes.count, 'number');
    assert.ok(Array.isArray(searchRes.results));
    assert.equal(searchRes.domain, 'style');
    assert.equal(searchRes.query, 'minimalist');
    assert.equal(searchRes.file, 'styles.csv');
    assert.equal(searchRes.count, searchRes.results.length);

    // search_stack
    const stackRes = search_stack('hooks state', 'react', 2);
    assert.equal(stackRes.domain, 'stack');
    assert.equal(stackRes.stack, 'react');
    assert.equal(typeof stackRes.query, 'string');
    assert.equal(typeof stackRes.file, 'string');
    assert.equal(typeof stackRes.count, 'number');
    assert.ok(Array.isArray(stackRes.results));
    assert.equal(stackRes.file, 'stacks/react.csv');

    // Unknown stack error contract
    const unknownStackRes = search_stack('test', 'unknown_stack_xyz');
    assert.ok(unknownStackRes.error);
    assert.match(unknownStackRes.error, /Unknown stack: unknown_stack_xyz/);
  });

  test('Criterion 4: Golden fixtures parity against Python oracle', () => {
    const fixturePath = path.join(__dirname, 'fixtures', 'research-golden.json');
    assert.ok(fs.existsSync(fixturePath), 'Golden fixture file must exist');

    const golden = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));

    // 1. Verify detect_domain parity
    for (const [query, expectedDomain] of Object.entries(golden.detect_domain)) {
      const actualDomain = detect_domain(query);
      assert.equal(
        actualDomain,
        expectedDomain,
        `detect_domain mismatch for "${query}": expected ${expectedDomain}, got ${actualDomain}`
      );
    }

    // 2. Verify search parity
    for (const item of golden.search) {
      const actual = search(item.query, item.domain_arg, item.max_results_arg);
      assert.deepEqual(
        actual,
        item.expected,
        `Search mismatch for query "${item.query}", domain "${item.domain_arg}"`
      );
    }

    // 3. Verify search_stack parity
    for (const item of golden.search_stack) {
      const actual = search_stack(item.query, item.stack_arg, item.max_results_arg);
      assert.deepEqual(
        actual,
        item.expected,
        `search_stack mismatch for query "${item.query}", stack "${item.stack_arg}"`
      );
    }

    // 4. Verify error contracts parity
    for (const item of golden.errors) {
      if (item.type === 'unknown_stack') {
        const actual = search_stack(item.query, item.stack_arg);
        assert.deepEqual(actual, item.expected);
      }
    }
  });

  test('Criterion 5: Research runtime executes with Node.js only without third-party dependencies', () => {
    const installedSearchPath = path.join(installedSkillDir, 'research', 'search.mjs');
    assert.ok(fs.existsSync(installedSearchPath), `Installed search.mjs must exist at ${installedSearchPath}`);

    // Execute in a clean temp directory with no node_modules
    const cleanDir = path.join(tempTestDir, 'clean-exec-env');
    fs.mkdirSync(cleanDir, { recursive: true });

    const output = execSync(`node "${installedSearchPath}" "dashboard" --json`, {
      cwd: cleanDir,
      encoding: 'utf8',
      timeout: 10000,
    });

    const parsed = JSON.parse(output);
    assert.ok(parsed.domain);
    assert.ok(parsed.results.length > 0);
  });

  test('Criterion 6: Research runtime performs zero project-file writes', () => {
    const installedSearchPath = path.join(installedSkillDir, 'research', 'search.mjs');
    const isolatedDir = path.join(tempTestDir, 'zero-write-env');
    fs.mkdirSync(isolatedDir, { recursive: true });

    // Snapshot directory contents before
    const beforeSkillFiles = fs.readdirSync(installedSkillDir, { recursive: true });
    const beforeCwdFiles = fs.readdirSync(isolatedDir, { recursive: true });

    // Execute searches
    execSync(`node "${installedSearchPath}" "dark mode"`, { cwd: isolatedDir, encoding: 'utf8' });
    execSync(`node "${installedSearchPath}" "vue reactivity" --stack vue`, { cwd: isolatedDir, encoding: 'utf8' });
    execSync(`node "${installedSearchPath}" "colors" --domain color --json`, { cwd: isolatedDir, encoding: 'utf8' });

    // Snapshot directory contents after
    const afterSkillFiles = fs.readdirSync(installedSkillDir, { recursive: true });
    const afterCwdFiles = fs.readdirSync(isolatedDir, { recursive: true });

    assert.deepEqual(afterCwdFiles, beforeCwdFiles, 'CWD must not contain any created or modified files');
    assert.deepEqual(afterSkillFiles, beforeSkillFiles, 'Installed skill directory must not have new or modified files');
  });

  test('Criterion 7: Distributed artifact does NOT contain or expose design_system, persist, or templates', () => {
    // Check files in source and installed skill
    const checkForbiddenFiles = (dir) => {
      const allFiles = fs.readdirSync(dir, { recursive: true }).map(f => f.toString());
      const forbiddenNames = [
        'design_system.py',
        'design_system.mjs',
        'design_system.js',
        '_sync_all.py',
        'design.csv',
        'draft.csv',
        'ui-reasoning.csv',
        'MASTER.md',
        'core.js',
        'search.js',
        'index.js'
      ];
      for (const name of forbiddenNames) {
        assert.ok(
          !allFiles.some(f => f.endsWith(path.sep + name) || f === name),
          `Forbidden/redundant file "${name}" found in ${dir}`
        );
      }
    };

    checkForbiddenFiles(path.join(REPO_ROOT, 'skills', 'ask-impeccable'));
    checkForbiddenFiles(installedSkillDir);

    // Verify search CLI args reject/do not implement design-system options
    const parsedArgs = parseArgs(['--design-system', '--persist', '-p', 'Project', '--page', 'home']);
    assert.equal(parsedArgs.design_system, undefined, 'CLI must not parse design_system');
    assert.equal(parsedArgs.persist, undefined, 'CLI must not parse persist');
  });

  test('Criterion 8: Machine-readable provenance metadata is present and valid', () => {
    const sourceProvPath = path.join(REPO_ROOT, 'skills', 'ask-impeccable', 'research', 'provenance.json');
    const installedProvPath = path.join(installedSkillDir, 'research', 'provenance.json');

    assert.ok(fs.existsSync(sourceProvPath), 'Source provenance.json must exist');
    assert.ok(fs.existsSync(installedProvPath), 'Installed provenance.json must exist');

    for (const provPath of [sourceProvPath, installedProvPath]) {
      const prov = JSON.parse(fs.readFileSync(provPath, 'utf8'));
      assert.equal(prov.upstream.repository, 'https://github.com/nextlevelbuilder/ui-ux-pro-max-skill');
      assert.equal(prov.upstream.tag, 'v2.9.0');
      assert.equal(prov.upstream.commit, '65e23199492fa911af32d9078e627ab4de01f4c8');
      assert.equal(prov.upstream.license, 'MIT');
      assert.equal(prov.adaptation.mode, 'search-only');
    }
  });

  test('Criterion 9: MIT copyright and permission notice is retained for Next Level Builder', () => {
    const sourceLicensePath = path.join(REPO_ROOT, 'skills', 'ask-impeccable', 'research', 'LICENSE-UPSTREAM.txt');
    const installedLicensePath = path.join(installedSkillDir, 'research', 'LICENSE-UPSTREAM.txt');

    assert.ok(fs.existsSync(sourceLicensePath), 'Source LICENSE-UPSTREAM.txt must exist');
    assert.ok(fs.existsSync(installedLicensePath), 'Installed LICENSE-UPSTREAM.txt must exist');

    for (const licPath of [sourceLicensePath, installedLicensePath]) {
      const content = fs.readFileSync(licPath, 'utf8');
      assert.match(content, /MIT License/);
      assert.match(content, /Copyright \(c\) 2024 Next Level Builder/);
      assert.match(content, /Permission is hereby granted, free of charge/);
    }
  });
});
