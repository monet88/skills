#!/usr/bin/env node
/**
 * UI Research CLI - BM25 search engine for UI/UX knowledge base
 * Read-only retrieval capability for Ask Impeccable (monet88/skills)
 */

import { CSV_CONFIG, AVAILABLE_STACKS, MAX_RESULTS, search, search_stack, detect_domain } from './core.mjs';

export function format_output(result) {
  if (result.error) {
    return `Error: ${result.error}`;
  }

  const output = [];
  if (result.stack) {
    output.push('## UI Pro Max Stack Guidelines');
    output.push(`**Stack:** ${result.stack} | **Query:** ${result.query}`);
  } else {
    output.push('## UI Pro Max Search Results');
    output.push(`**Domain:** ${result.domain} | **Query:** ${result.query}`);
  }
  output.push(`**Source:** ${result.file} | **Found:** ${result.count} results\n`);

  for (let i = 0; i < result.results.length; i++) {
    const row = result.results[i];
    output.push(`### Result ${i + 1}`);
    for (const [key, value] of Object.entries(row)) {
      let valueStr = String(value);
      if (valueStr.length > 300) {
        valueStr = valueStr.slice(0, 300) + '...';
      }
      output.push(`- **${key}:** ${valueStr}`);
    }
    output.push('');
  }

  return output.join('\n');
}

export function parseArgs(args) {
  let query = '';
  let domain = null;
  let stack = null;
  let maxResults = MAX_RESULTS;
  let json = false;
  let help = false;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--help' || arg === '-h') {
      help = true;
    } else if (arg === '--domain' || arg === '-d') {
      domain = args[++i];
    } else if (arg === '--stack' || arg === '-s') {
      stack = args[++i];
    } else if (arg === '--max-results' || arg === '-n') {
      maxResults = parseInt(args[++i], 10) || MAX_RESULTS;
    } else if (arg === '--json') {
      json = true;
    } else if (!arg.startsWith('-') && !query) {
      query = arg;
    }
  }

  return { query, domain, stack, maxResults, json, help };
}

export function main(argv = process.argv.slice(2)) {
  const { query, domain, stack, maxResults, json, help } = parseArgs(argv);

  if (help || !query) {
    const helpText = `UI Research Search CLI
Usage: node search.mjs "<query>" [--domain <domain>] [--stack <stack>] [--max-results 3] [--json]

Domains: ${Object.keys(CSV_CONFIG).join(', ')}
Stacks: ${AVAILABLE_STACKS.join(', ')}
`;
    process.stdout.write(helpText);
    return;
  }

  let result;
  if (stack) {
    result = search_stack(query, stack, maxResults);
  } else {
    result = search(query, domain, maxResults);
  }

  if (json) {
    process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  } else {
    process.stdout.write(format_output(result) + '\n');
  }
}

const isDirectRun = process.argv[1] && process.argv[1].endsWith('search.mjs');

if (isDirectRun) {
  main();
}
