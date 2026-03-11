const fs = require('fs');
const path = require('path');

function walkDir(dir) {
  let files = [];
  for (const f of fs.readdirSync(dir)) {
    const full = path.join(dir, f);
    if (fs.statSync(full).isDirectory()) files = files.concat(walkDir(full));
    else if (/\.(vue|js)$/.test(f)) files.push(full);
  }
  return files;
}

const srcDir = path.join(__dirname, 'src');
const files = walkDir(srcDir);

const replacements = [
  // Dark hex backgrounds -> warm equivalents
  [/#080C14/g,  '#0C0A09'],
  [/#0F1628/g,  '#1C1917'],
  [/#0D1220/g,  '#1C1917'],
  [/#0B1020/g,  '#1C1917'],
  [/#F8F9FB/g,  '#FAFAF9'],

  // Primary accent: indigo -> orange
  [/indigo-/g, 'orange-'],

  // Secondary accent: violet -> amber
  [/violet-/g, 'amber-'],

  // zinc -> stone
  [/zinc-/g, 'stone-'],

  // Warm neutral backgrounds
  [/slate-50/g,  'stone-50'],
  [/slate-100/g, 'stone-100'],
  [/slate-200/g, 'stone-200'],
  [/slate-900/g, 'stone-900'],
  [/slate-800/g, 'stone-800'],
  [/slate-700/g, 'stone-700'],
];

const SKIP = ['stores', 'services', 'router'];

let total = 0;
for (const file of files) {
  const rel = file.replace(srcDir, '');
  if (SKIP.some(s => rel.includes(s))) continue;

  let content = fs.readFileSync(file, 'utf8');
  const original = content;
  for (const [from, to] of replacements) {
    content = content.split(from.source ? undefined : from).join(to);
    if (from instanceof RegExp) content = fs.readFileSync(file, 'utf8');
  }

  // Re-do with regex properly
  content = fs.readFileSync(file, 'utf8');
  for (const [from, to] of replacements) {
    if (from instanceof RegExp) {
      content = content.replace(from, to);
    } else {
      content = content.split(from).join(to);
    }
  }

  if (content !== original) {
    fs.writeFileSync(file, content, 'utf8');
    total++;
    console.log('Updated: ' + path.basename(file));
  }
}
console.log('Done. Files updated: ' + total);
