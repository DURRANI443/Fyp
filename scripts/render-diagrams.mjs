import { existsSync } from 'node:fs';
import { mkdir, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer';
import { run } from '@mermaid-js/mermaid-cli';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const [version = 'v0.1.0', explicitOutput] = process.argv.slice(2);
if (!/^v\d+\.\d+\.\d+$/.test(version)) {
  throw new Error('Use a documentation version such as v0.1.0.');
}
const baseline = path.join(root, 'doc', version);
const sourceDir = path.join(baseline, 'diagrams');
const outputDir = explicitOutput ? path.resolve(root, explicitOutput) : sourceDir;
const relativeOutput = path.relative(root, outputDir);
if (relativeOutput.startsWith('..') || path.isAbsolute(relativeOutput)) {
  throw new Error('Diagram output must stay inside this repository.');
}
if (existsSync(path.join(baseline, 'manifest.json'))) {
  const relativeBaseline = path.relative(baseline, outputDir);
  if (!relativeBaseline.startsWith('..') && !path.isAbsolute(relativeBaseline)) {
    throw new Error('Captured baselines are immutable. Supply an output path such as .local/diagram-check/v0.1.0.');
  }
}

const executablePath = process.env.PUPPETEER_EXECUTABLE_PATH || puppeteer.executablePath();
if (!existsSync(executablePath)) {
  throw new Error('Set PUPPETEER_EXECUTABLE_PATH to an installed Chromium executable before rendering.');
}
const sources = (await readdir(sourceDir)).filter((name) => name.endsWith('.mmd')).sort();
if (sources.length === 0) throw new Error('No Mermaid sources were found.');
await mkdir(outputDir, { recursive: true });
const browser = await puppeteer.launch({ executablePath, headless: true });
try {
  for (const name of sources) {
    const output = path.join(outputDir, name.replace(/\.mmd$/, '.svg'));
    await run(path.join(sourceDir, name), output, {
      browser,
      quiet: true,
      outputFormat: 'svg',
      parseMMDOptions: {
        backgroundColor: 'white',
        viewport: { width: 1800, height: 1200 },
        mermaidConfig: {
          theme: 'neutral',
          securityLevel: 'strict',
          fontFamily: 'Arial, sans-serif',
          deterministicIds: true,
          deterministicIDSeed: name,
          flowchart: { htmlLabels: false, useMaxWidth: false },
          sequence: { useMaxWidth: false },
          er: { useMaxWidth: false },
        },
      },
    });
    console.log(`Rendered ${path.relative(root, output)}`);
  }
} finally {
  await browser.close();
}
console.log(`PASS: ${sources.length} Mermaid diagrams rendered to SVG.`);
