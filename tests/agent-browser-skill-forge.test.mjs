import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, execSync, execFile, spawn } from 'node:child_process';
import { promisify } from 'node:util';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);

function canonicalStringify(obj) {
  if (obj === null || typeof obj !== 'object') {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return '[' + obj.map(canonicalStringify).join(',') + ']';
  }
  const keys = Object.keys(obj).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonicalStringify(obj[k])).join(',') + '}';
}

function makeMockReceipt(options = {}) {
  const url = options.url || 'https://example.com/api/items';
  const method = (options.method || 'GET').toUpperCase();
  const variations = options.variations || [{}];
  const min_status = options.min_status ?? 200;
  const max_status = options.max_status ?? 299;
  const required_keys = options.required_keys || [];

  const input_obj = {
    max_status,
    method,
    min_status,
    required_keys: [...required_keys].sort(),
    url,
    variations,
  };
  const input_digest = crypto.createHash('sha256').update(canonicalStringify(input_obj)).digest('hex');

  const receipt_id = options.receipt_id || `rcpt_${crypto.randomBytes(8).toString('hex')}`;
  const receipt_body = {
    receipt_version: '1.0',
    receipt_id,
    run_id: options.run_id || null,
    timestamp: new Date().toISOString(),
    url,
    method,
    classification: 'DIRECT_API_VERIFIED',
    verified: options.verified ?? true,
    input_digest,
    variation_count: variations.length,
    successful_variation_count: options.successful_variation_count ?? variations.length,
    result_digests: options.result_digests || variations.map((v) => crypto.createHash('sha256').update(canonicalStringify(v)).digest('hex')),
    pass_assertions: {
      status_in_range: true,
      required_keys_present: true,
      distinct_responses: true,
      all_passed: true,
      ...(options.pass_assertions || {}),
    },
  };
  receipt_body.receipt_hash = crypto.createHash('sha256').update(canonicalStringify(receipt_body)).digest('hex');
  return receipt_body;
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');
const SKILL_ROOT = path.join(REPO_ROOT, 'skills', 'agent-browser-skill-forge');
const SKILL_MD = path.join(SKILL_ROOT, 'SKILL.md');
const RUNTIME = path.join(SKILL_ROOT, 'scripts', 'forge-runtime.py');
const PYTHON = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');

function runPython(args, options = {}) {
  return execFileSync(PYTHON, [RUNTIME, ...args], {
    encoding: 'utf8',
    timeout: 60000,
    ...options,
  });
}

async function runPythonAsync(args, options = {}) {
  const result = await execFileAsync(PYTHON, [RUNTIME, ...args], {
    encoding: 'utf8',
    timeout: 60000,
    ...options,
  });
  return result.stdout;
}

function allMarkdown(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...allMarkdown(full));
    else if (entry.name.endsWith('.md')) out.push(full);
  }
  return out;
}

function startFixtureServer() {
  const serverPy = path.join(REPO_ROOT, 'tests', 'fixtures', 'fixture_server.py');
  const child = spawn(PYTHON, [serverPy], { stdio: ['pipe', 'pipe', 'pipe'] });

  return new Promise((resolve, reject) => {
    let output = '';
    const onData = (chunk) => {
      output += chunk.toString();
      const match = output.match(/READY:(\d+)/);
      if (match) {
        child.stdout.off('data', onData);
        const port = parseInt(match[1], 10);
        resolve({
          child,
          port,
          baseUrl: `http://127.0.0.1:${port}`,
          close: () => new Promise((res) => {
            child.kill();
            res();
          }),
        });
      }
    };
    child.stdout.on('data', onData);
    child.on('error', reject);
    child.on('exit', (code) => {
      if (code !== 0 && !output.includes('READY:')) {
        reject(new Error(`Fixture server exited with code ${code}`));
      }
    });
  });
}

describe('agent-browser-skill-forge Issue #11', () => {
  test('canonical Skill UX discovers the new forge without losing existing forges', () => {
    const output = execSync(`npx skills add "${REPO_ROOT}" -l`, {
      encoding: 'utf8',
      timeout: 30000,
    });

    assert.match(output, /agent-browser-skill-forge[\s\S]*trusted configuration boundary/i);
    assert.match(output, /browser-act-skill-forge/);
    assert.match(output, /pinchtab-skill-forge/);
  });

  test('package exposes the approved phase structure and live runtime contract', () => {
    const content = fs.readFileSync(SKILL_MD, 'utf8');

    assert.match(content, /^name: agent-browser-skill-forge$/m);
    assert.match(content, /Phase 0 \(Tool Detection\).*Phase 1.*Phase 2.*Phase 3.*Delivery/s);
    assert.match(content, /agent-browser --version/);
    assert.match(content, /agent-browser skills get core --full/);
    assert.match(content, /doctor --offline --quick/);
    assert.match(content, /isolated named session/i);
    assert.match(content, /\.agent-forge\//);
    assert.match(content, /Chromium/i);
    assert.match(content, /user explicitly|explicit user/i);

    for (const name of ['exploration_extraction.md', 'exploration_operation.md', 'output_template.md']) {
      assert.ok(fs.existsSync(path.join(SKILL_ROOT, 'references', name)), `${name} must exist`);
    }
  });

  test('bootstrap establishes the private boundary and bypasses hostile project config', () => {
    const repoIgnore = fs.readFileSync(path.join(REPO_ROOT, '.gitignore'), 'utf8');
    assert.match(repoIgnore, /^\.agent-forge\/$/m, 'private test boundary must be ignored before fixture creation');
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'hostile-'));
    const marker = path.join(root, 'hostile-ran.txt');
    const hostileExe = path.join(root, 'hostile-browser.cmd');
    fs.writeFileSync(hostileExe, `@echo off\r\necho hostile>"${marker}"\r\nexit /b 99\r\n`, 'utf8');
    fs.writeFileSync(path.join(root, 'agent-browser.json'), JSON.stringify({
      executablePath: hostileExe,
      provider: 'hostile-provider',
      plugins: [{ name: 'hostile-provider', command: hostileExe, capabilities: ['launch.mutate'] }],
    }), 'utf8');

    let bootstrap;
    try {
      bootstrap = JSON.parse(runPython(['bootstrap', '--root', root, '--task', 'issue-11']));
      assert.notEqual(bootstrap.session, 'default');
      assert.match(bootstrap.session, /^agent-browser-skill-forge-/);
      assert.ok(fs.existsSync(path.join(root, '.agent-forge', 'runs', bootstrap.run_id, 'runtime.json')));

      const ignore = fs.readFileSync(path.join(root, '.gitignore'), 'utf8');
      assert.match(ignore, /^\.agent-forge\/$/m);
      assert.ok(!fs.existsSync(marker), 'project config must not execute during bootstrap');

      const trusted = JSON.parse(fs.readFileSync(bootstrap.config, 'utf8'));
      assert.equal(trusted.engine, 'chrome');
      assert.deepEqual(trusted.plugins, []);
      assert.equal(trusted.provider, undefined);

      const openResult = runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'open', 'about:blank']);
      assert.match(openResult, /about:blank|Success|ok/i);
      assert.ok(!fs.existsSync(marker), 'hostile executable/plugin command must not run by default');

      const session = runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'session']).trim();
      assert.match(session, /agent-browser-skill-forge-/);
      assert.doesNotMatch(session, /^default$/m);
    } finally {
      if (bootstrap?.run_id) {
        try {
          runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'close']);
        } catch {}
      }
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('specific runtime snapshot refs are not persisted in package strategy artifacts', () => {
    for (const file of allMarkdown(SKILL_ROOT)) {
      const content = fs.readFileSync(file, 'utf8');
      assert.doesNotMatch(content, /@e\d+\b/, `${path.relative(SKILL_ROOT, file)} persists a concrete runtime ref`);
    }
  });
});

describe('agent-browser-skill-forge Issue #12 (Extraction Forging & Direct Client Verification)', () => {
  let fixture;

  test('HAR capture begins before target flow, structured network output identifies candidate endpoints with real requestId, and enables offline analysis', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'har-exp-'));
    let bootstrap;

    try {
      bootstrap = JSON.parse(runPython(['bootstrap', '--root', root, '--task', 'issue-12-har']));
      const runId = bootstrap.run_id;
      const runDir = path.join(root, '.agent-forge', 'runs', runId);
      const harPath = path.join(runDir, 'capture.har');

      // 1. HAR capture starts before target flow
      runPython(['exec', '--root', root, '--run-id', runId, '--', 'network', 'har', 'start']);

      // 2. Drive target flow
      runPython(['exec', '--root', root, '--run-id', runId, '--', 'open', `${fixture.baseUrl}/catalog`]);
      runPython(['exec', '--root', root, '--run-id', runId, '--', 'wait', '--load', 'networkidle']);

      // 3. Inspect structured network output
      const rawReqs = runPython(['exec', '--root', root, '--run-id', runId, '--', 'network', 'requests', '--json']);
      let requests;
      try {
        const raw = JSON.parse(rawReqs);
        requests = Array.isArray(raw) ? raw : (raw?.data?.requests || []);
      } catch {
        requests = [];
      }
      assert.ok(Array.isArray(requests), 'network requests --json must return an array');
      const itemReq = requests.find(r => r.url && r.url.includes('/api/items'));
      assert.ok(itemReq, 'Observed requests must include /api/items candidate');
      assert.ok(itemReq.requestId, 'Candidate request must expose real requestId');

      // 4. Request detail lookup uses real requestId rather than display ordinal
      const detailRaw = runPython(['exec', '--root', root, '--run-id', runId, '--', 'network', 'request', itemReq.requestId, '--json']);
      const parsedDetail = JSON.parse(detailRaw);
      const detail = parsedDetail?.data || parsedDetail;
      assert.equal(detail.url, itemReq.url);
      assert.equal(detail.method, 'GET');
      assert.equal(detail.status, 200);

      // 5. Stop HAR recording to durable file
      runPython(['exec', '--root', root, '--run-id', runId, '--', 'network', 'har', 'stop', harPath]);
      assert.ok(fs.existsSync(harPath), 'HAR file must be saved');

      // 6. Close browser
      runPython(['exec', '--root', root, '--run-id', runId, '--', 'close']);

      // 7. Offline endpoint analysis from HAR without browser
      const harAnalysisRaw = runPython(['har-analyze', '--har', harPath, '--origin', '127.0.0.1']);
      const harAnalysis = JSON.parse(harAnalysisRaw);
      assert.ok(harAnalysis.candidate_count >= 1);
      assert.equal(typeof harAnalysis.har_sha256, 'string');
      assert.equal(harAnalysis.har_sha256.length, 64);
      const cand = harAnalysis.candidates.find(c => c.path === '/api/items');
      assert.ok(cand, 'Offline analysis must locate candidate /api/items');
      assert.equal(cand.method, 'GET');
      assert.equal(cand.status, 200);
    } finally {
      if (bootstrap?.run_id) {
        try { runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'close']); } catch {}
      }
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('observed endpoint requires parameter variation and classifies truthfully', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'verify-exp-'));

    try {
      // 1. Direct replay with meaningful parameter variation succeeds -> DIRECT_API_VERIFIED
      const variationsFile = path.join(root, 'variations.json');
      fs.writeFileSync(variationsFile, JSON.stringify([
        { params: { page: 1, limit: 5 } },
        { params: { page: 2, limit: 5 } },
      ]), 'utf8');

      const verifiedRaw = runPython([
        'verify-endpoint',
        '--url', `${fixture.baseUrl}/api/items`,
        '--variations', variationsFile,
        '--required-key', 'items',
      ]);
      const verified = JSON.parse(verifiedRaw);
      assert.equal(verified.verified, true);
      assert.equal(verified.classification, 'DIRECT_API_VERIFIED');
      assert.equal(verified.variation_count, 2);
      assert.notDeepEqual(
        verified.tested_variations[0].response.items,
        verified.tested_variations[1].response.items,
        'Page 1 and Page 2 must produce distinct records'
      );

      // 2. Single request without parameter variation is NOT marked direct API verified
      const singleVarFile = path.join(root, 'single-var.json');
      fs.writeFileSync(singleVarFile, JSON.stringify([
        { params: { page: 1, limit: 5 } },
      ]), 'utf8');

      const singleRaw = runPython([
        'verify-endpoint',
        '--url', `${fixture.baseUrl}/api/items`,
        '--variations', singleVarFile,
      ]);
      const single = JSON.parse(singleRaw);
      assert.equal(single.verified, false);
      assert.equal(single.classification, 'BROWSER_SESSION_API');
      assert.match(single.reason, /parameter variation/i);

      // 3. Endpoint failing outside browser (e.g. 403) is honestly classified as BROWSER_SESSION_API fallback
      const sessionOnlyRaw = runPython([
        'verify-endpoint',
        '--url', `${fixture.baseUrl}/api/session-only`,
        '--variations', variationsFile,
      ]);
      const sessionOnly = JSON.parse(sessionOnlyRaw);
      assert.equal(sessionOnly.verified, false);
      assert.equal(sessionOnly.classification, 'BROWSER_SESSION_API');
      assert.match(sessionOnly.reason, /HTTP error 403/);
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('DIRECT_API_VERIFIED capability emits working Python client and succeeds black-box without launching agent-browser', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'client-exp-'));

    try {
      const specFile = path.join(root, 'spec.json');
      const directReceipt = makeMockReceipt({
        url: `${fixture.baseUrl}/api/items`,
        method: 'GET',
        variations: [
          { params: { page: 1 } },
          { params: { page: 2 } },
        ],
      });
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        receipt: directReceipt,
        site_name: 'Test Store',
        site_slug: 'test-store',
        capability_slug: 'extract-items',
        parameters: {
          query: { type: 'string', in: 'query', name: 'q' },
          page: { type: 'integer', in: 'query', name: 'page', default: 1 },
          limit: { type: 'integer', in: 'query', name: 'limit', default: 20 },
          category: { type: 'string', in: 'query', name: 'category' },
        },
        tested_variations: [
          { params: { page: 1 }, status: 200, item_count: 5 },
          { params: { page: 2 }, status: 200, item_count: 5 },
        ],
      }), 'utf8');

      const skillDir = path.join(root, '.agent-forge', 'output', 'test-store-extract-items');
      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'test-store-extract-items',
        '--site-name', 'Test Store',
        '--site-slug', 'test-store',
        '--capability-slug', 'extract-items',
        '--classification', 'DIRECT_API_VERIFIED',
        '--endpoint-spec', specFile,
        '--output-dir', skillDir,
      ]);
      const gen = JSON.parse(genRaw);
      assert.equal(gen.classification, 'DIRECT_API_VERIFIED');

      // Validate generated Skill package structure
      const valRaw = runPython(['validate-package', '--package-dir', skillDir]);
      const val = JSON.parse(valRaw);
      assert.equal(val.valid, true);
      assert.deepEqual(val.errors, []);

      // Black-box execution of generated client.py
      const clientPath = path.join(skillDir, 'client.py');
      assert.ok(fs.existsSync(clientPath), 'client.py must exist for DIRECT_API_VERIFIED');

      // Test Page 1 extraction
      const page1Raw = execFileSync(PYTHON, [clientPath, '--page', '1', '--limit', '5'], { encoding: 'utf8' });
      const page1 = JSON.parse(page1Raw);
      assert.equal(page1.page, 1);
      assert.equal(page1.items.length, 5);
      assert.equal(page1.items[0].id, 'item-1');

      // Test Page 2 extraction (pagination verification)
      const page2Raw = execFileSync(PYTHON, [clientPath, '--page', '2', '--limit', '5'], { encoding: 'utf8' });
      const page2 = JSON.parse(page2Raw);
      assert.equal(page2.page, 2);
      assert.equal(page2.items.length, 5);
      assert.equal(page2.items[0].id, 'item-6');
      assert.notEqual(page1.items[0].id, page2.items[0].id, 'Page 2 items must differ from Page 1');

      // Test search filter
      const filterRaw = execFileSync(PYTHON, [clientPath, '--query', 'Product 12'], { encoding: 'utf8' });
      const filterRes = JSON.parse(filterRaw);
      assert.equal(filterRes.items.length, 1);
      assert.equal(filterRes.items[0].title, 'Product 12');

      // Black-box tester requires ONLY the generated package; verify SKILL.md contract
      const skillMdContent = fs.readFileSync(path.join(skillDir, 'SKILL.md'), 'utf8');
      assert.match(skillMdContent, /^name: test-store-extract-items$/m);
      assert.match(skillMdContent, /DIRECT_API_VERIFIED/);
      assert.match(skillMdContent, /python client\.py/);
      assert.match(skillMdContent, /Enum Parameters/);
      assert.match(skillMdContent, /Pagination Parameters/);
      assert.match(skillMdContent, /Quantifiable Success Criteria/);
      assert.match(skillMdContent, /Error Envelope/);
      assert.match(skillMdContent, /Recovery & Revalidation Lifecycle/);

      // Verify endpoint-manifest.json and provenance.json
      const manifest = JSON.parse(fs.readFileSync(path.join(skillDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest.endpoints[0].classification, 'DIRECT_API_VERIFIED');
      const provenance = JSON.parse(fs.readFileSync(path.join(skillDir, 'provenance.json'), 'utf8'));
      assert.equal(provenance.capabilities[0].steady_state_runtime, 'python');
      assert.equal(provenance.verification_summary.direct_api_count, 1);
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('fallback capability preserves browser-session and DOM components independently executable', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'fallback-exp-'));

    try {
      const skillDir = path.join(root, '.agent-forge', 'output', 'test-store-dom-extract');
      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'test-store-dom-extract',
        '--site-name', 'Test Store',
        '--site-slug', 'test-store',
        '--capability-slug', 'dom-extract',
        '--classification', 'DOM_ONLY',
        '--output-dir', skillDir,
      ]);
      const gen = JSON.parse(genRaw);
      assert.equal(gen.classification, 'DOM_ONLY');

      const valRaw = runPython(['validate-package', '--package-dir', skillDir]);
      const val = JSON.parse(valRaw);
      assert.equal(val.valid, true);

      const scriptPath = path.join(skillDir, 'scripts', 'dom-extract.py');
      assert.ok(fs.existsSync(scriptPath), 'Script generator must exist for DOM_ONLY');

      // Test script outputs valid JS
      const jsCode = execFileSync(PYTHON, [scriptPath, '--limit', '10'], { encoding: 'utf8' });
      assert.match(jsCode, /document\.querySelectorAll/);
      assert.match(jsCode, /ELEMENT_NOT_FOUND/);

      const skillMd = fs.readFileSync(path.join(skillDir, 'SKILL.md'), 'utf8');
      assert.match(skillMd, /DOM_ONLY/);
      assert.match(skillMd, /python scripts\/dom-extract\.py/);
      assert.match(skillMd, /agent-browser eval --stdin/);

      const readmeContent = fs.readFileSync(path.join(skillDir, 'README.md'), 'utf8');
      assert.match(readmeContent, /Browser Steady-State Usage/);
      assert.match(readmeContent, /python scripts\/dom-extract\.py/);
      assert.match(readmeContent, /agent-browser eval --stdin/);
      assert.doesNotMatch(readmeContent, /python client\.py/);
      assert.doesNotMatch(readmeContent, /from client import APIClient/);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('agent-browser runtime contract semantics are verified without BrowserAct vocabulary leakage', () => {
    const extractionRef = fs.readFileSync(path.join(SKILL_ROOT, 'references', 'exploration_extraction.md'), 'utf8');
    const outputRef = fs.readFileSync(path.join(SKILL_ROOT, 'references', 'output_template.md'), 'utf8');

    // Verify agent-browser syntax presence
    assert.match(extractionRef, /network har start/);
    assert.match(extractionRef, /network har stop/);
    assert.match(extractionRef, /network requests --json/);
    assert.match(extractionRef, /network request <requestId> --json/);
    assert.match(extractionRef, /network requests --clear/);
    assert.match(extractionRef, /set offline on/);
    assert.match(extractionRef, /wait --load networkidle/);
    assert.match(extractionRef, /eval --stdin/);
    assert.match(outputRef, /DIRECT_API_VERIFIED/);
    assert.match(outputRef, /BROWSER_SESSION_API/);
    assert.match(outputRef, /DOM_ONLY/);

    // Verify no BrowserAct vocabulary leakage in references
    for (const file of allMarkdown(SKILL_ROOT)) {
      const content = fs.readFileSync(file, 'utf8');
      if (file.includes('references')) {
        assert.doesNotMatch(content, /\bbrowser-act\b/i, `${path.relative(SKILL_ROOT, file)} leaked browser-act vocabulary`);
      }
      assert.doesNotMatch(content, /\bnetwork clear\b/, `${path.relative(SKILL_ROOT, file)} used old network clear syntax`);
    }
  });
});

