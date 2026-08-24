import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..');

function parseFrontmatter(content) {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  const lines = match[1].split(/\r?\n/);
  const data = {};
  for (const line of lines) {
    const colonIdx = line.indexOf(':');
    if (colonIdx !== -1) {
      const key = line.slice(0, colonIdx).trim();
      let value = line.slice(colonIdx + 1).trim();
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      }
      data[key] = value;
    }
  }
  return { data, body: content.slice(match[0].length).trim() };
}

function parseOpenAiYaml(content) {
  const lines = content.split(/\r?\n/);
  const result = { interface: {}, policy: { products: [] } };
  let currentSection = null;
  let currentListKey = null;
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    if (trimmed === 'interface:') {
      currentSection = 'interface';
      currentListKey = null;
      continue;
    }
    if (trimmed === 'policy:') {
      currentSection = 'policy';
      currentListKey = null;
      continue;
    }
    if (currentSection === 'policy' && trimmed.startsWith('products:')) {
      currentListKey = 'products';
      continue;
    }
    if (currentListKey === 'products' && trimmed.startsWith('-')) {
      const item = trimmed.slice(1).trim().replace(/^["']|["']$/g, '');
      result.policy.products.push(item);
      continue;
    }
    const colonIdx = trimmed.indexOf(':');
    if (colonIdx !== -1 && currentSection) {
      currentListKey = null;
      const key = trimmed.slice(0, colonIdx).trim();
      let value = trimmed.slice(colonIdx + 1).trim();
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      } else if (value === 'true') {
        value = true;
      } else if (value === 'false') {
        value = false;
      }
      result[currentSection][key] = value;
    }
  }
  return result;
}

function listFilesRecursive(dir, base = '') {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const relPath = base ? path.join(base, entry.name) : entry.name;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...listFilesRecursive(fullPath, relPath));
    } else {
      results.push(relPath);
    }
  }
  return results;
}

