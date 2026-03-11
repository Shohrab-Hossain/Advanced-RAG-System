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
  [/orange-/g, 'emerald-'],
  [/amber-/g,  'teal-'],
];

const SKIP = ['stores', 'services', 'router'];

let total = 0;
for (const file of files) {
  const rel = file.replace(srcDir, '');
  if (SKIP.some(s => rel.includes(s))) continue;

  let content = fs.readFileSync(file, 'utf8');
  const original = content;
  for (const [from, to] of replacements) {
    content = content.replace(from, to);
    // replace is not global by default with regex — re-read and do all
  }
  // redo properly
  content = original;
  for (const [from, to] of replacements) {
    content = content.replace(new RegExp(from.source, 'g'), to);
  }

  if (content !== original) {
    fs.writeFileSync(file, content, 'utf8');
    total++;
    console.log('Updated: ' + path.basename(file));
  }
}
console.log('Done. Files updated: ' + total);
