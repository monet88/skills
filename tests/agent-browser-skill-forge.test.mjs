import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync, execSync, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);

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
      assert.equal(parsed.entries[0].headers['X-CSRF-Token'], 'token-123');
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
