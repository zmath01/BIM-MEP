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

const fontSource = new URL('node_modules/@fontsource-variable/instrument-sans/', root);
const font = 'instrument-sans-latin-wght-normal.woff2';
await cp(new URL(`files/${font}`, fontSource), new URL(`vendor/${font}`, output));
await cp(new URL('LICENSE', fontSource), new URL('vendor/INSTRUMENT-SANS-LICENSE.txt', output));
const stylesheet = new URL('style.css', output);
const css = await readFile(stylesheet, 'utf8');
await writeFile(stylesheet, css.replace(`https://cdn.jsdelivr.net/npm/@fontsource-variable/instrument-sans@5.3.0/files/${font}`, `./vendor/${font}`));
