import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const output = new URL('dist/', root);
await rm(output, { recursive: true, force: true });
await cp(new URL('docs/', root), output, { recursive: true });
await mkdir(new URL('vendor/controls/', output), { recursive: true });
const vendor = {
  'build/three.module.js': 'three.module.js',
  'build/three.core.js': 'three.core.js',
  'examples/jsm/controls/OrbitControls.js': 'controls/OrbitControls.js',
  LICENSE: 'THREE-LICENSE.txt'
};
for (const [source, destination] of Object.entries(vendor)) {
  await cp(new URL(`node_modules/three/${source}`, root), new URL(`vendor/${destination}`, output));
}
const page = new URL('index.html', output);
const html = await readFile(page, 'utf8');
await writeFile(page, html.replace('https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js', './vendor/three.module.js').replace('https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/', './vendor/'));
