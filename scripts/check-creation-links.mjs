import { readFile, readdir } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../src/', import.meta.url));
const expectedPrefix = 'https://www.creationwatches.com/products/ja/search?keyword=';
const errors = [];

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const pathname = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await collectFiles(pathname));
    else if (entry.name.endsWith('.astro')) files.push(pathname);
  }

  return files;
}

for (const file of await collectFiles(root)) {
  const source = await readFile(file, 'utf8');
  const label = relative(root, file);

  if (/href=\{(?:product|watch)\.url/.test(source)) {
    errors.push(`${label}: uses a raw product URL`);
  }

  for (const match of source.matchAll(/href="(https:\/\/www\.creationwatches\.com\/products\/[^"]+)"/g)) {
    if (!match[1].startsWith(expectedPrefix)) {
      errors.push(`${label}: wrong locale URL ${match[1]}`);
    } else if (!match[1].slice(expectedPrefix.length).trim()) {
      errors.push(`${label}: missing SKU`);
    }
  }
}

if (errors.length) {
  console.error(`CreationWatches link validation failed:\n${errors.join('\n')}`);
  process.exit(1);
}

console.log('CreationWatches links: JP locale valid');