describe('Ask Impeccable Acceptance Suite', () => {
  let tempTestDir;

  before(() => {
    tempTestDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ask-impeccable-acceptance-'));
  });

  after(() => {
    if (tempTestDir && fs.existsSync(tempTestDir)) {
      fs.rmSync(tempTestDir, { recursive: true, force: true });
    }
  });

  test('CLI discovers ask-impeccable from local repository', () => {
    const output = execSync(`npx skills add "${REPO_ROOT}" -l`, {
      encoding: 'utf8',
      timeout: 30000,
    });

    assert.match(output, /ask-impeccable/, 'CLI should list ask-impeccable');
    assert.match(output, /Coordinator for Impeccable UI workflows/i, 'CLI should show the Impeccable coordinator description');
  });

  test('Source repository contains required agents/openai.yaml metadata and policy with products', () => {
    const sourceYamlPath = path.join(REPO_ROOT, 'skills', 'ask-impeccable', 'agents', 'openai.yaml');
    assert.ok(fs.existsSync(sourceYamlPath), `Source agents/openai.yaml must exist at ${sourceYamlPath}`);

    const content = fs.readFileSync(sourceYamlPath, 'utf8');
    const parsed = parseOpenAiYaml(content);
    assert.ok(parsed.interface.display_name, 'display_name must be defined');
    assert.match(parsed.interface.display_name, /Ask Impeccable/i);
    assert.match(parsed.interface.short_description, /Frontend|UI/i, 'short_description must target frontend/UI routing');
    assert.match(parsed.interface.default_prompt, /ask-impeccable/i, 'default_prompt must support explicit invocation');
    assert.equal(parsed.policy.allow_implicit_invocation, true, 'policy must set allow_implicit_invocation: true');
    assert.deepEqual(parsed.policy.products, ['chatgpt', 'codex'], 'policy.products must contain chatgpt and codex');
  });

  test('Installs into isolated temporary environment for Antigravity with agents/openai.yaml, policy, and products bundled', () => {
    const agentTempDir = path.join(tempTestDir, 'antigravity-env');
    fs.mkdirSync(agentTempDir, { recursive: true });

    execSync(`npx skills add "${REPO_ROOT}" --agent antigravity --copy -y`, {
      cwd: agentTempDir,
      encoding: 'utf8',
      timeout: 30000,
    });

    const skillDir = path.join(agentTempDir, '.agents', 'skills', 'ask-impeccable');
    const installedSkillPath = path.join(skillDir, 'SKILL.md');
    const installedYamlPath = path.join(skillDir, 'agents', 'openai.yaml');

    assert.ok(fs.existsSync(installedSkillPath), `Expected installed SKILL.md at ${installedSkillPath}`);
    assert.ok(fs.existsSync(installedYamlPath), `Expected installed agents/openai.yaml at ${installedYamlPath}`);

    const skillContent = fs.readFileSync(installedSkillPath, 'utf8');
    const parsedSkill = parseFrontmatter(skillContent);
    assert.ok(parsedSkill, 'Installed SKILL.md must have valid YAML frontmatter');
    assert.equal(parsedSkill.data.name, 'ask-impeccable');
    assert.match(parsedSkill.data.description, /Frontend/i);
    assert.match(parsedSkill.data.description, /ask-impeccable/i);

    const yamlContent = fs.readFileSync(installedYamlPath, 'utf8');
    const parsedYaml = parseOpenAiYaml(yamlContent);
    assert.equal(parsedYaml.interface.display_name, 'Ask Impeccable');
    assert.match(parsedYaml.interface.short_description, /Frontend|UI/i);
    assert.match(parsedYaml.interface.default_prompt, /ask-impeccable/i);
    assert.equal(parsedYaml.policy.allow_implicit_invocation, true, 'Installed policy must have allow_implicit_invocation: true');
    assert.deepEqual(parsedYaml.policy.products, ['chatgpt', 'codex'], 'Installed policy.products must contain chatgpt and codex');

    // Verify no .upstream files are copied into the skill directory
    const installedFiles = listFilesRecursive(skillDir);
    assert.ok(!installedFiles.some(f => f.includes('.upstream')), 'Installed skill must not contain .upstream files');
  });

  test('Installs into isolated temporary environment for Claude Code with agents/openai.yaml, policy, and products bundled', () => {
    const agentTempDir = path.join(tempTestDir, 'claude-code-env');
    fs.mkdirSync(agentTempDir, { recursive: true });

    execSync(`npx skills add "${REPO_ROOT}" --agent claude-code --copy -y`, {
      cwd: agentTempDir,
      encoding: 'utf8',
      timeout: 30000,
    });

    const skillDir = path.join(agentTempDir, '.claude', 'skills', 'ask-impeccable');
    const installedSkillPath = path.join(skillDir, 'SKILL.md');
    const installedYamlPath = path.join(skillDir, 'agents', 'openai.yaml');

    assert.ok(fs.existsSync(installedSkillPath), `Expected installed SKILL.md at ${installedSkillPath}`);
    assert.ok(fs.existsSync(installedYamlPath), `Expected installed agents/openai.yaml at ${installedYamlPath}`);

    const skillContent = fs.readFileSync(installedSkillPath, 'utf8');
    const parsedSkill = parseFrontmatter(skillContent);
    assert.ok(parsedSkill, 'Installed SKILL.md must have valid YAML frontmatter');
    assert.equal(parsedSkill.data.name, 'ask-impeccable');
    assert.match(parsedSkill.data.description, /Frontend/i);

    const yamlContent = fs.readFileSync(installedYamlPath, 'utf8');
    const parsedYaml = parseOpenAiYaml(yamlContent);
    assert.equal(parsedYaml.interface.display_name, 'Ask Impeccable');
    assert.match(parsedYaml.interface.short_description, /Frontend|UI/i);
    assert.match(parsedYaml.interface.default_prompt, /ask-impeccable/i);
    assert.equal(parsedYaml.policy.allow_implicit_invocation, true, 'Installed policy must have allow_implicit_invocation: true');
    assert.deepEqual(parsedYaml.policy.products, ['chatgpt', 'codex'], 'Installed policy.products must contain chatgpt and codex');
  });

  test('Installs into isolated temporary environment for Codex with agents/openai.yaml, policy, and products bundled', () => {
    const agentTempDir = path.join(tempTestDir, 'codex-env');
    fs.mkdirSync(agentTempDir, { recursive: true });

    execSync(`npx skills add "${REPO_ROOT}" --agent codex --copy -y`, {
      cwd: agentTempDir,
      encoding: 'utf8',
      timeout: 30000,
    });

    const skillDir = path.join(agentTempDir, '.agents', 'skills', 'ask-impeccable');
    const installedSkillPath = path.join(skillDir, 'SKILL.md');
    const installedYamlPath = path.join(skillDir, 'agents', 'openai.yaml');

    assert.ok(fs.existsSync(installedSkillPath), `Expected installed SKILL.md at ${installedSkillPath}`);
    assert.ok(fs.existsSync(installedYamlPath), `Expected installed agents/openai.yaml at ${installedYamlPath}`);

    const skillContent = fs.readFileSync(installedSkillPath, 'utf8');
    const parsedSkill = parseFrontmatter(skillContent);
    assert.ok(parsedSkill, 'Installed SKILL.md must have valid YAML frontmatter');
    assert.equal(parsedSkill.data.name, 'ask-impeccable');
    assert.match(parsedSkill.data.description, /Frontend/i);

    const yamlContent = fs.readFileSync(installedYamlPath, 'utf8');
    const parsedYaml = parseOpenAiYaml(yamlContent);
    assert.equal(parsedYaml.interface.display_name, 'Ask Impeccable');
    assert.match(parsedYaml.interface.short_description, /Frontend|UI/i);
    assert.match(parsedYaml.interface.default_prompt, /ask-impeccable/i);
    assert.equal(parsedYaml.policy.allow_implicit_invocation, true, 'Installed policy must have allow_implicit_invocation: true');
    assert.deepEqual(parsedYaml.policy.products, ['chatgpt', 'codex'], 'Installed policy.products must contain chatgpt and codex');
  });

  test('Multi-agent installation bundles SKILL.md, agents/openai.yaml, and policy across antigravity, claude-code, and codex', () => {
    const multiAgentDir = path.join(tempTestDir, 'multi-agent-env');
    fs.mkdirSync(multiAgentDir, { recursive: true });

    execSync(`npx skills add "${REPO_ROOT}" --agent antigravity claude-code codex --copy -y`, {
      cwd: multiAgentDir,
      encoding: 'utf8',
      timeout: 30000,
    });

    const agentsSkillDir = path.join(multiAgentDir, '.agents', 'skills', 'ask-impeccable');
    const claudeSkillDir = path.join(multiAgentDir, '.claude', 'skills', 'ask-impeccable');

    assert.ok(fs.existsSync(path.join(agentsSkillDir, 'SKILL.md')), 'Must have SKILL.md in .agents/skills');
    assert.ok(fs.existsSync(path.join(agentsSkillDir, 'agents', 'openai.yaml')), 'Must have agents/openai.yaml in .agents/skills');
    assert.ok(fs.existsSync(path.join(claudeSkillDir, 'SKILL.md')), 'Must have SKILL.md in .claude/skills');
    assert.ok(fs.existsSync(path.join(claudeSkillDir, 'agents', 'openai.yaml')), 'Must have agents/openai.yaml in .claude/skills');

    const agentsYaml = parseOpenAiYaml(fs.readFileSync(path.join(agentsSkillDir, 'agents', 'openai.yaml'), 'utf8'));
    const claudeYaml = parseOpenAiYaml(fs.readFileSync(path.join(claudeSkillDir, 'agents', 'openai.yaml'), 'utf8'));

    assert.equal(agentsYaml.policy.allow_implicit_invocation, true);
    assert.deepEqual(agentsYaml.policy.products, ['chatgpt', 'codex']);
    assert.equal(claudeYaml.policy.allow_implicit_invocation, true);
    assert.deepEqual(claudeYaml.policy.products, ['chatgpt', 'codex']);
  });

  test('Installed artifact is coordinator-only, init-first, and batches commands when safe', () => {
    const installedSkillPath = path.join(tempTestDir, 'antigravity-env', '.agents', 'skills', 'ask-impeccable', 'SKILL.md');
    const content = fs.readFileSync(installedSkillPath, 'utf8');

    const parsed = parseFrontmatter(content);
    assert.match(parsed.data.description, /Coordinator/i, 'Metadata must describe coordinator behavior');
    assert.match(parsed.data.description, /batching a coherent serial command chain/i, 'Metadata must prefer safe command batching');

    assert.match(content, /first command.*`\/impeccable init`/is, 'Init must be first');
    assert.match(content, /Native commands only/i, 'Worker prompts must preserve native Impeccable commands');
    assert.match(content, /Batch when safe/i, 'Known command chains should stay in one worker session');
    assert.match(content, /Serial inside the batch/i, 'Commands inside a batch must execute serially');
    assert.match(content, /Split only at a real boundary/i, 'Fresh sessions must be reserved for real boundaries');
    assert.match(content, /Coordinator does not design/i, 'Coordinator must not perform UI work itself');
    assert.match(content, /\/impeccable init\r?\n\/impeccable audit dashboard/is, 'Must include an init-first same-prompt command batch example');
    assert.match(content, /Do not force one-command-per-session churn/i, 'Unnecessary fresh-session churn must be forbidden');

    assert.match(content, /npx impeccable install/i, 'Must use upstream installer guidance');
    assert.match(content, /re-check/i, 'Must re-check dependency availability after installation');
    assert.match(content, /Never fabricate Impeccable behavior/i, 'Must forbid fallback improvisation');
    assert.match(content, /\.ask-impeccable/i, 'Must forbid parallel ask-impeccable state');
    assert.doesNotMatch(content, /Read-Only UI Research Layer/i, 'Coordinator skill must not own a competing research layer');
  });
  test('Installed artifact exposes all 23 commands while keeping sequencing coordinator-owned', () => {
    const installedSkillPath = path.join(tempTestDir, 'antigravity-env', '.agents', 'skills', 'ask-impeccable', 'SKILL.md');
    const content = fs.readFileSync(installedSkillPath, 'utf8');
    const routes = ['craft', 'init', 'document', 'extract', 'shape', 'critique', 'audit', 'polish', 'bolder', 'quieter', 'distill', 'harden', 'onboard', 'animate', 'colorize', 'typeset', 'layout', 'delight', 'overdrive', 'clarify', 'adapt', 'optimize', 'live'];

    assert.equal(routes.length, 23);
    assert.equal(new Set(routes).size, 23, 'Routing contract must contain 23 unique commands');
    for (const route of routes) {
      assert.match(content, new RegExp('/impeccable ' + route + '\\b', 'i'), 'Missing explicit route for /impeccable ' + route);
    }

    assert.match(content, /deprecated upstream alias/i, 'craft must reflect upstream deprecation');
    assert.match(content, /Known chain.*batch it in one prompt\/session/is, 'Known chains should be batched');
    assert.match(content, /Finding-dependent chain/i, 'Finding-dependent chains must stop before unknown commands');
    assert.match(content, /User explicitly names several commands/i, 'Explicit multi-command requests should preserve order');
    assert.match(content, /batch them unless a real boundary requires a split/i, 'Safe batching should be the default');
    assert.match(content, /Command asks a question/i, 'Questions must be boundary-aware');
    assert.match(content, /same worker may continue the remaining batch/i, 'Answered questions may resume the same safe batch');
    assert.match(content, /\/impeccable audit blog/i, 'Must include upstream-style scoped command example');
    assert.match(content, /\/impeccable critique landing/i, 'Must include upstream README example semantics');




  });

  test('.upstream remains excluded and untracked', () => {
    const gitignorePath = path.join(REPO_ROOT, '.gitignore');
    const gitignoreContent = fs.readFileSync(gitignorePath, 'utf8');
    assert.match(gitignoreContent, /\.upstream\/?/, '.gitignore must exclude .upstream/');

    const gitStatus = execSync('git status --porcelain', {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    });
    assert.doesNotMatch(gitStatus, /\.upstream/, 'git status must not track .upstream files');
  });
});