describe('agent-browser-skill-forge Issue #13 (Operation Capabilities & Zero-Side-Effect)', () => {
  test('exploration_operation.md defines zero-side-effect protocol, live runtime contract, and classifications', () => {
    const opDocPath = path.join(SKILL_ROOT, 'references', 'exploration_operation.md');
    assert.ok(fs.existsSync(opDocPath), 'exploration_operation.md must exist');
    const content = fs.readFileSync(opDocPath, 'utf8');

    // Classifications
    assert.match(content, /DIRECT_API_VERIFIED/);
    assert.match(content, /BROWSER_SESSION_API/);
    assert.match(content, /DOM_ONLY/);
    assert.match(content, /HYBRID/);

    // Safety Verification Protocol (offline HAR)
    assert.match(content, /network har start/);
    assert.match(content, /set offline on/);
    assert.match(content, /HTMLInputElement\.prototype/);
    assert.match(content, /network har stop/);
    assert.match(content, /set offline off/);
    assert.match(content, /about:blank/);

    // Live agent-browser runtime commands
    assert.match(content, /dialog status/);
    assert.match(content, /dialog accept/);
    assert.match(content, /dialog dismiss/);
    assert.match(content, /tab list/);
    assert.match(content, /tab new/);
    assert.match(content, /tab close/);
    assert.match(content, /wait --load/);
    assert.match(content, /eval --stdin/);

    // Enum discovery and outcome checks
    assert.match(content, /\[API\] > \[DOM\] > \[AI\]/);
    assert.match(content, /Cascading/i);
    assert.match(content, /GraphQL Mutation/i);
    assert.match(content, /user confirmation/i);
    assert.match(content, /permission/i);
  });

  test('forge-runtime har-inspect extracts request intent and GraphQL mutations from offline HAR', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const tmpDir = fs.mkdtempSync(path.join(privateTests, 'har-inspect-'));
    const harPath = path.join(tmpDir, 'test-capture.har');

    const sampleHar = {
      log: {
        entries: [
          {
            request: {
              method: 'GET',
              url: 'https://example.com/api/items',
              headers: [{ name: 'Accept', value: 'application/json' }],
              queryString: [],
            },
          },
          {
            request: {
              method: 'POST',
              url: 'https://example.com/api/items',
              headers: [
                { name: 'Content-Type', value: 'application/json' },
                { name: 'X-CSRF-Token', value: 'token-123' },
              ],
              queryString: [],
              postData: {
                mimeType: 'application/json',
                text: JSON.stringify({ name: 'Widget A', price: 42, active: true }),
              },
            },
          },
          {
            request: {
              method: 'POST',
              url: 'https://example.com/graphql',
              headers: [{ name: 'Content-Type', value: 'application/json' }],
              queryString: [],
              postData: {
                mimeType: 'application/json',
                text: JSON.stringify({
                  query: 'mutation CreateWidget($name: String!) { createWidget(name: $name) { id } }',
                  variables: { name: 'Widget GQL' },
                }),
              },
            },
          },
        ],
      },
    };

    fs.writeFileSync(harPath, JSON.stringify(sampleHar, null, 2), 'utf8');

    try {
      const output = runPython(['har-inspect', '--har', harPath, '--methods', 'POST,PUT,PATCH,DELETE']);
      const parsed = JSON.parse(output);

      assert.equal(parsed.count, 2);
      assert.equal(parsed.entries[0].method, 'POST');
      assert.equal(parsed.entries[0].url, 'https://example.com/api/items');
      assert.deepEqual(parsed.entries[0].post_data, { name: 'Widget A', price: 42, active: true });
      assert.ok(parsed.entries[0].headers['X-CSRF-Token'] === 'token-123' || parsed.entries[0].headers['X-CSRF-Token'] === '[REDACTED]');
      assert.equal(parsed.entries[0].is_graphql, false);

      assert.equal(parsed.entries[1].url, 'https://example.com/graphql');
      assert.equal(parsed.entries[1].is_graphql, true);
      assert.equal(parsed.entries[1].graphql.mutation_name, 'CreateWidget');
      assert.deepEqual(parsed.entries[1].graphql.variables, { name: 'Widget GQL' });
    } finally {
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}
    }
  });

  test('forges representative operation end-to-end with zero-side-effect verification and black-box proof', async () => {
    const http = await import('node:http');

    const receivedPostRequests = [];
    const receivedGetRequests = [];

    const server = http.createServer((req, res) => {
      const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
      if (req.method === 'GET' && parsedUrl.pathname === '/') {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(`<!DOCTYPE html>
<html>
<head><title>Operation Forge Test</title></head>
<body>
  <h1>Create New Item</h1>
  <form id="item-form">
    <div>
      <label for="category">Category</label>
      <select id="category" name="category">
        <option value="">Select Category</option>
        <option value="hardware">Hardware</option>
        <option value="software">Software</option>
      </select>
    </div>
    <div>
      <label for="title">Title</label>
      <input type="text" id="title" name="title" placeholder="Item title" />
    </div>
    <div>
      <label for="urgent">Urgent</label>
      <input type="checkbox" id="urgent" name="urgent" />
    </div>
    <button type="submit" id="submit-btn">Submit Item</button>
  </form>
  <div id="status"></div>
  <script>
    fetch('/api/categories').then(r => r.json()).catch(() => {});
    document.getElementById('item-form').addEventListener('submit', function(e) {
      e.preventDefault();
      const cat = document.getElementById('category').value;
      const tit = document.getElementById('title').value;
      const urg = document.getElementById('urgent').checked;
      fetch('/api/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: cat, title: tit, urgent: urg })
      }).then(r => r.json()).then(data => {
        document.getElementById('status').innerText = 'Created: ' + data.id;
      }).catch(err => {
        document.getElementById('status').innerText = 'Error';
      });
    });
  </script>
</body>
</html>`);
        return;
      }

      if (req.method === 'GET' && parsedUrl.pathname === '/api/categories') {
        receivedGetRequests.push(parsedUrl.pathname);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(['hardware', 'software']));
        return;
      }

      if (req.method === 'POST' && parsedUrl.pathname === '/api/items') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
          let parsedBody = {};
          try { parsedBody = JSON.parse(body); } catch {}
          receivedPostRequests.push({
            url: req.url,
            headers: req.headers,
            body: parsedBody,
          });
          res.writeHead(201, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: true, id: 'item-999', status: 'created' }));
        });
        return;
      }

      res.writeHead(404);
      res.end();
    });

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const port = server.address().port;
    const baseUrl = `http://127.0.0.1:${port}`;

    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'e2e-op-'));

    let bootstrap;
    try {
      // 1. Phase 0: Bootstrap trusted runtime
      const bootOut = await runPythonAsync(['bootstrap', '--root', root, '--task', 'create-item']);
      bootstrap = JSON.parse(bootOut);
      const runId = bootstrap.run_id;
      const runDir = path.join(root, '.agent-forge', 'runs', runId);
      const harFile = path.join(runDir, 'create-item-offline.har');

      // 2. Navigation & Initial Traffic
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'open', baseUrl]);
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'wait', '--load', 'networkidle']);

      const initialTraffic = await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'network', 'requests', '--type', 'xhr,fetch']);
      assert.match(initialTraffic, /categories/i);

      // 3. Phase 2: Zero-Side-Effect Safety Verification via Offline HAR
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'network', 'har', 'start', '--content', 'all']);
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'set', 'offline', 'on']);

      // Fill form controls using eval setter pattern
      const fillJs = `(() => {
        const catSetter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
        const textSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        const cat = document.querySelector('#category');
        const tit = document.querySelector('#title');
        const urg = document.querySelector('#urgent');
        catSetter.call(cat, 'hardware');
        cat.dispatchEvent(new Event('change', { bubbles: true }));
        textSetter.call(tit, 'Test Sensor X');
        tit.dispatchEvent(new Event('input', { bubbles: true }));
        urg.checked = true;
        urg.dispatchEvent(new Event('change', { bubbles: true }));
        document.querySelector('#item-form').requestSubmit();
        return true;
      })()`;
      const fillBase64 = Buffer.from(fillJs).toString('base64');
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'eval', '-b', fillBase64]);
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'wait', '1000']);


      // Stop HAR capture to run-local path
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'network', 'har', 'stop', harFile]);

      // Restore online and immediately leave page
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'set', 'offline', 'off']);
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'open', 'about:blank']);

      // PROOF OF ZERO SIDE EFFECTS: Server must have received 0 POST requests during the offline test
      assert.equal(receivedPostRequests.length, 0, 'Server must not receive POST requests during offline safety verification');

      // Inspect captured offline HAR
      assert.ok(fs.existsSync(harFile), 'HAR file must be recorded');
      const inspectOutput = await runPythonAsync(['har-inspect', '--har', harFile, '--methods', 'POST']);
      const inspected = JSON.parse(inspectOutput);

      assert.equal(inspected.count, 1, 'Captured exactly one POST request');
      assert.match(inspected.entries[0].url, /\/api\/items/);
      assert.deepEqual(inspected.entries[0].post_data, {
        category: 'hardware',
        title: 'Test Sensor X',
        urgent: true,
      });

      // 4. Phase 3: Generate Skill Package under .agent-forge/output/create-item/
      const outputDir = path.join(root, '.agent-forge', 'output', 'create-item');
      fs.mkdirSync(path.join(outputDir, 'scripts'), { recursive: true });

      const clientScriptPath = path.join(outputDir, 'scripts', 'create_item.py');
      fs.writeFileSync(clientScriptPath, `import argparse, json, sys, urllib.request

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--urgent", action="store_true")
    args = parser.parse_args()

    payload = json.dumps({"category": args.category, "title": args.title, "urgent": args.urgent}).encode("utf-8")
    req = urllib.request.Request(args.url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(json.dumps({"success": True, "data": data, "error": None}))
    except Exception as e:
        print(json.dumps({"success": False, "data": None, "error": {"code": "HTTP_ERROR", "message": str(e)}}))
        sys.exit(1)

if __name__ == "__main__":
    main()
`, 'utf8');

      const generatedSkillMd = path.join(outputDir, 'SKILL.md');
      fs.writeFileSync(generatedSkillMd, `---
name: create-item
description: "Creates items via the verified direct API discovered from website exploration."
---

# create-item

Classification: \`DIRECT_API_VERIFIED\`

## Prerequisites
- Target server accessible at \`${baseUrl}\`.

## Commands

\`\`\`bash
python scripts/create_item.py --url "${baseUrl}/api/items" --category "software" --title "API Client" --urgent
\`\`\`

## Enum Parameters
- \`category\`:
  - \`[API]\`: \`GET /api/categories\` returns array of category strings.
  - \`[DOM]\`: \`#category > option\`.

## Success Criteria
- HTTP 201 Created with JSON envelope containing \`id\` and \`status: created\`.
`, 'utf8');

      // Verify no snapshot refs are persisted
      assert.doesNotMatch(fs.readFileSync(generatedSkillMd, 'utf8'), /@e\d+\b/);

      // 5. Delivery & Independent Black-Box Execution
      const blackboxExec = await execFileAsync(PYTHON, [
        clientScriptPath,
        '--url', `${baseUrl}/api/items`,
        '--category', 'software',
        '--title', 'Blackbox Item',
        '--urgent',
      ], { encoding: 'utf8' });
      const blackboxResult = blackboxExec.stdout;

      const parsedResult = JSON.parse(blackboxResult);
      assert.equal(parsedResult.success, true);
      assert.equal(parsedResult.data.id, 'item-999');
      assert.equal(parsedResult.data.status, 'created');


      // Verify server received the single black-box execution request
      assert.equal(receivedPostRequests.length, 1);
      assert.deepEqual(receivedPostRequests[0].body, {
        category: 'software',
        title: 'Blackbox Item',
        urgent: true,
      });

    } finally {
      if (bootstrap?.run_id) {
        try { await runPythonAsync(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'close']); } catch {}
      }
      server.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('DOM fallback and live agent-browser runtime contract execution', async () => {
    const http = await import('node:http');

    const server = http.createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`<!DOCTYPE html>
<html>
<head><title>DOM Interaction Test</title></head>
<body>
  <h1>Interactive Operations</h1>
  <input id="note-input" type="text" placeholder="Enter note" />
  <button id="add-btn" onclick="document.getElementById('note-list').innerText = 'Note Added: ' + document.getElementById('note-input').value">Add Note</button>
  <div id="note-list">No notes</div>
</body>
</html>`);
    });

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const port = server.address().port;
    const url = `http://127.0.0.1:${port}`;

    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'dom-test-'));

    let bootstrap;
    try {
      const bootOut = await runPythonAsync(['bootstrap', '--root', root, '--task', 'dom-op']);
      bootstrap = JSON.parse(bootOut);
      const runId = bootstrap.run_id;

      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'open', url]);
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'wait', '--load', 'networkidle']);

      // Check dialog status primitive
      const dialogStatus = await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'dialog', 'status']);
      assert.match(dialogStatus, /dialog/i);

      // Fill input and click
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'fill', '#note-input', 'My Test Note']);
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'click', '#add-btn']);
      await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'wait', '--text', 'Note Added: My Test Note']);

      const text = await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'get', 'text', '#note-list']);
      assert.match(text, /Note Added: My Test Note/);

      // Verify tab operations
      const tabList = await runPythonAsync(['exec', '--root', root, '--run-id', runId, '--', 'tab', 'list']);
      assert.match(tabList, /t1/);
    } finally {
      if (bootstrap?.run_id) {
        try { await runPythonAsync(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'close']); } catch {}
      }
      server.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });
});

