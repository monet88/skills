import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, execSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

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
      fs.writeFileSync(specFile, JSON.stringify({
        base_url: fixture.baseUrl,
        path: '/api/items',
        method: 'GET',
        classification: 'DIRECT_API_VERIFIED',
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
