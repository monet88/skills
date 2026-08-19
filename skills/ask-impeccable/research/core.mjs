/**
 * MIT License
 * Copyright (c) 2024 Next Level Builder
 * Ported to Node.js for Ask Impeccable (monet88/skills)
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const DEFAULT_DATA_DIR = path.resolve(__dirname, 'data');
export const MAX_RESULTS = 3;

export const CSV_CONFIG = {
  style: {
    file: 'styles.csv',
    search_cols: ['Style Category', 'Keywords', 'Best For', 'Type', 'AI Prompt Keywords'],
    output_cols: ['Style Category', 'Type', 'Keywords', 'Primary Colors', 'Effects & Animation', 'Best For', 'Light Mode ✓', 'Dark Mode ✓', 'Performance', 'Accessibility', 'Framework Compatibility', 'Complexity', 'AI Prompt Keywords', 'CSS/Technical Keywords', 'Implementation Checklist', 'Design System Variables']
  },
  color: {
    file: 'colors.csv',
    search_cols: ['Product Type', 'Notes'],
    output_cols: ['Product Type', 'Primary', 'On Primary', 'Secondary', 'On Secondary', 'Accent', 'On Accent', 'Background', 'Foreground', 'Card', 'Card Foreground', 'Muted', 'Muted Foreground', 'Border', 'Destructive', 'On Destructive', 'Ring', 'Notes']
  },
  chart: {
    file: 'charts.csv',
    search_cols: ['Data Type', 'Keywords', 'Best Chart Type', 'When to Use', 'When NOT to Use', 'Accessibility Notes'],
    output_cols: ['Data Type', 'Keywords', 'Best Chart Type', 'Secondary Options', 'When to Use', 'When NOT to Use', 'Data Volume Threshold', 'Color Guidance', 'Accessibility Grade', 'Accessibility Notes', 'A11y Fallback', 'Library Recommendation', 'Interactive Level']
  },
  landing: {
    file: 'landing.csv',
    search_cols: ['Pattern Name', 'Keywords', 'Conversion Optimization', 'Section Order'],
    output_cols: ['Pattern Name', 'Keywords', 'Section Order', 'Primary CTA Placement', 'Color Strategy', 'Conversion Optimization']
  },
  product: {
    file: 'products.csv',
    search_cols: ['Product Type', 'Keywords', 'Primary Style Recommendation', 'Key Considerations'],
    output_cols: ['Product Type', 'Keywords', 'Primary Style Recommendation', 'Secondary Styles', 'Landing Page Pattern', 'Dashboard Style (if applicable)', 'Color Palette Focus']
  },
  ux: {
    file: 'ux-guidelines.csv',
    search_cols: ['Category', 'Issue', 'Description', 'Platform'],
    output_cols: ['Category', 'Issue', 'Platform', 'Description', 'Do', 'Don\'t', 'Code Example Good', 'Code Example Bad', 'Severity']
  },
  typography: {
    file: 'typography.csv',
    search_cols: ['Font Pairing Name', 'Category', 'Mood/Style Keywords', 'Best For', 'Heading Font', 'Body Font'],
    output_cols: ['Font Pairing Name', 'Category', 'Heading Font', 'Body Font', 'Mood/Style Keywords', 'Best For', 'Google Fonts URL', 'CSS Import', 'Tailwind Config', 'Notes']
  },
  icons: {
    file: 'icons.csv',
    search_cols: ['Category', 'Icon Name', 'Keywords', 'Best For'],
    output_cols: ['Category', 'Icon Name', 'Keywords', 'Library', 'Import Code', 'Usage', 'Best For', 'Style']
  },
  react: {
    file: 'react-performance.csv',
    search_cols: ['Category', 'Issue', 'Keywords', 'Description'],
    output_cols: ['Category', 'Issue', 'Platform', 'Description', 'Do', 'Don\'t', 'Code Example Good', 'Code Example Bad', 'Severity']
  },
  web: {
    file: 'app-interface.csv',
    search_cols: ['Category', 'Issue', 'Keywords', 'Description'],
    output_cols: ['Category', 'Issue', 'Platform', 'Description', 'Do', 'Don\'t', 'Code Example Good', 'Code Example Bad', 'Severity']
  },
  'google-fonts': {
    file: 'google-fonts.csv',
    search_cols: ['Family', 'Category', 'Stroke', 'Classifications', 'Keywords', 'Subsets', 'Designers'],
    output_cols: ['Family', 'Category', 'Stroke', 'Classifications', 'Styles', 'Variable Axes', 'Subsets', 'Designers', 'Popularity Rank', 'Google Fonts URL']
  }
};

export const STACK_CONFIG = {
  react:            { file: 'stacks/react.csv' },
  nextjs:           { file: 'stacks/nextjs.csv' },
  vue:              { file: 'stacks/vue.csv' },
  svelte:           { file: 'stacks/svelte.csv' },
  astro:            { file: 'stacks/astro.csv' },
  swiftui:          { file: 'stacks/swiftui.csv' },
  'react-native':   { file: 'stacks/react-native.csv' },
  flutter:          { file: 'stacks/flutter.csv' },
  nuxtjs:           { file: 'stacks/nuxtjs.csv' },
  'nuxt-ui':        { file: 'stacks/nuxt-ui.csv' },
  'html-tailwind':  { file: 'stacks/html-tailwind.csv' },
  shadcn:           { file: 'stacks/shadcn.csv' },
  'jetpack-compose':{ file: 'stacks/jetpack-compose.csv' },
  threejs:          { file: 'stacks/threejs.csv' },
  angular:          { file: 'stacks/angular.csv' },
  laravel:          { file: 'stacks/laravel.csv' },
  javafx:           { file: 'stacks/javafx.csv' },
  wpf:              { file: 'stacks/wpf.csv' },
  winui:            { file: 'stacks/winui.csv' },
  avalonia:         { file: 'stacks/avalonia.csv' },
  uno:              { file: 'stacks/uno.csv' },
  uwp:              { file: 'stacks/uwp.csv' }
};

export const STACK_COLS = {
  search_cols: ['Category', 'Guideline', 'Description', 'Do', 'Don\'t'],
  output_cols: ['Category', 'Guideline', 'Description', 'Do', 'Don\'t', 'Code Good', 'Code Bad', 'Severity', 'Docs URL']
};

export const AVAILABLE_STACKS = Object.keys(STACK_CONFIG);

export const DOMAIN_KEYWORDS = {
  color: ['color', 'palette', 'hex', '#', 'rgb', 'token', 'semantic', 'accent', 'destructive', 'muted', 'foreground'],
  chart: ['chart', 'graph', 'visualization', 'trend', 'bar', 'pie', 'scatter', 'heatmap', 'funnel'],
  landing: ['landing', 'page', 'cta', 'conversion', 'hero', 'testimonial', 'pricing', 'section'],
  product: ['saas', 'ecommerce', 'e-commerce', 'fintech', 'healthcare', 'gaming', 'portfolio', 'crypto', 'dashboard', 'fitness', 'restaurant', 'hotel', 'travel', 'music', 'education', 'learning', 'legal', 'insurance', 'medical', 'beauty', 'pharmacy', 'dental', 'pet', 'dating', 'wedding', 'recipe', 'delivery', 'ride', 'booking', 'calendar', 'timer', 'tracker', 'diary', 'note', 'chat', 'messenger', 'crm', 'invoice', 'parking', 'transit', 'vpn', 'alarm', 'weather', 'sleep', 'meditation', 'fasting', 'habit', 'grocery', 'meme', 'wardrobe', 'plant care', 'reading', 'flashcard', 'puzzle', 'trivia', 'arcade', 'photography', 'streaming', 'podcast', 'newsletter', 'marketplace', 'freelancer', 'coworking', 'airline', 'museum', 'theater', 'church', 'non-profit', 'charity', 'kindergarten', 'daycare', 'senior care', 'veterinary', 'florist', 'bakery', 'brewery', 'construction', 'automotive', 'real estate', 'logistics', 'agriculture', 'coding bootcamp'],
  style: ['style', 'design', 'ui', 'minimalism', 'glassmorphism', 'neumorphism', 'brutalism', 'dark mode', 'flat', 'aurora', 'prompt', 'css', 'implementation', 'variable', 'checklist', 'tailwind'],
  ux: ['ux', 'usability', 'accessibility', 'wcag', 'touch', 'scroll', 'animation', 'keyboard', 'navigation', 'mobile'],
  typography: ['font pairing', 'typography pairing', 'heading font', 'body font'],
  'google-fonts': ['google font', 'font family', 'font weight', 'font style', 'variable font', 'noto', 'font for', 'find font', 'font subset', 'font language', 'monospace font', 'serif font', 'sans serif font', 'display font', 'handwriting font', 'font', 'typography', 'serif', 'sans'],
  icons: ['icon', 'icons', 'lucide', 'heroicons', 'symbol', 'glyph', 'pictogram', 'svg icon'],
  react: ['react', 'next.js', 'nextjs', 'suspense', 'memo', 'usecallback', 'useeffect', 'rerender', 'bundle', 'waterfall', 'barrel', 'dynamic import', 'rsc', 'server component'],
  web: ['aria', 'focus', 'outline', 'semantic', 'virtualize', 'autocomplete', 'form', 'input type', 'preconnect']
};

export class BM25 {
  constructor(k1 = 1.5, b = 0.75) {
    this.k1 = k1;
    this.b = b;
    this.corpus = [];
    this.doc_lengths = [];
    this.avgdl = 0;
    this.idf = new Map();
    this.doc_freqs = new Map();
    this.N = 0;
  }

  tokenize(text) {
    const textStr = String(text ?? '').toLowerCase().replace(/[^\p{L}\p{N}_\s]/gu, ' ');
    return textStr.trim().split(/\s+/).filter(w => w.length >= 2);
  }

  fit(documents) {
    this.corpus = documents.map(doc => this.tokenize(doc));
    this.N = this.corpus.length;
    if (this.N === 0) {
      return;
    }
    this.doc_lengths = this.corpus.map(doc => doc.length);
    this.avgdl = this.doc_lengths.reduce((sum, len) => sum + len, 0) / this.N;

    this.doc_freqs = new Map();
    for (const doc of this.corpus) {
      const seen = new Set();
      for (const word of doc) {
        if (!seen.has(word)) {
          this.doc_freqs.set(word, (this.doc_freqs.get(word) || 0) + 1);
          seen.add(word);
        }
      }
    }

    this.idf = new Map();
    for (const [word, freq] of this.doc_freqs.entries()) {
      this.idf.set(word, Math.log((this.N - freq + 0.5) / (freq + 0.5) + 1));
    }
  }

  score(query) {
    const query_tokens = this.tokenize(query);
    const scores = [];

    for (let idx = 0; idx < this.corpus.length; idx++) {
      let score = 0;
      const doc = this.corpus[idx];
      const doc_len = this.doc_lengths[idx];
      const term_freqs = new Map();
      for (const word of doc) {
        term_freqs.set(word, (term_freqs.get(word) || 0) + 1);
      }

      for (const token of query_tokens) {
        if (this.idf.has(token)) {
          const tf = term_freqs.get(token) || 0;
          const token_idf = this.idf.get(token);
          const numerator = tf * (this.k1 + 1);
          const denominator = tf + this.k1 * (1 - this.b + (this.b * doc_len) / this.avgdl);
          score += (token_idf * numerator) / denominator;
        }
      }

      scores.push({ idx, score });
    }

    return scores.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.idx - b.idx;
    });
  }
}

export function parseCSV(content) {
  const rows = [];
  let currentRow = [];
  let currentCell = '';
  let inQuotes = false;
  let i = 0;
  if (content.charCodeAt(0) === 0xFEFF) {
    i = 1;
  }
  const len = content.length;

  while (i < len) {
    const char = content[i];

    if (inQuotes) {
      if (char === '"') {
        if (i + 1 < len && content[i + 1] === '"') {
          currentCell += '"';
          i += 2;
        } else {
          inQuotes = false;
          i++;
        }
      } else {
        currentCell += char;
        i++;
      }
    } else {
      // Quotes only open a quoted cell when at the start of the field (matching Python csv.DictReader)
      if (char === '"' && currentCell.length === 0) {
        inQuotes = true;
        i++;
      } else if (char === ',') {
        currentRow.push(currentCell);
        currentCell = '';
        i++;
      } else if (char === '\r') {
        if (i + 1 < len && content[i + 1] === '\n') {
          i++;
        }
        currentRow.push(currentCell);
        currentCell = '';
        rows.push(currentRow);
        currentRow = [];
        i++;
      } else if (char === '\n') {
        currentRow.push(currentCell);
        currentCell = '';
        rows.push(currentRow);
        currentRow = [];
        i++;
      } else {
        currentCell += char;
        i++;
      }
    }
  }

  if (currentCell !== '' || currentRow.length > 0) {
    currentRow.push(currentCell);
    rows.push(currentRow);
  }

  while (rows.length > 0 && rows[rows.length - 1].length === 1 && rows[rows.length - 1][0] === '') {
    rows.pop();
  }

  if (rows.length === 0) return [];

  const headers = rows[0];
  const results = [];
  for (let r = 1; r < rows.length; r++) {
    const row = rows[r];
    if (row.length === 1 && row[0] === '') continue;
    const obj = {};
    for (let c = 0; c < headers.length; c++) {
      obj[headers[c]] = row[c] !== undefined ? row[c] : null;
    }
    results.push(obj);
  }

  return results;
}

export function loadCSV(filepath) {
  const content = fs.readFileSync(filepath, 'utf8');
  return parseCSV(content);
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function detect_domain(query) {
  const queryLower = String(query ?? '').toLowerCase();
  const domains = Object.keys(DOMAIN_KEYWORDS);
  let bestDomain = 'style';
  let maxScore = 0;

  for (const domain of domains) {
    const keywords = DOMAIN_KEYWORDS[domain];
    let score = 0;
    for (const kw of keywords) {
      const regex = new RegExp(`\\b${escapeRegExp(kw)}\\b`);
      if (regex.test(queryLower)) {
        score++;
      }
    }
    if (score > maxScore) {
      maxScore = score;
      bestDomain = domain;
    }
  }

  return maxScore > 0 ? bestDomain : 'style';
}

function _search_csv(filepath, search_cols, output_cols, query, max_results) {
  if (!fs.existsSync(filepath)) {
    return [];
  }

  const data = loadCSV(filepath);
  const documents = data.map(row =>
    search_cols.map(col => (row[col] !== undefined && row[col] !== null ? String(row[col]) : '')).join(' ')
  );

  const bm25 = new BM25();
  bm25.fit(documents);
  const ranked = bm25.score(query);

  const results = [];
  for (const { idx, score } of ranked.slice(0, max_results)) {
    if (score > 0) {
      const row = data[idx];
      const outRow = {};
      for (const col of output_cols) {
        if (col in row) {
          outRow[col] = row[col];
        }
      }
      results.push(outRow);
    }
  }

  return results;
}

export function search(query, domain = null, max_results = MAX_RESULTS, dataDir = DEFAULT_DATA_DIR) {
  if (domain === null || domain === undefined) {
    domain = detect_domain(query);
  }

  const config = CSV_CONFIG[domain] || CSV_CONFIG['style'];
  const filepath = path.join(dataDir, config.file);

  if (!fs.existsSync(filepath)) {
    return { error: `File not found: ${filepath}`, domain };
  }

  const results = _search_csv(filepath, config.search_cols, config.output_cols, query, max_results);

  return {
    domain,
    query,
    file: config.file,
    count: results.length,
    results
  };
}

export function search_stack(query, stack, max_results = MAX_RESULTS, dataDir = DEFAULT_DATA_DIR) {
  if (!STACK_CONFIG[stack]) {
    return { error: `Unknown stack: ${stack}. Available: ${AVAILABLE_STACKS.join(', ')}` };
  }

  const filepath = path.join(dataDir, STACK_CONFIG[stack].file);

  if (!fs.existsSync(filepath)) {
    return { error: `Stack file not found: ${filepath}`, stack };
  }

  const results = _search_csv(filepath, STACK_COLS.search_cols, STACK_COLS.output_cols, query, max_results);

  return {
    domain: 'stack',
    stack,
    query,
    file: STACK_CONFIG[stack].file,
    count: results.length,
    results
  };
}