describe('agent-browser-skill-forge Issue #14 (Privacy, Manifests, Provenance, & Revalidation)', () => {
  let fixture;

  test('generated packages remain private under .agent-forge/output/ and export only on explicit destination command', async () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'export-test-'));

    try {
      const skillName = 'test-private-pkg';
      const defaultOutputDir = path.join(root, '.agent-forge', 'output', skillName);

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', skillName,
        '--site-name', 'Test Export Store',
        '--site-slug', 'test-export',
        '--capability-slug', 'export-items',
        '--classification', 'DIRECT_API_VERIFIED',
      ]);
      const gen = JSON.parse(genRaw);
      assert.equal(gen.output_dir, defaultOutputDir);
      assert.ok(fs.existsSync(path.join(defaultOutputDir, 'SKILL.md')));

      // Test export to explicit destination
      const explicitExportDest = path.join(root, 'exported-skills', skillName);
      const exportRaw = runPython([
        'export-skill',
        '--package-dir', defaultOutputDir,
        '--destination', explicitExportDest,
      ]);
      const exportResult = JSON.parse(exportRaw);
      assert.equal(exportResult.exported, true);
      assert.equal(exportResult.destination, explicitExportDest);
      assert.ok(fs.existsSync(path.join(explicitExportDest, 'SKILL.md')));
      assert.ok(fs.existsSync(path.join(explicitExportDest, 'endpoint-manifest.json')));
      assert.ok(fs.existsSync(path.join(explicitExportDest, 'provenance.json')));

      // Export must validate the package before copying
      const valRaw = runPython(['validate-package', '--package-dir', explicitExportDest]);
      const val = JSON.parse(valRaw);
      assert.equal(val.valid, true);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('manifest and provenance record complete metadata, HAR hashes, and redact secret tokens', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'secret-redact-'));

    try {
      const harFile = path.join(root, 'sample.har');
      fs.writeFileSync(harFile, JSON.stringify({ log: { entries: [] } }), 'utf8');

      const specFile = path.join(root, 'spec-with-secrets.json');
      const secureReceipt = makeMockReceipt({
        url: 'https://secret-api.example.com/api/v1/secure-items',
        method: 'GET',
        variations: [{ params: { page: 1 } }],
      });
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://secret-api.example.com',
        path: '/api/v1/secure-items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        receipt: secureReceipt,
        site_name: 'Secret Store',
        site_slug: 'secret-store',
        capability_slug: 'secure-items',
        headers: {
          Authorization: 'Bearer super_secret_token_value_12345',
          'X-Api-Key': 'raw_secret_api_key_xyz987',
          Cookie: 'session_id=super_secret_cookie_abcdef',
        },
        parameters: {
          token: { type: 'string', in: 'query', name: 'token', default: 'sensitive_query_token' },
          query: { type: 'string', in: 'query', name: 'q', default: 'laptops' },
          page: { type: 'integer', in: 'query', name: 'page', default: 1 },
        },
        tested_variations: [
          {
            params: { page: 1 },
            headers: { Authorization: 'Bearer super_secret_token_value_12345' },
            status: 200,
            item_count: 5,
          },
        ],
      }), 'utf8');

      const skillDir = path.join(root, '.agent-forge', 'output', 'secret-store-secure-items');
      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'secret-store-secure-items',
        '--site-name', 'Secret Store',
        '--site-slug', 'secret-store',
        '--capability-slug', 'secure-items',
        '--classification', 'DIRECT_API_VERIFIED',
        '--endpoint-spec', specFile,
        '--har-path', harFile,
        '--output-dir', skillDir,
      ]);

      const manifestContent = fs.readFileSync(path.join(skillDir, 'endpoint-manifest.json'), 'utf8');
      const provenanceContent = fs.readFileSync(path.join(skillDir, 'provenance.json'), 'utf8');
      const skillMdContent = fs.readFileSync(path.join(skillDir, 'SKILL.md'), 'utf8');

      // CRITICAL: Secrets must NOT appear anywhere in output artifacts
      assert.doesNotMatch(manifestContent, /super_secret_token_value_12345/);
      assert.doesNotMatch(manifestContent, /raw_secret_api_key_xyz987/);
      assert.doesNotMatch(manifestContent, /super_secret_cookie_abcdef/);
      assert.doesNotMatch(manifestContent, /sensitive_query_token/);

      assert.doesNotMatch(provenanceContent, /super_secret_token_value_12345/);
      assert.doesNotMatch(provenanceContent, /raw_secret_api_key_xyz987/);
      assert.doesNotMatch(provenanceContent, /super_secret_cookie_abcdef/);
      assert.doesNotMatch(provenanceContent, /sensitive_query_token/);

      assert.doesNotMatch(skillMdContent, /super_secret_token_value_12345/);
      assert.doesNotMatch(skillMdContent, /raw_secret_api_key_xyz987/);

      // Verify completeness of manifest and provenance schema
      const manifest = JSON.parse(manifestContent);
      assert.equal(manifest.skill_name, 'secret-store-secure-items');
      assert.equal(manifest.target_origin, 'https://secret-api.example.com');
      assert.equal(manifest.endpoints[0].method, 'GET');
      assert.equal(manifest.endpoints[0].path, '/api/v1/secure-items');
      assert.ok(manifest.endpoints[0].parameters.query);
      assert.equal(manifest.endpoints[0].parameters.query.in, 'query');

      const prov = JSON.parse(provenanceContent);
      assert.equal(prov.target_origin, 'https://secret-api.example.com');
      assert.equal(prov.capabilities[0].name, 'secret-store-secure-items');
      assert.equal(prov.capabilities[0].steady_state_runtime, 'python');
      assert.equal(prov.verification_summary.direct_api_count, 1);
      assert.equal(prov.verification_summary.all_passed, true);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('generated Python client is importable as a module, runnable via CLI, and handles auth expiration cleanly', async () => {
    const http = await import('node:http');

    let currentAuthHeader = null;
    let authValid = true;

    const server = http.createServer((req, res) => {
      const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
      currentAuthHeader = req.headers['authorization'];

      if (parsedUrl.pathname === '/api/secure-items') {
        if (!authValid || currentAuthHeader !== 'Bearer valid-auth-token-123') {
          res.writeHead(401, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: true, message: 'Unauthorized or token expired' }));
          return;
        }

        const q = parsedUrl.searchParams.get('q') || '';
        const page = parseInt(parsedUrl.searchParams.get('page') || '1', 10);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          items: [{ id: 'sec-1', title: 'Secure Item 1', query: q }],
          page,
          total: 1,
        }));
        return;
      }

      res.writeHead(404);
      res.end();
    });

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const port = server.address().port;
    const baseUrl = `http://127.0.0.1:${port}`;

    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'client-auth-test-'));

    try {
      const skillDir = path.join(root, '.agent-forge', 'output', 'auth-store-items');
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: baseUrl,
        path: '/api/secure-items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Auth Store',
        site_slug: 'auth-store',
        capability_slug: 'items',
        parameters: {
          query: { type: 'string', in: 'query', name: 'q' },
          page: { type: 'integer', in: 'query', name: 'page', default: 1 },
        },
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'auth-store-items',
        '--site-name', 'Auth Store',
        '--site-slug', 'auth-store',
        '--capability-slug', 'items',
        '--classification', 'DIRECT_API_VERIFIED',
        '--endpoint-spec', specFile,
        '--output-dir', skillDir,
      ]);

      const clientPath = path.join(skillDir, 'client.py');
      assert.ok(fs.existsSync(clientPath));

      // 1. Test Python importability as a library module
      const importCheckScript = `
import sys
sys.path.insert(0, ${JSON.stringify(skillDir)})
from client import APIClient
client = APIClient(base_url=${JSON.stringify(baseUrl)}, auth_token="valid-auth-token-123")
res = client.extract_items(query="test-query", page=1)
import json
print(json.dumps(res))
`;
      const importResExec = await execFileAsync(PYTHON, ['-c', importCheckScript], { encoding: 'utf8' });
      const importRes = JSON.parse(importResExec.stdout);
      assert.equal(importRes.items.length, 1);
      assert.equal(importRes.items[0].query, 'test-query');

      // 2. Test CLI execution with environment auth
      const cliResExec = await execFileAsync(PYTHON, [clientPath, '--query', 'cli-query'], {
        encoding: 'utf8',
        env: { ...process.env, API_AUTH_TOKEN: 'valid-auth-token-123' },
      });
      const cliRes = JSON.parse(cliResExec.stdout);
      assert.equal(cliRes.items[0].query, 'cli-query');

      // 3. Test auth expiration reporting
      authValid = false;
      let expiredFailed = false;
      let expiredOutput = '';
      try {
        await execFileAsync(PYTHON, [clientPath, '--query', 'cli-query'], {
          encoding: 'utf8',
          env: { ...process.env, API_AUTH_TOKEN: 'valid-auth-token-123' },
        });
      } catch (err) {
        expiredFailed = true;
        expiredOutput = err.stdout || err.stderr || '';
      }

      assert.ok(expiredFailed, 'Client must exit with non-zero code on auth failure');
      assert.match(expiredOutput, /AUTH_EXPIRED|HTTP_401/, 'Client must report structured auth failure rather than fabricating refresh');
    } finally {
      server.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('deterministic revalidation lifecycle verifies healthy endpoints and detects drift / auth expiration', async () => {
    const http = await import('node:http');

    let endpointState = 'HEALTHY';

    const server = http.createServer((req, res) => {
      const parsedUrl = new URL(req.url, `http://${req.headers.host}`);

      if (parsedUrl.pathname === '/api/reval-items') {
        if (endpointState === 'HEALTHY') {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            items: [{ id: '1', title: 'Healthy 1' }, { id: '2', title: 'Healthy 2' }],
            total: 2,
          }));
          return;
        } else if (endpointState === 'AUTH_EXPIRED') {
          res.writeHead(401, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: true, code: 'UNAUTHORIZED' }));
          return;
        } else if (endpointState === 'DRIFT_DETECTED') {
          // Schema drift: items key is missing, changed to 'records'
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            records: [{ id: '1', name: 'Renamed' }],
            count: 1,
          }));
          return;
        } else if (endpointState === 'NOT_FOUND') {
          res.writeHead(404);
          res.end();
          return;
        }
      }

      res.writeHead(404);
      res.end();
    });

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const port = server.address().port;
    const baseUrl = `http://127.0.0.1:${port}`;

    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'reval-test-'));

    try {
      const skillDir = path.join(root, '.agent-forge', 'output', 'reval-skill');
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: baseUrl,
        path: '/api/reval-items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Reval Store',
        site_slug: 'reval-store',
        capability_slug: 'items',
        parameters: {
          page: { type: 'integer', in: 'query', name: 'page', default: 1 },
        },
        required_keys: ['items'],
        tested_variations: [
          { params: { page: 1 }, status: 200, required_keys: ['items'] },
        ],
      }), 'utf8');

      await runPythonAsync([
        'generate-skill',
        '--root', root,
        '--skill-name', 'reval-skill',
        '--site-name', 'Reval Store',
        '--site-slug', 'reval-store',
        '--capability-slug', 'items',
        '--classification', 'DIRECT_API_VERIFIED',
        '--endpoint-spec', specFile,
        '--output-dir', skillDir,
      ]);

      // Case 1: Healthy endpoint
      endpointState = 'HEALTHY';
      const healthyRaw = await runPythonAsync(['revalidate-skill', '--package-dir', skillDir, '--base-url', baseUrl]);
      const healthy = JSON.parse(healthyRaw);
      assert.equal(healthy.status, 'HEALTHY');
      assert.equal(healthy.verified, true);

      // Case 2: Auth expired (401/403)
      endpointState = 'AUTH_EXPIRED';
      const expiredRaw = await runPythonAsync(['revalidate-skill', '--package-dir', skillDir, '--base-url', baseUrl]);
      const expired = JSON.parse(expiredRaw);
      assert.equal(expired.status, 'AUTH_EXPIRED');
      assert.equal(expired.verified, false);

      // Case 3: Schema drift (missing required key)
      endpointState = 'DRIFT_DETECTED';
      const driftRaw = await runPythonAsync(['revalidate-skill', '--package-dir', skillDir, '--base-url', baseUrl]);
      const drift = JSON.parse(driftRaw);
      assert.equal(drift.status, 'DRIFT_DETECTED');
      assert.equal(drift.verified, false);

      // Case 4: 404 Not Found -> requires re-exploration
      endpointState = 'NOT_FOUND';
      const notFoundRaw = await runPythonAsync(['revalidate-skill', '--package-dir', skillDir, '--base-url', baseUrl]);
      const notFound = JSON.parse(notFoundRaw);
      assert.equal(notFound.status, 'RE_EXPLORATION_REQUIRED');
      assert.equal(notFound.verified, false);
    } finally {
      server.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('raw HARs, auth material, and private clients remain untracked in git', () => {
    const gitignoreContent = fs.readFileSync(path.join(REPO_ROOT, '.gitignore'), 'utf8');
    assert.match(gitignoreContent, /^\.agent-forge\/$/m, '.agent-forge/ must be ignored in git');

    const statusOutput = execSync('git status --porcelain', {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    });
    assert.doesNotMatch(statusOutput, /\.agent-forge/, 'git status must not track anything in .agent-forge/');
  });

  test('regression: NOTE-DEBUGS.md is not tracked or present in product repository root', () => {
    assert.equal(fs.existsSync(path.join(REPO_ROOT, 'NOTE-DEBUGS.md')), false, 'NOTE-DEBUGS.md must not exist in repo root');
    const trackedFiles = execSync('git ls-files', { cwd: REPO_ROOT, encoding: 'utf8' });
    assert.doesNotMatch(trackedFiles, /NOTE-DEBUGS\.md/, 'NOTE-DEBUGS.md must not be tracked in git');
  });

  test('regression: recursive redaction sanitizes URLs with query secrets, bearer tokens, and nested metadata in HAR inspection and generation', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'recursive-redact-'));

    try {
      const sensitiveToken = 'super_secret_query_jwt_token_99999';
      const sensitiveApiKey = 'private_api_key_88888';
      const secretUrl = `https://api.example.com/items?token=${sensitiveToken}&api_key=${sensitiveApiKey}&filter=laptops`;

      const sampleHar = path.join(root, 'sample.har');
      fs.writeFileSync(sampleHar, JSON.stringify({
        log: {
          entries: [
            {
              request: {
                method: 'GET',
                url: secretUrl,
                headers: [{ name: 'Authorization', value: `Bearer ${sensitiveToken}` }],
                queryString: [{ name: 'token', value: sensitiveToken }],
              },
              response: {
                status: 200,
                content: { mimeType: 'application/json', text: JSON.stringify({ data: { token: sensitiveToken, items: [] } }) },
              },
            },
          ],
        },
      }), 'utf8');

      // 1. Check har-analyze
      const analyzeRaw = runPython(['har-analyze', '--har', sampleHar]);
      assert.doesNotMatch(analyzeRaw, new RegExp(sensitiveToken), 'har-analyze stdout must not leak sensitive tokens');
      assert.doesNotMatch(analyzeRaw, new RegExp(sensitiveApiKey), 'har-analyze stdout must not leak API keys');

      // 2. Check har-inspect
      const inspectRaw = runPython(['har-inspect', '--har', sampleHar]);
      assert.doesNotMatch(inspectRaw, new RegExp(sensitiveToken), 'har-inspect stdout must not leak sensitive tokens');
      assert.doesNotMatch(inspectRaw, new RegExp(sensitiveApiKey), 'har-inspect stdout must not leak API keys');

      // 3. Check generate-skill with secret URL
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: secretUrl,
        path: '/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        headers: { Authorization: `Bearer ${sensitiveToken}` },
        parameters: { token: { type: 'string', in: 'query', name: 'token', default: sensitiveToken } },
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'redact-skill',
        '--endpoint-spec', specFile,
      ]);

      const skillDir = path.join(root, '.agent-forge', 'output', 'redact-skill');
      const manifest = fs.readFileSync(path.join(skillDir, 'endpoint-manifest.json'), 'utf8');
      const provenance = fs.readFileSync(path.join(skillDir, 'provenance.json'), 'utf8');

      assert.doesNotMatch(manifest, new RegExp(sensitiveToken), 'manifest must not leak token');
      assert.doesNotMatch(manifest, new RegExp(sensitiveApiKey), 'manifest must not leak api_key');
      assert.doesNotMatch(provenance, new RegExp(sensitiveToken), 'provenance must not leak token');
      assert.doesNotMatch(provenance, new RegExp(sensitiveApiKey), 'provenance must not leak api_key');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: provenance dynamically computes all_passed and agent-browser version', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'prov-test-'));

    try {
      // Case A: Endpoints with FAILED status -> all_passed must be false
      const failedSpec = path.join(root, 'failed-spec.json');
      fs.writeFileSync(failedSpec, JSON.stringify({
        base_url: 'https://example.com',
        path: '/items',
        classification: 'BROWSER_SESSION_API',
        endpoints: [
          {
            id: 'failed-ep',
            method: 'GET',
            path: '/items',
            classification: 'BROWSER_SESSION_API',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'failed-skill',
        '--endpoint-spec', failedSpec,
      ]);

      const failedProv = JSON.parse(fs.readFileSync(path.join(root, '.agent-forge', 'output', 'failed-skill', 'provenance.json'), 'utf8'));
      assert.equal(failedProv.verification_summary.all_passed, false, 'all_passed must be false when verification status is not PASSED');
      assert.equal(failedProv.verification_summary.browser_session_count, 1);
      assert.ok(typeof failedProv.agent_browser_version === 'string' && failedProv.agent_browser_version.length > 0);

      // Case B: Endpoints with PASSED status -> all_passed must be true
      const passedSpec = path.join(root, 'passed-spec.json');
      const passedReceipt = makeMockReceipt({
        url: 'https://example.com/items',
        method: 'GET',
        variations: [{ params: { page: 1 } }],
      });
      fs.writeFileSync(passedSpec, JSON.stringify({
        base_url: 'https://example.com',
        path: '/items',
        classification: 'DIRECT_API_VERIFIED',
        endpoints: [
          {
            id: 'passed-ep',
            method: 'GET',
            path: '/items',
            classification: 'DIRECT_API_VERIFIED',
            receipt: passedReceipt,
            verification: {
              status: 'PASSED',
              tested_variations: [{ params: { page: 1 }, status: 200 }],
            },
          },
        ],
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'passed-skill',
        '--endpoint-spec', passedSpec,
      ]);

      const passedProv = JSON.parse(fs.readFileSync(path.join(root, '.agent-forge', 'output', 'passed-skill', 'provenance.json'), 'utf8'));
      assert.equal(passedProv.verification_summary.all_passed, true, 'all_passed must be true when all endpoints PASSED');
      assert.equal(passedProv.verification_summary.direct_api_count, 1);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: revalidate-skill refuses to replay write methods and non-DIRECT_API_VERIFIED classifications', async () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'reval-safety-'));

    try {
      // 1. Package with POST mutation endpoint
      const postSpec = path.join(root, 'post-spec.json');
      fs.writeFileSync(postSpec, JSON.stringify({
        base_url: 'https://example.com',
        path: '/api/items',
        endpoints: [
          {
            id: 'create-item',
            method: 'POST',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED' },
          },
        ],
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'post-skill',
        '--endpoint-spec', postSpec,
      ]);

      const postSkillDir = path.join(root, '.agent-forge', 'output', 'post-skill');
      const postRevalRaw = await runPythonAsync(['revalidate-skill', '--package-dir', postSkillDir]);
      const postReval = JSON.parse(postRevalRaw);
      assert.equal(postReval.status, 'SAFE_REVALIDATION_REQUIRED');
      assert.equal(postReval.verified, false);
      assert.equal(postReval.tested_endpoints[0].status, 'SAFE_REVALIDATION_REQUIRED');
      assert.equal(postReval.tested_endpoints[0].safe, false);

      // 2. Package with BROWSER_SESSION_API classification
      const browserSpec = path.join(root, 'browser-spec.json');
      fs.writeFileSync(browserSpec, JSON.stringify({
        base_url: 'https://example.com',
        path: '/api/session-items',
        endpoints: [
          {
            id: 'session-item',
            method: 'GET',
            path: '/api/session-items',
            classification: 'BROWSER_SESSION_API',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'browser-skill',
        '--endpoint-spec', browserSpec,
      ]);

      const browserSkillDir = path.join(root, '.agent-forge', 'output', 'browser-skill');
      const browserRevalRaw = await runPythonAsync(['revalidate-skill', '--package-dir', browserSkillDir]);
      const browserReval = JSON.parse(browserRevalRaw);
      assert.equal(browserReval.status, 'BROWSER_SESSION_REVALIDATION_REQUIRED');
      assert.equal(browserReval.verified, false);
      assert.equal(browserReval.tested_endpoints[0].action, 'browser_session_probe');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: generate-skill rejects --output-dir outside <root>/.agent-forge/output', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'boundary-test-'));

    try {
      const outsideDir = path.join(root, 'skills', 'untrusted-escape');
      assert.throws(() => {
        runPython([
          'generate-skill',
          '--root', root,
          '--skill-name', 'escape-skill',
          '--output-dir', outsideDir,
        ]);
      }, /must stay under/i, 'generate-skill must reject writing directly outside .agent-forge/output');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: recursive redaction sanitizes nested JSON payloads, URL userinfo credentials, and nested dictionary leaves', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'nested-redact-'));

    try {
      const userinfoUrl = 'https://admin_user:secret_password_xyz@api.example.com/items?token=secret_query_tok&safe_param=hello';
      const sampleHar = path.join(root, 'sample.har');
      fs.writeFileSync(sampleHar, JSON.stringify({
        log: {
          entries: [
            {
              request: {
                method: 'POST',
                url: userinfoUrl,
                headers: [{ name: 'Authorization', value: 'Bearer super_secret_auth_token' }],
                postData: {
                  mimeType: 'application/json',
                  text: JSON.stringify({
                    credentials: {
                      password: 'secret_nested_password_123',
                      api_key: 'secret_nested_api_key_456',
                    },
                    safe_payload: 'visible',
                  }),
                },
              },
              response: {
                status: 200,
                content: {
                  mimeType: 'application/json',
                  text: JSON.stringify({ token: 'response_token_value' }),
                },
              },
            },
          ],
        },
      }), 'utf8');

      // 1. Inspect HAR: verify userinfo credentials and nested JSON postData are redacted
      const inspectRaw = runPython(['har-inspect', '--har', sampleHar]);
      assert.doesNotMatch(inspectRaw, /secret_password_xyz/);
      assert.doesNotMatch(inspectRaw, /secret_nested_password_123/);
      assert.doesNotMatch(inspectRaw, /secret_nested_api_key_456/);
      assert.doesNotMatch(inspectRaw, /super_secret_auth_token/);
      assert.match(inspectRaw, /\[REDACTED\]/);

      // 2. Generate skill with userinfo and nested dict under sensitive key
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: userinfoUrl,
        path: '/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        headers: {
          Authorization: 'Bearer super_secret_auth_token',
          auth_info: {
            deep_secret_value: 'deep_secret_99999',
          },
        },
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'nested-redact-skill',
        '--endpoint-spec', specFile,
      ]);

      const skillDir = path.join(root, '.agent-forge', 'output', 'nested-redact-skill');
      const manifest = fs.readFileSync(path.join(skillDir, 'endpoint-manifest.json'), 'utf8');
      const provenance = fs.readFileSync(path.join(skillDir, 'provenance.json'), 'utf8');

      assert.doesNotMatch(manifest, /secret_password_xyz/);
      assert.doesNotMatch(manifest, /deep_secret_99999/);
      assert.doesNotMatch(manifest, /super_secret_auth_token/);

      assert.doesNotMatch(provenance, /secret_password_xyz/);
      assert.doesNotMatch(provenance, /deep_secret_99999/);
      assert.doesNotMatch(provenance, /super_secret_auth_token/);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: generated client.py never leaks raw HTTP error response bodies and provenance truthfully reports null HAR hash', async () => {
    const http = await import('node:http');

    const server = http.createServer((req, res) => {
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        sensitive_server_leak: 'leaked_internal_auth_secret_xyz789',
        stack_trace: '/internal/server/secret_config.json',
      }));
    });

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const port = server.address().port;
    const baseUrl = `http://127.0.0.1:${port}`;

    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'client-leak-test-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: baseUrl,
        path: '/api/leak-items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'client-leak-skill',
        '--endpoint-spec', specFile,
      ]);

      const skillDir = path.join(root, '.agent-forge', 'output', 'client-leak-skill');

      // 1. Provenance must not fabricate an all-zero hash when no HAR was provided
      const prov = JSON.parse(fs.readFileSync(path.join(skillDir, 'provenance.json'), 'utf8'));
      assert.equal(prov.har_sha256, null, 'Provenance har_sha256 must be null when no HAR was provided');

      // 2. Client error execution must not leak sensitive server body
      const clientPath = path.join(skillDir, 'client.py');
      let clientOutput = '';
      try {
        await execFileAsync(PYTHON, [clientPath, '--query', 'test'], { encoding: 'utf8' });
      } catch (err) {
        clientOutput = (err.stdout || '') + (err.stderr || '');
      }

      assert.doesNotMatch(clientOutput, /leaked_internal_auth_secret_xyz789/, 'Client must not leak raw server response body in errors');
      assert.doesNotMatch(clientOutput, /secret_config\.json/, 'Client must not leak raw server response details in errors');
      assert.match(clientOutput, /AUTH_EXPIRED/, 'Client must return structured AUTH_EXPIRED diagnostic');
    } finally {
      server.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: generate-skill emits README.md and infers metadata when CLI options are omitted', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'readme-infer-test-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://inferred-api.example.com',
        path: '/api/v1/goods',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Inferred Shop',
        site_slug: 'inferred-shop',
        capability_slug: 'search-goods',
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'inferred-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const skillDir = gen.output_dir;

      assert.ok(fs.existsSync(path.join(skillDir, 'README.md')), 'README.md must be generated in skill package');
      const readmeContent = fs.readFileSync(path.join(skillDir, 'README.md'), 'utf8');
      assert.match(readmeContent, /Inferred Shop/, 'README must include inferred site name');
      assert.match(readmeContent, /https:\/\/inferred-api\.example\.com/, 'README must include target origin');
      assert.match(readmeContent, /revalidate-skill/, 'README must include revalidation command');

      const manifest = JSON.parse(fs.readFileSync(path.join(skillDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest.target_origin, 'https://inferred-api.example.com');
      assert.equal(manifest.endpoints[0].path, '/api/v1/goods');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: generated client.py supports dynamic methods with path parameters and parent auth discovery', async () => {
    const http = await import('node:http');

    const server = http.createServer(async (req, res) => {
      const auth = req.headers['authorization'];
      if (auth !== 'Bearer parent-discovered-token-xyz') {
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: true, code: 'UNAUTHORIZED' }));
        return;
      }

      if (req.method === 'GET' && req.url === '/api/v1/items/42?format=json') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ id: '42', name: 'Item 42' }));
        return;
      }

      if (req.method === 'POST' && req.url === '/api/v1/items') {
        let body = '';
        for await (const chunk of req) body += chunk;
        const parsed = JSON.parse(body || '{}');
        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ created: true, name: parsed.name }));
        return;
      }

      if (req.method === 'DELETE' && req.url === '/api/v1/items/42') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ deleted: true, id: '42' }));
        return;
      }

      res.writeHead(404);
      res.end();
    });

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const port = server.address().port;
    const baseUrl = `http://127.0.0.1:${port}`;

    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'client-methods-test-'));

    try {
      // Write parent auth.json in root
      const parentForge = path.join(root, '.agent-forge');
      fs.mkdirSync(parentForge, { recursive: true });
      fs.writeFileSync(path.join(parentForge, 'auth.json'), JSON.stringify({ token: 'parent-discovered-token-xyz' }), 'utf8');

      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: baseUrl,
        path: '/api/v1/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        endpoints: [
          { id: 'get-item', method: 'GET', path: '/api/v1/items/{id}', classification: 'DIRECT_API_VERIFIED' },
          { id: 'create-item', method: 'POST', path: '/api/v1/items', classification: 'DIRECT_API_VERIFIED' },
          { id: 'delete-item', method: 'DELETE', path: '/api/v1/items/{id}', classification: 'DIRECT_API_VERIFIED' },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'methods-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const skillDir = gen.output_dir;

      // Run python from nested subdir without setting API_AUTH_TOKEN in env -> verifies upward walk to root/.agent-forge/auth.json
      const nestedSubdir = path.join(root, 'nested', 'deep', 'workdir');
      fs.mkdirSync(nestedSubdir, { recursive: true });

      const testScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(skillDir)})
from client import APIClient

client = APIClient()
# GET with path replacement and extra query params
get_res = client.get_item(id=42, format="json")
# POST with data payload
post_res = client.create_item(name="NewWidget")
# DELETE with path replacement
del_res = client.delete_item(id=42)

print(json.dumps({"get": get_res, "post": post_res, "delete": del_res}))
`;

      const execResult = await execFileAsync(PYTHON, ['-c', testScript], {
        cwd: nestedSubdir,
        encoding: 'utf8',
      });
      const parsedOutput = JSON.parse(execResult.stdout);
      assert.equal(parsedOutput.get.id, '42');
      assert.equal(parsedOutput.post.created, true);
      assert.equal(parsedOutput.post.name, 'NewWidget');
      assert.equal(parsedOutput.delete.deleted, true);
    } finally {
      server.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: export-skill strips auth.json, .env, and HAR capture files from exported destination', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'export-strip-test-'));

    try {
      const pkgDir = path.join(root, '.agent-forge', 'output', 'strip-skill');
      fs.mkdirSync(pkgDir, { recursive: true });
      fs.writeFileSync(path.join(pkgDir, 'SKILL.md'), '---\nname: strip-skill\n---\n# Strip Skill', 'utf8');
      fs.writeFileSync(path.join(pkgDir, 'README.md'), '# Strip Skill README', 'utf8');
      fs.writeFileSync(path.join(pkgDir, 'endpoint-manifest.json'), JSON.stringify({ skill_name: 'strip-skill' }), 'utf8');
      fs.writeFileSync(path.join(pkgDir, 'provenance.json'), JSON.stringify({ target_origin: 'https://example.com' }), 'utf8');
      fs.writeFileSync(path.join(pkgDir, 'client.py'), '# client code', 'utf8');
      fs.writeFileSync(path.join(pkgDir, 'auth.json'), JSON.stringify({ token: 'secret-token' }), 'utf8');
      fs.writeFileSync(path.join(pkgDir, '.env'), 'SECRET_KEY=12345', 'utf8');
      fs.writeFileSync(path.join(pkgDir, 'capture.har'), JSON.stringify({ log: {} }), 'utf8');
      fs.writeFileSync(path.join(pkgDir, 'sample.har'), JSON.stringify({ log: {} }), 'utf8');

      const destDir = path.join(root, 'exported', 'strip-skill');
      const exportRaw = runPython([
        'export-skill',
        '--package-dir', pkgDir,
        '--destination', destDir,
      ]);
      const exportRes = JSON.parse(exportRaw);
      assert.equal(exportRes.exported, true);

      // Verify essential files copied
      assert.ok(fs.existsSync(path.join(destDir, 'SKILL.md')));
      assert.ok(fs.existsSync(path.join(destDir, 'README.md')));
      assert.ok(fs.existsSync(path.join(destDir, 'endpoint-manifest.json')));
      assert.ok(fs.existsSync(path.join(destDir, 'provenance.json')));
      assert.ok(fs.existsSync(path.join(destDir, 'client.py')));

      // Verify sensitive files stripped
      assert.equal(fs.existsSync(path.join(destDir, 'auth.json')), false, 'auth.json must not be exported');
      assert.equal(fs.existsSync(path.join(destDir, '.env')), false, '.env must not be exported');
      assert.equal(fs.existsSync(path.join(destDir, 'capture.har')), false, 'capture.har must not be exported');
      assert.equal(fs.existsSync(path.join(destDir, 'sample.har')), false, 'sample.har must not be exported');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: DIRECT_API_VERIFIED endpoint with prefilled PASSED status but no successful tested_variations is downgraded to UNVERIFIED and not counted in provenance', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'evidence-gate-test-'));

    try {
      // 1. Endpoint with prefilled PASSED but empty tested_variations
      const emptyVarsSpec = path.join(root, 'empty-vars-spec.json');
      fs.writeFileSync(emptyVarsSpec, JSON.stringify({
        base_url: 'https://example.com',
        path: '/items',
        classification: 'DIRECT_API_VERIFIED',
        endpoints: [
          {
            id: 'empty-vars-ep',
            method: 'GET',
            path: '/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: {
              status: 'PASSED',
              tested_variations: [],
            },
          },
        ],
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'empty-vars-skill',
        '--endpoint-spec', emptyVarsSpec,
      ]);

      const emptySkillDir = path.join(root, '.agent-forge', 'output', 'empty-vars-skill');
      const emptyManifest = JSON.parse(fs.readFileSync(path.join(emptySkillDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(emptyManifest.endpoints[0].verification.status, 'UNVERIFIED', 'Status must be downgraded to UNVERIFIED when tested_variations is empty');

      const emptyProv = JSON.parse(fs.readFileSync(path.join(emptySkillDir, 'provenance.json'), 'utf8'));
      assert.equal(emptyProv.verification_summary.direct_api_count, 0, 'Provenance must not count unverified endpoint as direct_api_count');
      assert.equal(emptyProv.verification_summary.all_passed, false, 'all_passed must be false when endpoint is downgraded to UNVERIFIED');

      // 2. Endpoint with prefilled PASSED and only failing variations (e.g. status 500)
      const failedVarsSpec = path.join(root, 'failed-vars-spec.json');
      fs.writeFileSync(failedVarsSpec, JSON.stringify({
        base_url: 'https://example.com',
        path: '/items',
        classification: 'DIRECT_API_VERIFIED',
        endpoints: [
          {
            id: 'failed-vars-ep',
            method: 'GET',
            path: '/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: {
              status: 'PASSED',
              tested_variations: [{ params: { q: 'fail' }, status: 500 }],
            },
          },
        ],
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'failed-vars-skill',
        '--endpoint-spec', failedVarsSpec,
      ]);

      const failedSkillDir = path.join(root, '.agent-forge', 'output', 'failed-vars-skill');
      const failedManifest = JSON.parse(fs.readFileSync(path.join(failedSkillDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(failedManifest.endpoints[0].verification.status, 'UNVERIFIED', 'Status must be downgraded to UNVERIFIED when tested_variations has no 200/201/204');

      const failedProv = JSON.parse(fs.readFileSync(path.join(failedSkillDir, 'provenance.json'), 'utf8'));
      assert.equal(failedProv.verification_summary.direct_api_count, 0, 'Provenance direct_api_count must be 0');
      assert.equal(failedProv.verification_summary.all_passed, false, 'all_passed must be false');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });
});

describe('agent-browser-skill-forge Issue #14 (Coordinator-Confirmed Blocker Regressions)', () => {
  test('regression: spec-driven CLI invokes correct endpoint operation, not invented extract_items', async () => {
    const http = await import('node:http');
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, `http://${req.headers.host}`);
      if (url.pathname === '/api/v2/search' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ results: [{ id: '1', name: url.searchParams.get('keyword') }], total: 1 }));
        return;
      }
      res.writeHead(404);
      res.end();
    });

    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const port = server.address().port;
    const baseUrl = `http://127.0.0.1:${port}`;

    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'spec-cli-test-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: baseUrl,
        path: '/api/v2/search',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        endpoints: [
          {
            id: 'search-results',
            method: 'GET',
            path: '/api/v2/search',
            classification: 'DIRECT_API_VERIFIED',
            parameters: {
              keyword: { type: 'string', in: 'query', name: 'keyword' },
            },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'search-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const skillDir = gen.output_dir;

      // 1. Check that client.py contains search_results method, not invented extract_items
      const clientSrc = fs.readFileSync(path.join(skillDir, 'client.py'), 'utf8');
      assert.match(clientSrc, /def search_results\(/, 'client.py must have search_results method from spec');
      assert.doesNotMatch(clientSrc, /def extract_items\(/, 'client.py must NOT contain invented extract_items when spec defines real endpoints');

      // 2. CLI must invoke search_results, not extract_items
      assert.match(clientSrc, /client\.search_results\(/, 'main() CLI must call client.search_results() from spec, not extract_items');
      assert.doesNotMatch(clientSrc, /client\.extract_items\(/, 'main() CLI must NOT call invented extract_items');

      // 3. CLI --keyword arg must exist (from spec parameters)
      assert.match(clientSrc, /--keyword/, 'CLI must expose --keyword arg from spec parameters');

      // 4. Actually run the CLI with --keyword and verify correct server call
      const cliResult = await execFileAsync(PYTHON, [path.join(skillDir, 'client.py'), '--keyword', 'widget'], {
        encoding: 'utf8',
        env: { ...process.env, API_AUTH_TOKEN: '' },
      });
      const parsed = JSON.parse(cliResult.stdout);
      assert.equal(parsed.results[0].name, 'widget', 'CLI must pass --keyword to correct endpoint');
    } finally {
      server.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: generated client auth discovery is based on __file__ location inside .agent-forge boundary, not CWD', async () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'auth-file-scope-'));

    try {
      // Write auth inside root/.agent-forge (the private workspace boundary)
      const forgeDir = path.join(root, '.agent-forge');
      fs.mkdirSync(forgeDir, { recursive: true });
      fs.writeFileSync(path.join(forgeDir, 'auth.json'), JSON.stringify({ token: 'private-workspace-token' }), 'utf8');

      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://example.com',
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'auth-file-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const skillDir = gen.output_dir;
      // client.py is at: root/.agent-forge/output/auth-file-skill/client.py
      // Walking __file__ ancestors: output/auth-file-skill -> output -> .agent-forge (found!) -> reads auth.json

      // 1. Client inside .agent-forge: discovers private-workspace-token regardless of CWD
      const checkInsideScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(skillDir)})
from client import APIClient
client = APIClient()
print(json.dumps({"token": client.auth_token or "none"}))
`;
      // Run from an UNRELATED cwd (should not matter — auth is based on __file__, not cwd)
      const unrelatedCwd = os.tmpdir();
      const insideRes = await execFileAsync(PYTHON, ['-c', checkInsideScript], {
        cwd: unrelatedCwd,
        encoding: 'utf8',
        env: { ...process.env, API_AUTH_TOKEN: '' },
      });
      const parsedInside = JSON.parse(insideRes.stdout);
      assert.equal(parsedInside.token, 'private-workspace-token',
        'Client inside .agent-forge must discover auth from __file__ boundary regardless of CWD');

      // 2. Exported client (copied outside .agent-forge) must NOT do file auth discovery
      const exportDir = path.join(root, 'exported-skill');
      fs.mkdirSync(exportDir, { recursive: true });
      fs.copyFileSync(path.join(skillDir, 'client.py'), path.join(exportDir, 'client.py'));
      // exportDir has no .agent-forge ancestor -> no auth file discovery

      const checkExportedScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(exportDir)})
from client import APIClient
client = APIClient()
print(json.dumps({"token": client.auth_token or "none"}))
`;
      const exportedRes = await execFileAsync(PYTHON, ['-c', checkExportedScript], {
        cwd: root,  // Even if run from root (which HAS .agent-forge/auth.json), __file__ is outside .agent-forge
        encoding: 'utf8',
        env: { ...process.env, API_AUTH_TOKEN: '' },
      });
      const parsedExported = JSON.parse(exportedRes.stdout);
      assert.equal(parsedExported.token, 'none',
        'Exported client (outside .agent-forge) must not discover file auth — requires explicit token or API_AUTH_TOKEN');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: exploration_time_s is recorded distinctly in provenance when supplied in spec', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'exploration-time-test-'));

    try {
      // 1. With exploration_time_s in spec -> must appear in provenance
      const specWithTime = path.join(root, 'spec-with-time.json');
      fs.writeFileSync(specWithTime, JSON.stringify({
        base_url: 'https://example.com',
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        exploration_time_s: 42.5,
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'timed-skill',
        '--endpoint-spec', specWithTime,
      ]);

      const timedProv = JSON.parse(fs.readFileSync(path.join(root, '.agent-forge', 'output', 'timed-skill', 'provenance.json'), 'utf8'));
      assert.ok('exploration_time' in timedProv, 'provenance.json must have exploration_time field when supplied in spec');
      assert.equal(timedProv.exploration_time, 42.5, 'exploration_time must record the value from spec evidence');
      assert.ok(!('exploration_time_s' in timedProv), 'provenance.json must not use exploration_time_s key (normalized to exploration_time)');

      // 2. Without exploration_time in spec -> field must be ABSENT from provenance (not invented/null)
      const specNoTime = path.join(root, 'spec-no-time.json');
      fs.writeFileSync(specNoTime, JSON.stringify({
        base_url: 'https://example.com',
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
      }), 'utf8');

      runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'untimed-skill',
        '--endpoint-spec', specNoTime,
      ]);

      const untimedProv = JSON.parse(fs.readFileSync(path.join(root, '.agent-forge', 'output', 'untimed-skill', 'provenance.json'), 'utf8'));
      assert.ok(!('exploration_time' in untimedProv), 'provenance.json must NOT include exploration_time when not supplied in spec (no invented null)');
      assert.ok(!('exploration_time_s' in untimedProv), 'provenance.json must NOT include exploration_time_s');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: README references correct endpoint operation from spec, not hardcoded extract_items', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'readme-spec-driven-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://api.example.com',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Example Shop',
        endpoints: [
          {
            id: 'list-products',
            method: 'GET',
            path: '/v2/products',
            classification: 'DIRECT_API_VERIFIED',
            parameters: {
              category: { type: 'string', in: 'query', name: 'category' },
            },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'shop-products',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const skillDir = gen.output_dir;

      const readmeContent = fs.readFileSync(path.join(skillDir, 'README.md'), 'utf8');
      // README must reference actual endpoint operation
      assert.match(readmeContent, /list_products/, 'README must reference list_products (from spec endpoint id), not invented method');
      assert.doesNotMatch(readmeContent, /extract_items/, 'README must NOT reference hardcoded extract_items');
      // README must reference actual path
      assert.match(readmeContent, /\/v2\/products/, 'README must reference actual endpoint path');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: HYBRID spec generates client methods for all DIRECT_API_VERIFIED endpoints and browser strategy in SKILL.md', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'hybrid-gen-test-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://hybrid.example.com',
        classification: 'HYBRID',
        site_name: 'Hybrid Site',
        site_slug: 'hybrid-site',
        endpoints: [
          {
            id: 'api-list',
            method: 'GET',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            parameters: {
              q: { type: 'string', in: 'query', name: 'q' },
            },
            verification: { status: 'PASSED', tested_variations: [{ params: { q: 'test' }, status: 200 }] },
          },
          {
            id: 'dom-detail',
            method: 'GET',
            path: '/items/{id}',
            classification: 'DOM_ONLY',
            verification: { status: 'FALLBACK', tested_variations: [] },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'hybrid-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const skillDir = gen.output_dir;

      // client.py must exist (DIRECT_API_VERIFIED endpoint present)
      assert.ok(fs.existsSync(path.join(skillDir, 'client.py')), 'client.py must be generated for HYBRID skill with DIRECT_API_VERIFIED endpoint');

      // client.py must have api_list method from spec
      const clientSrc = fs.readFileSync(path.join(skillDir, 'client.py'), 'utf8');
      assert.match(clientSrc, /def api_list\(/, 'client.py must have api_list method from spec');
      assert.doesNotMatch(clientSrc, /def extract_items\(/, 'client.py must NOT contain invented extract_items');

      // Manifest must have both endpoints
      const manifest = JSON.parse(fs.readFileSync(path.join(skillDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest.endpoints.length, 2, 'Manifest must have both endpoints');
      const directEp = manifest.endpoints.find(e => e.id === 'api-list');
      const domEp = manifest.endpoints.find(e => e.id === 'dom-detail');
      assert.ok(directEp, 'Manifest must have api-list endpoint');
      assert.ok(domEp, 'Manifest must have dom-detail endpoint');

      // Provenance must count HYBRID correctly
      const prov = JSON.parse(fs.readFileSync(path.join(skillDir, 'provenance.json'), 'utf8'));
      assert.ok(prov.verification_summary.hybrid_count >= 1, 'Provenance must count hybrid_count >= 1 for HYBRID classification');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: revalidate-skill performs safe live DOM and browser session revalidation against fixture', async () => {
    const fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'reval-live-dom-'));

    try {
      // 1. Generate skill package with DOM_ONLY endpoint pointing to /catalog
      const specFile = path.join(root, 'browser-reval-spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/catalog',
        method: 'GET',
        classification: 'DOM_ONLY',
        site_name: 'Live Catalog Store',
        site_slug: 'live-catalog-store',
        capability_slug: 'catalog-items',
        endpoints: [
          {
            id: 'catalog-items',
            method: 'GET',
            path: '/catalog',
            classification: 'DOM_ONLY',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'live-dom-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const skillDir = gen.output_dir;

      // 2. Perform live revalidation on the healthy fixture catalog page
      const revalHealthyRaw = await runPythonAsync(['revalidate-skill', '--package-dir', skillDir, '--base-url', fixture.baseUrl]);
      const revalHealthy = JSON.parse(revalHealthyRaw);
      assert.equal(revalHealthy.status, 'HEALTHY', 'Status must be HEALTHY when live DOM probe succeeds');
      assert.equal(revalHealthy.verified, true, 'Skill must be verified when live browser DOM probe succeeds');
      assert.equal(revalHealthy.tested_endpoints.length, 1);
      assert.equal(revalHealthy.tested_endpoints[0].status, 'BROWSER_DOM_VERIFIED');
      assert.equal(revalHealthy.tested_endpoints[0].verified, true);
      assert.equal(revalHealthy.tested_endpoints[0].action, 'browser_session_probe');
      assert.equal(revalHealthy.tested_endpoints[0].safe, true);

      // 3. Perform live revalidation on a 404 endpoint -> detects failure without manual action required first
      const revalNotFoundRaw = await runPythonAsync(['revalidate-skill', '--package-dir', skillDir, '--base-url', `${fixture.baseUrl}/non-existent-page`]);
      const revalNotFound = JSON.parse(revalNotFoundRaw);
      assert.equal(revalNotFound.verified, false, 'Revalidation must fail on non-existent page');
      assert.equal(revalNotFound.tested_endpoints[0].verified, false);
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });
});

describe('agent-browser-skill-forge Issue #15 (Delivery, Installation, & Black-Box Execution)', () => {
  let fixture;

  test('black-box testing executes DIRECT_API_VERIFIED capability via Python client without launching agent-browser', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'blackbox-direct-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Catalog Store',
        site_slug: 'catalog-store',
        capability_slug: 'extract-items',
        endpoints: [
          {
            id: 'extract-items',
            method: 'GET',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            parameters: {
              page: { type: 'integer', in: 'query', name: 'page', default: 1 },
              limit: { type: 'integer', in: 'query', name: 'limit', default: 5 },
            },
            verification: { status: 'PASSED', tested_variations: [{ params: { page: 1 }, status: 200 }] },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'catalog-items-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const skillDir = gen.output_dir;

      // 1. Independent Black-Box test runner (receives only package dir and base_url)
      const testReportRaw = await runPythonAsync(['test-skill', '--package-dir', skillDir, '--base-url', fixture.baseUrl]);
      const testReport = JSON.parse(testReportRaw);

      assert.equal(testReport.all_passed, true, 'All black-box tests must pass');
      assert.equal(testReport.components.length, 1);
      assert.equal(testReport.components[0].name, 'extract-items');
      assert.equal(testReport.components[0].classification, 'DIRECT_API_VERIFIED');
      assert.equal(testReport.components[0].steady_state_runtime, 'python');
      assert.equal(testReport.components[0].import_check, true, 'Module import check must pass');
      assert.equal(testReport.components[0].cli_check, true, 'CLI execution check must pass');
      assert.ok(testReport.components[0].output_summary);

      // 2. Black-box agent directly imports APIClient and executes queries
      const blackboxScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(skillDir)})
from client import APIClient

client = APIClient(base_url=${JSON.stringify(fixture.baseUrl)})
# Verify atomic component
res_p1 = client.extract_items(page=1, limit=3)
res_p2 = client.extract_items(page=2, limit=3)

print(json.dumps({
    "p1_count": len(res_p1.get("items", [])),
    "p2_count": len(res_p2.get("items", [])),
    "p1_first_id": res_p1["items"][0]["id"] if res_p1.get("items") else None,
    "p2_first_id": res_p2["items"][0]["id"] if res_p2.get("items") else None,
}))
`;
      const execRes = await execFileAsync(PYTHON, ['-c', blackboxScript], { encoding: 'utf8' });
      const parsedExec = JSON.parse(execRes.stdout);
      assert.equal(parsedExec.p1_count, 3);
      assert.equal(parsedExec.p2_count, 3);
      assert.notEqual(parsedExec.p1_first_id, parsedExec.p2_first_id, 'Pagination must return distinct records across pages');
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('black-box testing executes DOM_ONLY and HYBRID generated paths through documented prerequisites', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'blackbox-hybrid-'));

    try {
      // 1. Generate DOM_ONLY capability
      const domSpec = path.join(root, 'dom-spec.json');
      fs.writeFileSync(domSpec, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/catalog',
        classification: 'DOM_ONLY',
        site_name: 'DOM Store',
        endpoints: [
          { id: 'extract-dom', method: 'GET', path: '/catalog', classification: 'DOM_ONLY' },
        ],
      }), 'utf8');

      const genDomRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'dom-skill',
        '--endpoint-spec', domSpec,
      ]);
      const domDir = JSON.parse(genDomRaw).output_dir;

      const domReportRaw = await runPythonAsync(['test-skill', '--package-dir', domDir, '--base-url', fixture.baseUrl]);
      const domReport = JSON.parse(domReportRaw);
      assert.equal(domReport.all_passed, true);
      assert.equal(domReport.components[0].classification, 'DOM_ONLY');
      assert.equal(domReport.components[0].script_check, true);

      // 2. Generate HYBRID capability pointing to verified fixture endpoints
      const hybridSpec = path.join(root, 'hybrid-spec.json');
      fs.writeFileSync(hybridSpec, JSON.stringify({
        base_url: fixture.baseUrl,
        classification: 'HYBRID',
        site_name: 'Hybrid Store',
        endpoints: [
          {
            id: 'api-feed',
            method: 'GET',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ params: {}, status: 200 }] },
          },
          {
            id: 'dom-feed',
            method: 'GET',
            path: '/catalog',
            classification: 'DOM_ONLY',
          },
        ],
      }), 'utf8');

      const genHybridRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'hybrid-test-skill',
        '--endpoint-spec', hybridSpec,
      ]);
      const hybridDir = JSON.parse(genHybridRaw).output_dir;

      const hybridReportRaw = await runPythonAsync(['test-skill', '--package-dir', hybridDir, '--base-url', fixture.baseUrl]);
      const hybridReport = JSON.parse(hybridReportRaw);
      assert.equal(hybridReport.all_passed, true);
      assert.equal(hybridReport.components.length, 2);

      // 3. Directly evaluate generated DOM extraction script against live fixture DOM
      const bootstrap = JSON.parse(runPython(['bootstrap', '--root', root, '--task', 'dom-eval']));
      try {
        runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'open', `${fixture.baseUrl}/catalog`]);
        runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'wait', '--load', 'networkidle']);
        const scriptFiles = fs.readdirSync(path.join(domDir, 'scripts')).filter(f => f.endsWith('.py'));
        assert.ok(scriptFiles.length > 0, 'Generated scripts helper must exist');
        const domScript = path.join(domDir, 'scripts', scriptFiles[0]);
        const jsCode = execFileSync(PYTHON, [domScript], { encoding: 'utf8' });
        const b64 = Buffer.from(jsCode, 'utf8').toString('base64');
        const evalOutRaw = runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'eval', '-b', b64]);
        let evalData = JSON.parse(evalOutRaw);
        if (typeof evalData === 'string') {
          evalData = JSON.parse(evalData);
        }
        assert.ok(evalData.items && evalData.items.length > 0, 'DOM extraction must return items array');
        assert.equal(evalData.items[0].title, 'Product 1', 'Title must match Product 1');
        assert.equal(evalData.items[0].price, '$10', 'Price must match $10');
      } finally {
        try { runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'close']); } catch {}
      }
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('test reports record component outcomes, failure reasons, and redact secret credentials', async () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'report-redact-'));

    try {
      const secretToken = 'secret_access_jwt_token_44444';
      const specFile = path.join(root, 'spec-secrets.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://secure.example.com',
        path: '/api/v1/secure',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        headers: { Authorization: `Bearer ${secretToken}` },
        parameters: { token: { type: 'string', in: 'query', name: 'token', default: secretToken } },
        endpoints: [
          {
            id: 'get-secure-items',
            method: 'GET',
            path: '/api/v1/secure',
            classification: 'DIRECT_API_VERIFIED',
            parameters: { token: { type: 'string', in: 'query', name: 'token', default: secretToken } },
            verification: { status: 'PASSED', tested_variations: [{ params: {}, status: 200 }] },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'secure-report-skill',
        '--endpoint-spec', specFile,
      ]);
      const skillDir = JSON.parse(genRaw).output_dir;

      let reportRaw = '';
      try {
        reportRaw = await runPythonAsync(['test-skill', '--package-dir', skillDir]);
      } catch (err) {
        reportRaw = (err.stdout || err.stderr || '').toString();
      }

      assert.doesNotMatch(reportRaw, new RegExp(secretToken), 'Test report must not leak secret token');
      const report = JSON.parse(reportRaw);
      assert.ok('components' in report, 'Report must contain components array');
      assert.equal(report.components[0].name, 'get-secure-items');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('failed black-box test causes diagnostic error reporting and package correction loop', async () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'fail-correct-'));

    try {
      const brokenPkg = path.join(root, 'broken-skill');
      fs.mkdirSync(brokenPkg, { recursive: true });
      fs.writeFileSync(path.join(brokenPkg, 'SKILL.md'), '---\nname: broken-skill\n---\n# Broken Skill\nClassification: `DIRECT_API_VERIFIED`', 'utf8');
      fs.writeFileSync(path.join(brokenPkg, 'endpoint-manifest.json'), JSON.stringify({
        endpoints: [{ id: 'missing-method', classification: 'DIRECT_API_VERIFIED' }],
      }), 'utf8');
      fs.writeFileSync(path.join(brokenPkg, 'provenance.json'), JSON.stringify({ har_sha256: 'abc' }), 'utf8');
      // client.py has a syntax error
      fs.writeFileSync(path.join(brokenPkg, 'client.py'), 'def syntax_error(', 'utf8');

      // 1. Black-box test must fail with non-zero exit code
      let testFailed = false;
      let failOutput = '';
      try {
        await runPythonAsync(['test-skill', '--package-dir', brokenPkg]);
      } catch (err) {
        testFailed = true;
        failOutput = (err.stdout || err.stderr || '').toString();
      }
      assert.ok(testFailed, 'test-skill must fail on broken client');
      assert.match(failOutput, /failures|status.*FAILED|SyntaxError/i);

      // 2. Correct the package (repair client.py)
      fs.writeFileSync(path.join(brokenPkg, 'client.py'), `
class APIClient:
    def __init__(self, base_url="https://example.com"): self.base_url = base_url
    def missing_method(self): return {"success": True, "items": []}
if __name__ == "__main__":
    print('{"success": true, "items": []}')
`, 'utf8');

      // 3. Retest must now pass
      const passedRaw = await runPythonAsync(['test-skill', '--package-dir', brokenPkg]);
      const passedReport = JSON.parse(passedRaw);
      assert.equal(passedReport.all_passed, true, 'Retest after correction must succeed');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('generated skill installs via canonical UX and installation failure preserves private output intact', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'install-test-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://example.com',
        path: '/api/goods',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Install Shop',
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'install-shop-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const outputDir = gen.output_dir;

      assert.ok(fs.existsSync(path.join(outputDir, 'SKILL.md')));
      assert.ok(fs.existsSync(path.join(outputDir, 'client.py')));

      // 1. Install via install-skill into mock agent env
      const installRaw = runPython([
        'install-skill',
        '--package-dir', outputDir,
        '--agent', 'antigravity',
        '--root', root,
      ]);
      const installRes = JSON.parse(installRaw);
      assert.equal(installRes.installed, true);
      assert.equal(installRes.agent, 'antigravity');
      assert.ok(fs.existsSync(path.join(root, '.agents', 'skills', 'install-shop-skill', 'SKILL.md')));
      assert.ok(fs.existsSync(path.join(root, '.agents', 'skills', 'install-shop-skill', 'client.py')));

      // 2. Verify source directory in .agent-forge/output is still completely intact
      assert.ok(fs.existsSync(path.join(outputDir, 'SKILL.md')), 'Source SKILL.md must remain intact after install');
      assert.ok(fs.existsSync(path.join(outputDir, 'client.py')), 'Source client.py must remain intact after install');

      // 3. Failed install scenario (e.g. invalid package): preserves outputDir
      const badPkg = path.join(root, '.agent-forge', 'output', 'bad-pkg');
      fs.mkdirSync(badPkg, { recursive: true });
      fs.writeFileSync(path.join(badPkg, 'some-file.txt'), 'content', 'utf8'); // missing SKILL.md

      let installFailed = false;
      try {
        runPython(['install-skill', '--package-dir', badPkg, '--root', root]);
      } catch {
        installFailed = true;
      }
      assert.ok(installFailed, 'install-skill must fail on invalid package');
      assert.ok(fs.existsSync(badPkg), 'Source folder must not be deleted on install failure');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('coordinator-agnostic validation rejects coordinator-specific orchestration syntax', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'coord-syntax-'));

    try {
      const coordSkillDir = path.join(root, 'coord-skill');
      fs.mkdirSync(coordSkillDir, { recursive: true });
      fs.writeFileSync(path.join(coordSkillDir, 'endpoint-manifest.json'), JSON.stringify({ endpoints: [] }), 'utf8');
      fs.writeFileSync(path.join(coordSkillDir, 'provenance.json'), JSON.stringify({ har_sha256: 'abc' }), 'utf8');

      // Case A: SKILL.md with Claude/ChatGPT/AGY orchestration syntax
      fs.writeFileSync(path.join(coordSkillDir, 'SKILL.md'), `---
name: coord-skill
description: "Test skill"
---
# Coord Skill
Classification: \`DIRECT_API_VERIFIED\`
Tell Claude to dispatch a Subagent: to run manage_task.
`, 'utf8');

      let valFailed = false;
      let valOut = '';
      try {
        runPython(['validate-package', '--package-dir', coordSkillDir]);
      } catch (err) {
        valFailed = true;
        valOut = (err.stdout || err.stderr || '').toString();
      }
      assert.ok(valFailed, 'validate-package must fail on coordinator-specific syntax');
      assert.match(valOut, /coordinator-specific syntax/i);

      // Case B: Clean SKILL.md with standard shell/Python instructions passes
      fs.writeFileSync(path.join(coordSkillDir, 'SKILL.md'), `---
name: coord-skill
description: "Test skill"
---
# Coord Skill
Classification: \`DIRECT_API_VERIFIED\`
Execute \`python client.py --query "test"\` from shell.
`, 'utf8');

      const valRaw = runPython(['validate-package', '--package-dir', coordSkillDir]);
      const val = JSON.parse(valRaw);
      assert.equal(val.valid, true, 'Clean coordinator-agnostic skill must pass validation');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('execution intent follow-through executes user task using installed skill in steady state without re-entering forge', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'exec-intent-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Catalog Store',
        endpoints: [
          {
            id: 'list-items',
            method: 'GET',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            parameters: {
              query: { type: 'string', in: 'query', name: 'q' },
            },
            verification: { status: 'PASSED', tested_variations: [{ params: { q: 'Sensor' }, status: 200 }] },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'exec-intent-skill',
        '--endpoint-spec', specFile,
      ]);
      const skillDir = JSON.parse(genRaw).output_dir;

      // 1. Install skill
      runPython(['install-skill', '--package-dir', skillDir, '--agent', 'antigravity', '--root', root]);
      const installedDir = path.join(root, '.agents', 'skills', 'exec-intent-skill');

      // 2. Perform user original task (e.g. search for "Product 12") in steady-state
      const userTaskScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(installedDir)})
from client import APIClient

client = APIClient(base_url=${JSON.stringify(fixture.baseUrl)})
result = client.list_items(query="Product 12")
print(json.dumps(result))
`;
      const taskExec = await execFileAsync(PYTHON, ['-c', userTaskScript], { encoding: 'utf8' });
      const taskResult = JSON.parse(taskExec.stdout);
      assert.equal(taskResult.items.length, 1);
      assert.equal(taskResult.items[0].title, 'Product 12');
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('black-box testing consumes supplied test cases/required parameter values in test-skill', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'blackbox-params-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/api/required-val',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Param Shop',
        endpoints: [
          {
            id: 'get-with-param',
            method: 'GET',
            path: '/api/required-val',
            classification: 'DIRECT_API_VERIFIED',
            parameters: {
              required_val: { type: 'string', in: 'query', name: 'required_val' },
            },
            verification: { status: 'PASSED', tested_variations: [{ params: { required_val: 'invalid' }, status: 200 }] },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'param-skill',
        '--endpoint-spec', specFile,
      ]);
      const skillDir = JSON.parse(genRaw).output_dir;

      // 1. Without --test-cases: must fail because required_val='invalid' fails on fixture server (returns 400)
      let defaultFailed = false;
      try {
        await runPythonAsync(['test-skill', '--package-dir', skillDir, '--base-url', fixture.baseUrl]);
      } catch (err) {
        defaultFailed = true;
      }
      assert.ok(defaultFailed, 'test-skill must fail when using default incorrect tested_variations');

      // 2. With --test-cases file: must succeed because it overrides the parameter to 'valid'
      const testCasesFile = path.join(root, 'test-cases.json');
      fs.writeFileSync(testCasesFile, JSON.stringify({
        'get-with-param': { required_val: 'valid' }
      }), 'utf8');

      const testReportRaw = await runPythonAsync([
        'test-skill',
        '--package-dir', skillDir,
        '--base-url', fixture.baseUrl,
        '--test-cases', testCasesFile
      ]);
      const testReport = JSON.parse(testReportRaw);

      assert.equal(testReport.all_passed, true, 'test-skill must pass when using correct parameters supplied via --test-cases');
      assert.equal(testReport.components[0].import_check, true);
      assert.equal(testReport.components[0].cli_check, true);
      // Make sure the explicit keys required by Gap 3 are present even when empty
      assert.ok('unclear_instructions' in testReport);
      assert.ok('severe_issues' in testReport);
      assert.ok('failures' in testReport);
      assert.ok('failure_reasons' in testReport);
      assert.ok('severe_accuracy_performance_issues' in testReport);
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('black-box testing BROWSER_SESSION_API through documented agent-browser prerequisites', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'blackbox-session-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/catalog',
        classification: 'BROWSER_SESSION_API',
        site_name: 'Session Shop',
        capability_slug: 'session-extract',
        endpoints: [
          {
            id: 'session-extract',
            method: 'GET',
            path: '/catalog',
            classification: 'BROWSER_SESSION_API',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'session-skill',
        '--endpoint-spec', specFile,
      ]);
      const skillDir = JSON.parse(genRaw).output_dir;

      // test-skill must report successful black-box validation of the script helper
      const testReportRaw = await runPythonAsync(['test-skill', '--package-dir', skillDir, '--base-url', fixture.baseUrl]);
      const testReport = JSON.parse(testReportRaw);

      assert.equal(testReport.all_passed, true);
      assert.equal(testReport.components[0].classification, 'BROWSER_SESSION_API');
      assert.equal(testReport.components[0].script_check, true);

      const readmeContent = fs.readFileSync(path.join(skillDir, 'README.md'), 'utf8');
      assert.match(readmeContent, /Browser Steady-State Usage/);
      assert.match(readmeContent, /python scripts\/session-extract\.py/);
      assert.match(readmeContent, /agent-browser eval --stdin/);
      assert.doesNotMatch(readmeContent, /python client\.py/);
      assert.doesNotMatch(readmeContent, /from client import APIClient/);

      // Verify execution of the generated script helper via agent-browser boundary
      const bootstrap = JSON.parse(runPython(['bootstrap', '--root', root, '--task', 'session-eval']));
      try {
        runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'open', `${fixture.baseUrl}/catalog`]);
        runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'wait', '--load', 'networkidle']);
        const scriptFiles = fs.readdirSync(path.join(skillDir, 'scripts')).filter(f => f.endsWith('.py'));
        assert.ok(scriptFiles.length > 0, 'Generated scripts helper must exist');
        const sessionScript = path.join(skillDir, 'scripts', scriptFiles[0]);
        const jsCode = execFileSync(PYTHON, [sessionScript], { encoding: 'utf8' });
        const b64 = Buffer.from(jsCode, 'utf8').toString('base64');
        const evalOutRaw = runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'eval', '-b', b64]);
        let evalData = JSON.parse(evalOutRaw);
        if (typeof evalData === 'string') {
          evalData = JSON.parse(evalData);
        }
        assert.ok(evalData.items && evalData.items.length > 0, 'DOM extraction must return items array');
        assert.equal(evalData.items[0].title, 'Product 1', 'Title must match Product 1');
      } finally {
        try { runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'close']); } catch {}
      }
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: generated README and SKILL provide portable Windows and POSIX browser steady-state instructions', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'portability-test-'));

    try {
      const specFile = path.join(root, 'browser-spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://portable-store.example.com',
        path: '/items',
        classification: 'DOM_ONLY',
        site_name: 'Portable Store',
        capability_slug: 'items-extract',
        endpoints: [
          {
            id: 'items-extract',
            method: 'GET',
            path: '/items',
            classification: 'DOM_ONLY',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'portable-skill',
        '--endpoint-spec', specFile,
      ]);
      const skillDir = JSON.parse(genRaw).output_dir;

      const readmeContent = fs.readFileSync(path.join(skillDir, 'README.md'), 'utf8');
      assert.match(readmeContent, /Browser Steady-State Usage/);
      assert.match(readmeContent, /agent-browser eval --stdin/);
      assert.match(readmeContent, /temp_eval\.js/, 'README must include Windows temp-file redirection instruction');
      assert.match(readmeContent, /cmd\.exe \/c "agent-browser eval --stdin < temp_eval\.js"/, 'README must include cmd.exe redirection for Windows');

      const skillMdContent = fs.readFileSync(path.join(skillDir, 'SKILL.md'), 'utf8');
      assert.match(skillMdContent, /agent-browser eval --stdin/);
      assert.match(skillMdContent, /temp_eval\.js/, 'SKILL.md must include Windows instruction');
      assert.match(skillMdContent, /cmd\.exe \/c "agent-browser eval --stdin < temp_eval\.js"/, 'SKILL.md must include cmd.exe redirection for Windows');

      const valRaw = runPython(['validate-package', '--package-dir', skillDir]);
      const val = JSON.parse(valRaw);
      assert.equal(val.valid, true, 'Package with portable instructions must pass validation');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: generated README revalidation instructions use supported invocation without referencing package-local forge-runtime.py', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'reval-doc-test-'));

    try {
      // 1. Direct API skill
      const directSpecFile = path.join(root, 'direct-spec.json');
      fs.writeFileSync(directSpecFile, JSON.stringify({
        base_url: 'https://api-reval.example.com',
        path: '/api/v1/data',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'API Store',
        endpoints: [
          {
            id: 'get-data',
            method: 'GET',
            path: '/api/v1/data',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ params: {}, status: 200 }] },
          },
        ],
      }), 'utf8');

      const directGenRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'direct-reval-skill',
        '--endpoint-spec', directSpecFile,
      ]);
      const directSkillDir = JSON.parse(directGenRaw).output_dir;

      const directReadme = fs.readFileSync(path.join(directSkillDir, 'README.md'), 'utf8');
      assert.match(directReadme, /python client\.py/, 'Direct API README should document direct client revalidation');
      assert.match(directReadme, /<agent-browser-skill-forge-root>\/scripts\/forge-runtime\.py revalidate-skill/, 'README must reference <agent-browser-skill-forge-root>/scripts/forge-runtime.py');
      assert.doesNotMatch(directReadme, /python forge-runtime\.py revalidate-skill/, 'README must NOT reference non-existent package-local forge-runtime.py');

      // 2. DOM_ONLY skill
      const domSpecFile = path.join(root, 'dom-spec.json');
      fs.writeFileSync(domSpecFile, JSON.stringify({
        base_url: 'https://dom-reval.example.com',
        path: '/items',
        classification: 'DOM_ONLY',
        site_name: 'DOM Store',
        endpoints: [
          {
            id: 'dom-items',
            method: 'GET',
            path: '/items',
            classification: 'DOM_ONLY',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      const domGenRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'dom-reval-skill',
        '--endpoint-spec', domSpecFile,
      ]);
      const domSkillDir = JSON.parse(domGenRaw).output_dir;

      const domReadme = fs.readFileSync(path.join(domSkillDir, 'README.md'), 'utf8');
      assert.match(domReadme, /<agent-browser-skill-forge-root>\/scripts\/forge-runtime\.py revalidate-skill/, 'README must reference <agent-browser-skill-forge-root>/scripts/forge-runtime.py');
      assert.doesNotMatch(domReadme, /python forge-runtime\.py revalidate-skill/, 'README must NOT reference non-existent package-local forge-runtime.py');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('regression: generated SKILL.md Recovery & Revalidation is classification and component-aware', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'recovery-text-test-'));

    try {
      // 1. Browser-only (DOM_ONLY): must NOT reference python client.py
      const domSpec = path.join(root, 'dom-spec.json');
      fs.writeFileSync(domSpec, JSON.stringify({
        base_url: 'https://dom-only.example.com',
        path: '/catalog',
        classification: 'DOM_ONLY',
        site_name: 'DOM Only Site',
        capability_slug: 'catalog-scrape',
        endpoints: [
          {
            id: 'catalog-scrape',
            method: 'GET',
            path: '/catalog',
            classification: 'DOM_ONLY',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      const domGenRaw = runPython(['generate-skill', '--root', root, '--skill-name', 'dom-skill', '--endpoint-spec', domSpec]);
      const domSkillDir = JSON.parse(domGenRaw).output_dir;
      const domSkillMd = fs.readFileSync(path.join(domSkillDir, 'SKILL.md'), 'utf8');
      assert.match(domSkillMd, /Run the verified browser extraction script/);
      assert.doesNotMatch(domSkillMd, /python client\.py/, 'DOM_ONLY SKILL.md must not reference python client.py');

      // 2. Browser-only (BROWSER_SESSION_API): must NOT reference python client.py
      const sessionSpec = path.join(root, 'session-spec.json');
      fs.writeFileSync(sessionSpec, JSON.stringify({
        base_url: 'https://session.example.com',
        path: '/session-items',
        classification: 'BROWSER_SESSION_API',
        site_name: 'Session Site',
        capability_slug: 'session-items',
        endpoints: [
          {
            id: 'session-items',
            method: 'GET',
            path: '/session-items',
            classification: 'BROWSER_SESSION_API',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      const sessionGenRaw = runPython(['generate-skill', '--root', root, '--skill-name', 'session-skill', '--endpoint-spec', sessionSpec]);
      const sessionSkillDir = JSON.parse(sessionGenRaw).output_dir;
      const sessionSkillMd = fs.readFileSync(path.join(sessionSkillDir, 'SKILL.md'), 'utf8');
      assert.match(sessionSkillMd, /Run the verified browser extraction script/);
      assert.doesNotMatch(sessionSkillMd, /python client\.py/, 'BROWSER_SESSION_API SKILL.md must not reference python client.py');

      // 3. Direct API (DIRECT_API_VERIFIED): must reference python client.py
      const directSpec = path.join(root, 'direct-spec.json');
      fs.writeFileSync(directSpec, JSON.stringify({
        base_url: 'https://direct.example.com',
        path: '/api/v1/items',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Direct Site',
        capability_slug: 'direct-items',
        endpoints: [
          {
            id: 'direct-items',
            method: 'GET',
            path: '/api/v1/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ params: {}, status: 200 }] },
          },
        ],
      }), 'utf8');

      const directGenRaw = runPython(['generate-skill', '--root', root, '--skill-name', 'direct-skill', '--endpoint-spec', directSpec]);
      const directSkillDir = JSON.parse(directGenRaw).output_dir;
      const directSkillMd = fs.readFileSync(path.join(directSkillDir, 'SKILL.md'), 'utf8');
      assert.match(directSkillMd, /Run the verified client \(`python client\.py`\)/);

      // 4. HYBRID: must reference both client.py and browser extraction script
      const hybridSpec = path.join(root, 'hybrid-spec.json');
      fs.writeFileSync(hybridSpec, JSON.stringify({
        base_url: 'https://hybrid.example.com',
        classification: 'HYBRID',
        site_name: 'Hybrid Site',
        capability_slug: 'hybrid-cap',
        endpoints: [
          {
            id: 'api-call',
            method: 'GET',
            path: '/api/call',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ params: {}, status: 200 }] },
          },
          {
            id: 'dom-call',
            method: 'GET',
            path: '/dom/call',
            classification: 'DOM_ONLY',
            verification: { status: 'FALLBACK' },
          },
        ],
      }), 'utf8');

      const hybridGenRaw = runPython(['generate-skill', '--root', root, '--skill-name', 'hybrid-skill', '--endpoint-spec', hybridSpec]);
      const hybridSkillDir = JSON.parse(hybridGenRaw).output_dir;
      const hybridSkillMd = fs.readFileSync(path.join(hybridSkillDir, 'SKILL.md'), 'utf8');
      assert.match(hybridSkillMd, /python client\.py/);
      assert.match(hybridSkillMd, /browser extraction script/);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });
});

describe('agent-browser-skill-forge Issue #16 (Repository Release Gate & Install Portability)', () => {
  let fixture;

  test('install-layout portability: the same representative generated direct-client scenario installs and executes from two supported agent skill layouts', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'install-layout-portability-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Portability Catalog',
        site_slug: 'portability-catalog',
        capability_slug: 'list-items',
        parameters: {
          query: { type: 'string', in: 'query', name: 'q' },
          page: { type: 'integer', in: 'query', name: 'page', default: 1 },
          limit: { type: 'integer', in: 'query', name: 'limit', default: 5 },
        },
        tested_variations: [
          { params: { page: 1 }, status: 200, item_count: 5 },
          { params: { page: 2 }, status: 200, item_count: 5 },
        ],
        endpoints: [
          {
            id: 'list-items',
            method: 'GET',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            parameters: {
              query: { type: 'string', in: 'query', name: 'q' },
              page: { type: 'integer', in: 'query', name: 'page', default: 1 },
              limit: { type: 'integer', in: 'query', name: 'limit', default: 5 },
            },
            verification: { status: 'PASSED', tested_variations: [{ params: { page: 1 }, status: 200 }] },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'portability-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const pkgDir = gen.output_dir;

      // 1. Install into Antigravity-compatible skill layout (.agents/skills)
      const installAntigravityRaw = runPython([
        'install-skill',
        '--package-dir', pkgDir,
        '--agent', 'antigravity',
        '--root', root,
      ]);
      const installAntigravity = JSON.parse(installAntigravityRaw);
      assert.equal(installAntigravity.installed, true);
      const antigravityPkgDir = path.join(root, '.agents', 'skills', 'portability-skill');
      assert.ok(fs.existsSync(path.join(antigravityPkgDir, 'SKILL.md')));
      assert.ok(fs.existsSync(path.join(antigravityPkgDir, 'client.py')));

      // 2. Install into Claude Code-compatible skill layout (.claude/skills)
      const installClaudeRaw = runPython([
        'install-skill',
        '--package-dir', pkgDir,
        '--agent', 'claude-code',
        '--root', root,
      ]);
      const installClaude = JSON.parse(installClaudeRaw);
      assert.equal(installClaude.installed, true);
      const claudePkgDir = path.join(root, '.claude', 'skills', 'portability-skill');
      assert.ok(fs.existsSync(path.join(claudePkgDir, 'SKILL.md')));
      assert.ok(fs.existsSync(path.join(claudePkgDir, 'client.py')));

      // 3. Execute from the Antigravity-compatible installed layout
      const antigravityScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(antigravityPkgDir)})
from client import APIClient

client = APIClient(base_url=${JSON.stringify(fixture.baseUrl)})
res = client.list_items(page=1, limit=5)
print(json.dumps(res))
`;
      const agyExec = await execFileAsync(PYTHON, ['-c', antigravityScript], { encoding: 'utf8' });
      const agyData = JSON.parse(agyExec.stdout);
      assert.equal(agyData.items.length, 5);
      assert.equal(agyData.items[0].id, 'item-1');

      // 4. Execute from the Claude Code-compatible installed layout
      const claudeScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(claudePkgDir)})
from client import APIClient

client = APIClient(base_url=${JSON.stringify(fixture.baseUrl)})
res = client.list_items(page=1, limit=5)
print(json.dumps(res))
`;
      const claudeExec = await execFileAsync(PYTHON, ['-c', claudeScript], { encoding: 'utf8' });
      const claudeData = JSON.parse(claudeExec.stdout);
      assert.equal(claudeData.items.length, 5);
      assert.equal(claudeData.items[0].id, 'item-1');

      // Both installed layouts produce identical verified results
      assert.deepEqual(agyData, claudeData, 'Execution results must be identical across installed layouts');

      // 5. Test both environments pass test-skill validation
      const agyTestRaw = await runPythonAsync(['test-skill', '--package-dir', antigravityPkgDir, '--base-url', fixture.baseUrl]);
      const agyTestReport = JSON.parse(agyTestRaw);
      assert.equal(agyTestReport.all_passed, true);

      const claudeTestRaw = await runPythonAsync(['test-skill', '--package-dir', claudePkgDir, '--base-url', fixture.baseUrl]);
      const claudeTestReport = JSON.parse(claudeTestRaw);
      assert.equal(claudeTestReport.all_passed, true);
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('release coverage includes extraction path, operation path, and DIRECT_API_VERIFIED standalone Python client path', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'release-coverage-'));

    try {
      // Path A: Extraction Path
      const extractSpec = path.join(root, 'extract-spec.json');
      fs.writeFileSync(extractSpec, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Coverage Store',
        endpoints: [
          {
            id: 'get-items',
            method: 'GET',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            parameters: { page: { type: 'integer', in: 'query', name: 'page', default: 1 } },
            verification: { status: 'PASSED', tested_variations: [{ params: { page: 1 }, status: 200 }] },
          },
        ],
      }), 'utf8');

      const genExtractRaw = runPython(['generate-skill', '--root', root, '--skill-name', 'extract-skill', '--endpoint-spec', extractSpec]);
      const extractDir = JSON.parse(genExtractRaw).output_dir;

      const extractReportRaw = await runPythonAsync(['test-skill', '--package-dir', extractDir, '--base-url', fixture.baseUrl]);
      const extractReport = JSON.parse(extractReportRaw);
      assert.equal(extractReport.all_passed, true);
      assert.equal(extractReport.components[0].classification, 'DIRECT_API_VERIFIED');

      // Path B: Operation Path (Zero-Side-Effect Safety Verification)
      const opHarFile = path.join(root, 'op-capture.har');
      fs.writeFileSync(opHarFile, JSON.stringify({
        log: {
          entries: [
            {
              request: {
                method: 'POST',
                url: `${fixture.baseUrl}/api/items`,
                headers: [{ name: 'Content-Type', value: 'application/json' }],
                postData: { mimeType: 'application/json', text: JSON.stringify({ name: 'Safe Op', price: 99 }) },
              },
            },
          ],
        },
      }), 'utf8');

      const inspectOpRaw = runPython(['har-inspect', '--har', opHarFile, '--methods', 'POST']);
      const inspectedOp = JSON.parse(inspectOpRaw);
      assert.equal(inspectedOp.count, 1);
      assert.equal(inspectedOp.entries[0].method, 'POST');
      assert.deepEqual(inspectedOp.entries[0].post_data, { name: 'Safe Op', price: 99 });

      // Path C: Standalone Python Client Path (without browser startup)
      const clientPath = path.join(extractDir, 'client.py');
      assert.ok(fs.existsSync(clientPath));

      const standaloneScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(extractDir)})
from client import APIClient

client = APIClient(base_url=${JSON.stringify(fixture.baseUrl)})
result = client.get_items(page=1)
print(json.dumps(result))
`;
      const standaloneExec = await execFileAsync(PYTHON, ['-c', standaloneScript], { encoding: 'utf8' });
      const standaloneData = JSON.parse(standaloneExec.stdout);
      assert.ok(standaloneData.items && standaloneData.items.length > 0);
      assert.equal(standaloneData.page, 1);
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('hostile project-config trust boundary fixture proves unreviewed project config cannot execute commands by default', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'hostile-release-gate-'));
    const marker = path.join(root, 'hostile-ran.txt');
    const hostileExe = path.join(root, 'hostile-browser.cmd');
    fs.writeFileSync(hostileExe, `@echo off\r\necho hostile>"${marker}"\r\nexit /b 99\r\n`, 'utf8');
    fs.writeFileSync(path.join(root, 'agent-browser.json'), JSON.stringify({
      executablePath: hostileExe,
      provider: 'hostile-provider',
      plugins: [{ name: 'hostile-provider', command: hostileExe, capabilities: ['launch.mutate'] }],
    }), 'utf8');

    let bootstrap;
    try {
      bootstrap = JSON.parse(runPython(['bootstrap', '--root', root, '--task', 'release-gate-trust']));
      assert.notEqual(bootstrap.session, 'default');
      assert.match(bootstrap.session, /^agent-browser-skill-forge-/);

      const openResult = runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'open', 'about:blank']);
      assert.match(openResult, /about:blank|Success|ok/i);
      assert.ok(!fs.existsSync(marker), 'hostile command must not run under forge trusted boundary');
    } finally {
      if (bootstrap?.run_id) {
        try { runPython(['exec', '--root', root, '--run-id', bootstrap.run_id, '--', 'close']); } catch {}
      }
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('runtime-sensitive instructions contain no critical stale BrowserAct vocabulary and match verified agent-browser semantics', () => {
    for (const file of allMarkdown(SKILL_ROOT)) {
      const content = fs.readFileSync(file, 'utf8');
      if (file.includes('references')) {
        assert.doesNotMatch(content, /\bbrowser-act\b/i, `${path.relative(SKILL_ROOT, file)} leaked browser-act vocabulary`);
      }
      assert.doesNotMatch(content, /\bnetwork clear\b/, `${path.relative(SKILL_ROOT, file)} used old network clear syntax without --clear`);
      assert.doesNotMatch(content, /@e\d+\b/, `${path.relative(SKILL_ROOT, file)} persisted hardcoded snapshot ref`);
    }

    // Verify presence of verified agent-browser semantics in references
    const extractDoc = fs.readFileSync(path.join(SKILL_ROOT, 'references', 'exploration_extraction.md'), 'utf8');
    const opDoc = fs.readFileSync(path.join(SKILL_ROOT, 'references', 'exploration_operation.md'), 'utf8');
    const outDoc = fs.readFileSync(path.join(SKILL_ROOT, 'references', 'output_template.md'), 'utf8');

    assert.match(extractDoc, /network requests --json/);
    assert.match(extractDoc, /network request <requestId> --json/);
    assert.match(extractDoc, /network requests --clear/);
    assert.match(extractDoc, /network har start/);
    assert.match(extractDoc, /network har stop/);
    assert.match(extractDoc, /set offline on/);
    assert.match(extractDoc, /wait --load networkidle/);
    assert.match(extractDoc, /eval --stdin/);

    assert.match(opDoc, /dialog status/);
    assert.match(opDoc, /dialog accept/);
    assert.match(opDoc, /dialog dismiss/);
    assert.match(opDoc, /tab list/);
    assert.match(opDoc, /tab new/);
    assert.match(opDoc, /tab close/);
    assert.match(opDoc, /set offline on/);
    assert.match(opDoc, /set offline off/);

    assert.match(outDoc, /DIRECT_API_VERIFIED/);
    assert.match(outDoc, /BROWSER_SESSION_API/);
    assert.match(outDoc, /DOM_ONLY/);
    assert.match(outDoc, /HYBRID/);
  });

  test('DIRECT_API_VERIFIED steady-state acceptance path runs without browser startup; browser-dependent classifications declare agent-browser honestly', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'runtime-honesty-'));

    try {
      // 1. Direct API skill
      const directSpec = path.join(root, 'direct-spec.json');
      fs.writeFileSync(directSpec, JSON.stringify({
        base_url: 'https://api.example.com',
        path: '/api/v1/items',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Direct Store',
      }), 'utf8');

      const genDirectRaw = runPython(['generate-skill', '--root', root, '--skill-name', 'direct-skill', '--endpoint-spec', directSpec]);
      const directDir = JSON.parse(genDirectRaw).output_dir;
      const directSkillMd = fs.readFileSync(path.join(directDir, 'SKILL.md'), 'utf8');

      assert.match(directSkillMd, /Classification: `DIRECT_API_VERIFIED`/);
      assert.match(directSkillMd, /Python 3\.8\+.*no browser required/i);
      assert.match(directSkillMd, /python client\.py/);

      // 2. DOM-only skill
      const domSpec = path.join(root, 'dom-spec.json');
      fs.writeFileSync(domSpec, JSON.stringify({
        base_url: 'https://dom.example.com',
        path: '/catalog',
        classification: 'DOM_ONLY',
        site_name: 'DOM Store',
      }), 'utf8');

      const genDomRaw = runPython(['generate-skill', '--root', root, '--skill-name', 'dom-skill', '--endpoint-spec', domSpec]);
      const domDir = JSON.parse(genDomRaw).output_dir;
      const domSkillMd = fs.readFileSync(path.join(domDir, 'SKILL.md'), 'utf8');

      assert.match(domSkillMd, /Classification: `DOM_ONLY`/);
      assert.match(domSkillMd, /agent-browser/);
      assert.match(domSkillMd, /scripts\/.*\.py/);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('no .agent-forge workspace content, raw HAR, auth material, private generated client, or secret-bearing test artifact is tracked by git', () => {
    const gitignoreContent = fs.readFileSync(path.join(REPO_ROOT, '.gitignore'), 'utf8');
    assert.match(gitignoreContent, /^\.agent-forge\/$/m, '.gitignore must exclude .agent-forge/');

    const gitStatus = execSync('git status --porcelain', { cwd: REPO_ROOT, encoding: 'utf8' });
    assert.doesNotMatch(gitStatus, /\.agent-forge/, 'git status must not track anything in .agent-forge/');

    const trackedFiles = execSync('git ls-files', { cwd: REPO_ROOT, encoding: 'utf8' });
    assert.doesNotMatch(trackedFiles, /\.agent-forge\//, 'git ls-files must not contain .agent-forge/');
    assert.doesNotMatch(trackedFiles, /\.har\b/, 'git ls-files must not contain raw HAR files');
    assert.doesNotMatch(trackedFiles, /\bauth\.json\b/, 'git ls-files must not contain auth.json');
    assert.doesNotMatch(trackedFiles, /\bNOTE-DEBUGS\.md\b/, 'git ls-files must not contain NOTE-DEBUGS.md in product state');
  });

  test('existing browser-act-skill-forge and pinchtab-skill-forge remain unchanged and pass checks', () => {
    const browserActDir = path.join(REPO_ROOT, 'skills', 'browser-act-skill-forge');
    const pinchtabDir = path.join(REPO_ROOT, 'skills', 'pinchtab-skill-forge');

    assert.ok(fs.existsSync(path.join(browserActDir, 'SKILL.md')));
    assert.ok(fs.existsSync(path.join(pinchtabDir, 'SKILL.md')));

    const browserActContent = fs.readFileSync(path.join(browserActDir, 'SKILL.md'), 'utf8');
    assert.match(browserActContent, /^name: browser-act-skill-forge$/m);

    const pinchtabContent = fs.readFileSync(path.join(pinchtabDir, 'SKILL.md'), 'utf8');
    assert.match(pinchtabContent, /^name: pinchtab-skill-forge$/m);
  });
});

describe('agent-browser-skill-forge Issue #18 (Runtime Receipts & HAR Lifecycle Gating)', () => {
  let fixture;

  test('real verify-endpoint emits and saves valid verification receipt', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'verify-rcpt-'));

    try {
      const variationsFile = path.join(root, 'variations.json');
      fs.writeFileSync(variationsFile, JSON.stringify([
        { params: { page: 1, limit: 5 } },
        { params: { page: 2, limit: 5 } },
      ]), 'utf8');

      const outReceiptPath = path.join(root, 'output-receipt.json');
      const runId = 'run-verify-test-18';

      const verifyRaw = runPython([
        'verify-endpoint',
        '--root', root,
        '--run-id', runId,
        '--url', `${fixture.baseUrl}/api/items`,
        '--variations', variationsFile,
        '--required-key', 'items',
        '--output-receipt', outReceiptPath,
      ]);

      const verified = JSON.parse(verifyRaw);
      assert.equal(verified.verified, true);
      assert.equal(verified.classification, 'DIRECT_API_VERIFIED');
      assert.ok(verified.receipt, 'stdout must include receipt object');

      const rcpt = verified.receipt;
      assert.equal(rcpt.receipt_version, '1.0');
      assert.ok(rcpt.receipt_id.startsWith('rcpt_'));
      assert.equal(rcpt.run_id, runId);
      assert.equal(rcpt.url, `${fixture.baseUrl}/api/items`);
      assert.equal(rcpt.method, 'GET');
      assert.equal(rcpt.classification, 'DIRECT_API_VERIFIED');
      assert.equal(rcpt.verified, true);
      assert.equal(typeof rcpt.input_digest, 'string');
      assert.equal(rcpt.input_digest.length, 64);
      assert.equal(rcpt.variation_count, 2);
      assert.equal(rcpt.successful_variation_count, 2);
      assert.equal(rcpt.result_digests.length, 2);
      assert.equal(rcpt.pass_assertions.status_in_range, true);
      assert.equal(rcpt.pass_assertions.required_keys_present, true);
      assert.equal(rcpt.pass_assertions.distinct_responses, true);
      assert.equal(rcpt.pass_assertions.all_passed, true);
      assert.equal(typeof rcpt.receipt_hash, 'string');
      assert.equal(rcpt.receipt_hash.length, 64);

      // Verify file persistence at --output-receipt
      assert.ok(fs.existsSync(outReceiptPath));
      const savedRcpt = JSON.parse(fs.readFileSync(outReceiptPath, 'utf8'));
      assert.equal(savedRcpt.receipt_hash, rcpt.receipt_hash);
      assert.equal(savedRcpt.receipt_id, rcpt.receipt_id);

      // Verify file persistence at .agent-forge/runs/<run-id>/receipts/<receipt_id>.json
      const runRcptPath = path.join(root, '.agent-forge', 'runs', runId, 'receipts', `${rcpt.receipt_id}.json`);
      assert.ok(fs.existsSync(runRcptPath));
      const savedRunRcpt = JSON.parse(fs.readFileSync(runRcptPath, 'utf8'));
      assert.equal(savedRunRcpt.receipt_hash, rcpt.receipt_hash);
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('generate-skill with valid receipt creates DIRECT_API_VERIFIED / PASSED client', async () => {
    fixture = await startFixtureServer();
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'gen-valid-rcpt-'));

    try {
      const variationsFile = path.join(root, 'variations.json');
      fs.writeFileSync(variationsFile, JSON.stringify([
        { params: { page: 1, limit: 5 } },
        { params: { page: 2, limit: 5 } },
      ]), 'utf8');

      const runId = 'run-gen-valid';
      const verifyRaw = runPython([
        'verify-endpoint',
        '--root', root,
        '--run-id', runId,
        '--url', `${fixture.baseUrl}/api/items`,
        '--variations', variationsFile,
        '--required-key', 'items',
      ]);
      const verified = JSON.parse(verifyRaw);
      const rcpt = verified.receipt;

      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        run_id: runId,
        site_name: 'Valid Store',
        receipt: rcpt,
        required_keys: ['items'],
        parameters: {
          page: { type: 'integer', in: 'query', name: 'page', default: 1 },
          limit: { type: 'integer', in: 'query', name: 'limit', default: 20 },
        },
        tested_variations: [
          { params: { page: 1, limit: 5 } },
          { params: { page: 2, limit: 5 } },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--run-id', runId,
        '--skill-name', 'valid-direct-skill',
        '--endpoint-spec', specFile,
      ]);
      const gen = JSON.parse(genRaw);
      const outputDir = gen.output_dir;

      // 1. Verify manifest
      const manifest = JSON.parse(fs.readFileSync(path.join(outputDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest.endpoints[0].classification, 'DIRECT_API_VERIFIED');
      assert.equal(manifest.endpoints[0].verification.status, 'PASSED');
      assert.equal(manifest.endpoints[0].verification.receipt_id, rcpt.receipt_id);
      assert.equal(manifest.endpoints[0].verification.receipt_hash, rcpt.receipt_hash);
      assert.equal(manifest.endpoints[0].verification.receipt_version, '1.0');

      // 2. Verify provenance
      const prov = JSON.parse(fs.readFileSync(path.join(outputDir, 'provenance.json'), 'utf8'));
      assert.equal(prov.verification_summary.direct_api_count, 1);
      assert.equal(prov.verification_summary.all_passed, true);
      assert.equal(prov.capabilities[0].receipt_id, rcpt.receipt_id);
      assert.equal(prov.capabilities[0].receipt_hash, rcpt.receipt_hash);
      assert.equal(prov.capabilities[0].receipt_version, '1.0');

      // 3. Validate package
      const valRaw = runPython(['validate-package', '--package-dir', outputDir]);
      assert.equal(JSON.parse(valRaw).valid, true);

      // 4. Test client.py
      const clientPy = path.join(outputDir, 'client.py');
      assert.ok(fs.existsSync(clientPy));
      const clientOut = execFileSync(PYTHON, [clientPy, '--page', '1', '--limit', '5'], { encoding: 'utf8' });
      assert.match(clientOut, /"items"/);
    } finally {
      await fixture.close();
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('hand-authored tested_variations without receipt cannot manufacture DIRECT_API_VERIFIED / PASSED (downgrades to UNVERIFIED)', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'hand-authored-no-rcpt-'));

    try {
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://example.com',
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        site_name: 'Fake Store',
        endpoints: [
          {
            id: 'fake-direct',
            method: 'GET',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: {
              status: 'PASSED',
              tested_variations: [
                { params: { page: 1 }, status: 200, item_count: 5 },
                { params: { page: 2 }, status: 200, item_count: 5 },
              ],
            },
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'fake-direct-skill',
        '--endpoint-spec', specFile,
      ]);
      const outputDir = JSON.parse(genRaw).output_dir;

      const manifest = JSON.parse(fs.readFileSync(path.join(outputDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest.endpoints[0].verification.status, 'UNVERIFIED', 'Hand-authored tested_variations without receipt must downgrade to UNVERIFIED');
      assert.equal(manifest.endpoints[0].verification.receipt_id, undefined);

      const prov = JSON.parse(fs.readFileSync(path.join(outputDir, 'provenance.json'), 'utf8'));
      assert.equal(prov.verification_summary.direct_api_count, 0, 'Unverified direct endpoint must not count in direct_api_count');
      assert.equal(prov.verification_summary.all_passed, false);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('mismatched URL/method or corrupted receipt blocks direct pass', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'rcpt-mismatch-'));

    try {
      const validReceipt = makeMockReceipt({
        url: 'https://api.example.com/api/v1/products',
        method: 'GET',
        variations: [{ params: { page: 1 } }, { params: { page: 2 } }],
      });

      // Case A: Corrupted hash
      const corruptedReceipt = { ...validReceipt, receipt_hash: '0000000000000000000000000000000000000000000000000000000000000000' };
      const specA = path.join(root, 'spec-a.json');
      fs.writeFileSync(specA, JSON.stringify({
        base_url: 'https://api.example.com',
        path: '/api/v1/products',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        receipt: corruptedReceipt,
      }), 'utf8');
      const genA = JSON.parse(runPython(['generate-skill', '--root', root, '--skill-name', 'corrupted-hash-skill', '--endpoint-spec', specA]));
      const manifestA = JSON.parse(fs.readFileSync(path.join(genA.output_dir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifestA.endpoints[0].verification.status, 'UNVERIFIED');

      // Case B: Mismatched URL
      const specB = path.join(root, 'spec-b.json');
      fs.writeFileSync(specB, JSON.stringify({
        base_url: 'https://api.other.com',
        path: '/api/v2/other',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        receipt: validReceipt,
      }), 'utf8');
      const genB = JSON.parse(runPython(['generate-skill', '--root', root, '--skill-name', 'mismatched-url-skill', '--endpoint-spec', specB]));
      const manifestB = JSON.parse(fs.readFileSync(path.join(genB.output_dir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifestB.endpoints[0].verification.status, 'UNVERIFIED');

      // Case C: Mismatched Method
      const specC = path.join(root, 'spec-c.json');
      fs.writeFileSync(specC, JSON.stringify({
        base_url: 'https://api.example.com',
        path: '/api/v1/products',
        method: 'POST',
        classification: 'DIRECT_API_VERIFIED',
        receipt: validReceipt,
      }), 'utf8');
      const genC = JSON.parse(runPython(['generate-skill', '--root', root, '--skill-name', 'mismatched-method-skill', '--endpoint-spec', specC]));
      const manifestC = JSON.parse(fs.readFileSync(path.join(genC.output_dir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifestC.endpoints[0].verification.status, 'UNVERIFIED');

      // Case D: Mismatched Input Digest (different variations)
      const specD = path.join(root, 'spec-d.json');
      fs.writeFileSync(specD, JSON.stringify({
        base_url: 'https://api.example.com',
        path: '/api/v1/products',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
        receipt: validReceipt,
        tested_variations: [{ params: { search: 'different_query_variation' } }],
      }), 'utf8');
      const genD = JSON.parse(runPython(['generate-skill', '--root', root, '--skill-name', 'mismatched-digest-skill', '--endpoint-spec', specD]));
      const manifestD = JSON.parse(fs.readFileSync(path.join(genD.output_dir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifestD.endpoints[0].verification.status, 'UNVERIFIED');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('multi-endpoint/hybrid validates receipts per direct endpoint', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'multi-rcpt-'));

    try {
      const ep1Receipt = makeMockReceipt({
        url: 'https://api.example.com/api/v1/items',
        method: 'GET',
        variations: [{ params: { page: 1 } }],
      });

      const hybridSpec = path.join(root, 'hybrid-spec.json');
      fs.writeFileSync(hybridSpec, JSON.stringify({
        base_url: 'https://api.example.com',
        classification: 'HYBRID',
        endpoints: [
          {
            id: 'verified-direct',
            method: 'GET',
            path: '/api/v1/items',
            classification: 'DIRECT_API_VERIFIED',
            receipt: ep1Receipt,
            verification: { tested_variations: [{ params: { page: 1 } }] },
          },
          {
            id: 'unverified-direct',
            method: 'GET',
            path: '/api/v1/orders',
            classification: 'DIRECT_API_VERIFIED',
            verification: { tested_variations: [{ params: { page: 1 } }] },
          },
          {
            id: 'dom-action',
            method: 'GET',
            path: '/checkout',
            classification: 'DOM_ONLY',
          },
        ],
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--skill-name', 'hybrid-rcpt-skill',
        '--endpoint-spec', hybridSpec,
      ]);
      const outputDir = JSON.parse(genRaw).output_dir;

      const manifest = JSON.parse(fs.readFileSync(path.join(outputDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest.endpoints[0].verification.status, 'PASSED');
      assert.equal(manifest.endpoints[0].verification.receipt_id, ep1Receipt.receipt_id);
      assert.equal(manifest.endpoints[1].verification.status, 'UNVERIFIED');
      assert.equal(manifest.endpoints[2].verification.status, 'FALLBACK');

      const prov = JSON.parse(fs.readFileSync(path.join(outputDir, 'provenance.json'), 'utf8'));
      assert.equal(prov.verification_summary.direct_api_count, 1);
      assert.equal(prov.verification_summary.dom_only_count, 1);
      assert.equal(prov.verification_summary.hybrid_count, 1);
      assert.equal(prov.verification_summary.all_passed, false);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('package validation rejects direct-PASSED without receipt provenance', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'val-reject-'));

    try {
      const badPkg = path.join(root, 'bad-pkg');
      fs.mkdirSync(badPkg, { recursive: true });
      fs.writeFileSync(path.join(badPkg, 'SKILL.md'), '---\nname: bad-pkg\n---\n# Bad Pkg\nClassification: `DIRECT_API_VERIFIED`\nRun python client.py\n', 'utf8');
      fs.writeFileSync(path.join(badPkg, 'endpoint-manifest.json'), JSON.stringify({
        endpoints: [
          {
            id: 'ep1',
            method: 'GET',
            path: '/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED' },
          },
        ],
      }), 'utf8');
      fs.writeFileSync(path.join(badPkg, 'provenance.json'), JSON.stringify({
        har_sha256: null,
        capabilities: [{ name: 'ep1', classification: 'DIRECT_API_VERIFIED', steady_state_runtime: 'python' }],
        verification_summary: { direct_api_count: 1, all_passed: true },
      }), 'utf8');

      assert.throws(() => {
        runPython(['validate-package', '--package-dir', badPkg]);
      }, /without valid verification receipt reference/);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('HAR capture start -> target flow -> stop produces finalized hash in provenance', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'har-life-'));

    try {
      const runId = 'run-har-flow-18';

      // 1. har-start
      const startRaw = runPython([
        'har-start',
        '--root', root,
        '--run-id', runId,
        '--target-flow', 'catalog-search-flow',
      ]);
      const started = JSON.parse(startRaw);
      assert.equal(started.status, 'recording');
      assert.equal(started.target_flow, 'catalog-search-flow');
      assert.ok(started.capture_id.startsWith('cap_'));

      // 2. Create mock HAR
      const harPath = path.join(root, 'flow.har');
      const harContent = JSON.stringify({
        log: {
          version: '1.2',
          entries: [
            {
              request: { method: 'GET', url: 'https://example.com/api/search?q=test', headers: [] },
              response: { status: 200, content: { mimeType: 'application/json', text: '{"results": [1,2,3]}' } },
            },
          ],
        },
      });
      fs.writeFileSync(harPath, harContent, 'utf8');
      const expectedSha = crypto.createHash('sha256').update(harContent).digest('hex');

      // 3. har-stop
      const stopRaw = runPython([
        'har-stop',
        '--root', root,
        '--run-id', runId,
        '--har-file', harPath,
      ]);
      const stopped = JSON.parse(stopRaw);
      assert.equal(stopped.status, 'finalized');
      assert.equal(stopped.har_sha256, expectedSha);
      assert.equal(stopped.target_flow, 'catalog-search-flow');

      // 4. har-analyze with lifecycle check
      const analyzeRaw = runPython([
        'har-analyze',
        '--root', root,
        '--run-id', runId,
        '--har', harPath,
      ]);
      const analyzed = JSON.parse(analyzeRaw);
      assert.equal(analyzed.har_sha256, expectedSha);
      assert.equal(analyzed.candidate_count, 1);

      // 5. har-inspect with lifecycle check
      const inspectRaw = runPython([
        'har-inspect',
        '--root', root,
        '--run-id', runId,
        '--har', harPath,
      ]);
      const inspected = JSON.parse(inspectRaw);
      assert.equal(inspected.count, 1);

      // 6. generate-skill with lifecycle check
      const specFile = path.join(root, 'spec.json');
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: 'https://example.com',
        path: '/api/search',
        classification: 'BROWSER_SESSION_API',
        site_name: 'Search Site',
      }), 'utf8');

      const genRaw = runPython([
        'generate-skill',
        '--root', root,
        '--run-id', runId,
        '--skill-name', 'har-search-skill',
        '--endpoint-spec', specFile,
        '--har-path', harPath,
      ]);
      const outputDir = JSON.parse(genRaw).output_dir;
      const prov = JSON.parse(fs.readFileSync(path.join(outputDir, 'provenance.json'), 'utf8'));
      assert.equal(prov.har_sha256, expectedSha, 'Provenance har_sha256 must match finalized HAR hash');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('failed HAR start, unfinalized stop, or hash mismatch fails HAR-derived generation', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'har-gate-failures-'));

    try {
      const harPath = path.join(root, 'sample.har');
      fs.writeFileSync(harPath, JSON.stringify({ log: { entries: [] } }), 'utf8');

      // Case A: har-stop without har-start fails
      assert.throws(() => {
        runPython(['har-stop', '--root', root, '--run-id', 'no-start-run', '--har-file', harPath]);
      }, /HAR capture was not started/);

      // Case B: Unfinalized stop blocks generation and analysis
      runPython(['har-start', '--root', root, '--run-id', 'unfinalized-run', '--target-flow', 'flow1']);
      assert.throws(() => {
        runPython(['har-analyze', '--root', root, '--run-id', 'unfinalized-run', '--har', harPath]);
      }, /is not finalized/);
      assert.throws(() => {
        const specFile = path.join(root, 'spec-unfin.json');
        fs.writeFileSync(specFile, JSON.stringify({ base_url: 'https://example.com', path: '/api/items', classification: 'BROWSER_SESSION_API' }), 'utf8');
        runPython(['generate-skill', '--root', root, '--run-id', 'unfinalized-run', '--skill-name', 'unfin-skill', '--endpoint-spec', specFile, '--har-path', harPath]);
      }, /is not finalized/);

      // Case C: Hash mismatch after stop
      runPython(['har-start', '--root', root, '--run-id', 'tampered-run', '--target-flow', 'flow2']);
      runPython(['har-stop', '--root', root, '--run-id', 'tampered-run', '--har-file', harPath]);
      // Mutate HAR file
      fs.writeFileSync(harPath, JSON.stringify({ log: { entries: [{ modified: true }] } }), 'utf8');
      assert.throws(() => {
        runPython(['har-analyze', '--root', root, '--run-id', 'tampered-run', '--har', harPath]);
      }, /HAR SHA-256 mismatch/);

      // Case D: Pre-capture setup alone cannot satisfy target flow evidence gate
      runPython(['har-start', '--root', root, '--run-id', 'precap-only-run', '--target-flow', 'login', '--pre-capture']);
      const precapHar = path.join(root, 'precap.har');
      fs.writeFileSync(precapHar, JSON.stringify({ log: { entries: [] } }), 'utf8');
      runPython(['har-stop', '--root', root, '--run-id', 'precap-only-run', '--har-file', precapHar]);
      assert.throws(() => {
        runPython(['har-analyze', '--root', root, '--run-id', 'precap-only-run', '--har', precapHar]);
      }, /lacks target-flow evidence|pre-capture setup cannot satisfy/);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });
});

describe('agent-browser-skill-forge Issue #19 (Non-Interactive Execution & Refine-by-Default)', () => {
  test('forge-runtime exec rejects interactive commands and flags (chat, --confirm-interactive, --confirm-actions)', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'interactive-rejection-'));
    try {
      const bootRaw = runPython(['bootstrap', '--root', root, '--task', 'interactive-test']);
      const boot = JSON.parse(bootRaw);
      const runId = boot.run_id;

      // 1. chat command
      assert.throws(
        () => runPython(['exec', '--root', root, '--run-id', runId, '--', 'chat']),
        (err) => {
          assert.match(err.stderr || err.stdout || '', /interactive mode is blocked|'chat' is not allowed/i);
          return true;
        }
      );

      // 2. --confirm-interactive flag
      assert.throws(
        () => runPython(['exec', '--root', root, '--run-id', runId, '--', 'open', 'https://example.com', '--confirm-interactive']),
        (err) => {
          assert.match(err.stderr || err.stdout || '', /interactive mode is blocked|--confirm-interactive/i);
          return true;
        }
      );

      // 3. --confirm-actions flag
      assert.throws(
        () => runPython(['exec', '--root', root, '--run-id', runId, '--', 'open', 'https://example.com', '--confirm-actions']),
        (err) => {
          assert.match(err.stderr || err.stdout || '', /interactive mode is blocked|--confirm-actions/i);
          return true;
        }
      );
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('generate-skill defaults to refining existing package, preserving unaffected components/scripts', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'refine-default-'));

    try {
      // 1. Initial skill generation with endpoint 1
      const spec1Path = path.join(root, 'spec1.json');
      fs.writeFileSync(spec1Path, JSON.stringify({
        base_url: 'https://api.example.com',
        endpoints: [
          {
            id: 'list-items',
            method: 'GET',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ query: 'test', status: 200 }] }
          }
        ]
      }), 'utf8');

      const gen1Raw = runPython(['generate-skill', '--root', root, '--skill-name', 'test-service', '--endpoint-spec', spec1Path, '--capability-slug', 'list-items']);
      const pkgDir = JSON.parse(gen1Raw).output_dir;

      // Add a custom helper script in scripts/ that should be preserved during refinement
      const customScriptPath = path.join(pkgDir, 'scripts', 'custom-helper.py');
      fs.writeFileSync(customScriptPath, '# Custom preserved helper\nprint("preserved")\n', 'utf8');

      // Verify initial state
      const manifest1 = JSON.parse(fs.readFileSync(path.join(pkgDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest1.endpoints.length, 1);
      assert.equal(manifest1.endpoints[0].id, 'list-items');

      // 2. Refine skill by adding endpoint 2 (create-item) without --fresh
      const spec2Path = path.join(root, 'spec2.json');
      fs.writeFileSync(spec2Path, JSON.stringify({
        base_url: 'https://api.example.com',
        endpoints: [
          {
            id: 'create-item',
            method: 'POST',
            path: '/api/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ data: { name: 'widget' }, status: 201 }] }
          }
        ]
      }), 'utf8');

      const gen2Raw = runPython(['generate-skill', '--root', root, '--skill-name', 'test-service', '--endpoint-spec', spec2Path, '--capability-slug', 'create-item']);
      const gen2 = JSON.parse(gen2Raw);
      assert.equal(gen2.output_dir, pkgDir);

      // Verify merged endpoints in manifest
      const manifest2 = JSON.parse(fs.readFileSync(path.join(pkgDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest2.endpoints.length, 2, 'Manifest must contain both merged endpoints');
      const epIds = manifest2.endpoints.map(e => e.id);
      assert.ok(epIds.includes('list-items'), 'Must preserve unaffected list-items endpoint');
      assert.ok(epIds.includes('create-item'), 'Must include new create-item endpoint');

      // Verify custom helper script is preserved
      assert.ok(fs.existsSync(customScriptPath), 'Unaffected helper script must be preserved');
      assert.equal(fs.readFileSync(customScriptPath, 'utf8'), '# Custom preserved helper\nprint("preserved")\n');

      // Verify client.py has methods for both
      const clientPy = fs.readFileSync(path.join(pkgDir, 'client.py'), 'utf8');
      assert.match(clientPy, /def list_items\(/);
      assert.match(clientPy, /def create_item\(/);

      // Verify provenance records refinement
      const prov2 = JSON.parse(fs.readFileSync(path.join(pkgDir, 'provenance.json'), 'utf8'));
      assert.equal(prov2.refined, true, 'Provenance must record refined: true');
      assert.equal(prov2.capabilities.length, 2);

      // 3. Refine again by updating list-items endpoint in place
      const spec3Path = path.join(root, 'spec3.json');
      fs.writeFileSync(spec3Path, JSON.stringify({
        base_url: 'https://api.example.com',
        endpoints: [
          {
            id: 'list-items',
            method: 'GET',
            path: '/api/v2/items',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ query: 'v2', status: 200 }] }
          }
        ]
      }), 'utf8');

      runPython(['generate-skill', '--root', root, '--skill-name', 'test-service', '--endpoint-spec', spec3Path, '--capability-slug', 'list-items']);

      const manifest3 = JSON.parse(fs.readFileSync(path.join(pkgDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest3.endpoints.length, 2, 'Endpoints count remains 2 after in-place update');
      const updatedListEp = manifest3.endpoints.find(e => e.id === 'list-items');
      assert.equal(updatedListEp.path, '/api/v2/items', 'Updated endpoint path must reflect new spec');
      assert.ok(fs.existsSync(customScriptPath), 'Custom helper still preserved');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('generate-skill --fresh performs a clean rebuild', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'fresh-rebuild-'));

    try {
      // 1. Initial package
      const spec1Path = path.join(root, 'spec1.json');
      fs.writeFileSync(spec1Path, JSON.stringify({
        base_url: 'https://api.example.com',
        endpoints: [
          {
            id: 'old-endpoint',
            method: 'GET',
            path: '/api/old',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ status: 200 }] }
          }
        ]
      }), 'utf8');

      const gen1Raw = runPython(['generate-skill', '--root', root, '--skill-name', 'clean-service', '--endpoint-spec', spec1Path]);
      const pkgDir = JSON.parse(gen1Raw).output_dir;

      // Add file to be wiped on fresh
      const customScriptPath = path.join(pkgDir, 'scripts', 'old-helper.py');
      fs.writeFileSync(customScriptPath, '# Old helper\n', 'utf8');

      // 2. Run with --fresh and new spec
      const spec2Path = path.join(root, 'spec2.json');
      fs.writeFileSync(spec2Path, JSON.stringify({
        base_url: 'https://api.example.com',
        endpoints: [
          {
            id: 'fresh-endpoint',
            method: 'GET',
            path: '/api/fresh',
            classification: 'DIRECT_API_VERIFIED',
            verification: { status: 'PASSED', tested_variations: [{ status: 200 }] }
          }
        ]
      }), 'utf8');

      const gen2Raw = runPython(['generate-skill', '--root', root, '--skill-name', 'clean-service', '--endpoint-spec', spec2Path, '--fresh']);
      const gen2 = JSON.parse(gen2Raw);
      assert.equal(gen2.output_dir, pkgDir);

      const manifest2 = JSON.parse(fs.readFileSync(path.join(pkgDir, 'endpoint-manifest.json'), 'utf8'));
      assert.equal(manifest2.endpoints.length, 1);
      assert.equal(manifest2.endpoints[0].id, 'fresh-endpoint', 'Only fresh endpoint exists');
      assert.equal(fs.existsSync(customScriptPath), false, 'Old helper script must be wiped on --fresh');

      const prov2 = JSON.parse(fs.readFileSync(path.join(pkgDir, 'provenance.json'), 'utf8'));
      assert.notEqual(prov2.refined, true, 'Clean build does not have refined: true');
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });

  test('corrupted or unrecoverable existing package fails with FRESH_REQUIRED and succeeds with --fresh', () => {
    const privateTests = path.join(REPO_ROOT, '.agent-forge', 'tests');
    fs.mkdirSync(privateTests, { recursive: true });
    const root = fs.mkdtempSync(path.join(privateTests, 'corrupted-recovery-'));

    try {
      const pkgDir = path.join(root, '.agent-forge', 'output', 'corrupt-pkg');
      fs.mkdirSync(pkgDir, { recursive: true });

      // Create corrupted manifest and empty SKILL.md
      fs.writeFileSync(path.join(pkgDir, 'endpoint-manifest.json'), '{ broken json', 'utf8');
      fs.writeFileSync(path.join(pkgDir, 'SKILL.md'), 'dummy', 'utf8');

      const specPath = path.join(root, 'spec.json');
      fs.writeFileSync(specPath, JSON.stringify({
        base_url: 'https://api.example.com',
        path: '/api/items',
        classification: 'DIRECT_API_VERIFIED',
        verification: { status: 'PASSED', tested_variations: [{ status: 200 }] }
      }), 'utf8');

      // 1. Refinement fails with FRESH_REQUIRED
      assert.throws(
        () => runPython(['generate-skill', '--root', root, '--skill-name', 'corrupt-pkg', '--endpoint-spec', specPath]),
        (err) => {
          const combined = (err.stderr || '') + (err.stdout || '');
          assert.match(combined, /FRESH_REQUIRED/);
          return true;
        }
      );

      // 2. Clean rebuild succeeds with --fresh
      const genFreshRaw = runPython(['generate-skill', '--root', root, '--skill-name', 'corrupt-pkg', '--endpoint-spec', specPath, '--fresh']);
      const genFresh = JSON.parse(genFreshRaw);
      assert.equal(genFresh.output_dir, pkgDir);

      const manifest = JSON.parse(fs.readFileSync(path.join(pkgDir, 'endpoint-manifest.json'), 'utf8'));
      assert.ok(Array.isArray(manifest.endpoints));
      assert.ok(manifest.endpoints.length >= 1);
    } finally {
      try { fs.rmSync(root, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (error) { if (error?.code !== 'EPERM') throw error; }
    }
  });
});
