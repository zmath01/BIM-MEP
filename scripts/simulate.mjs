import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { parseArgs } from 'node:util';
import { solveDucts, thermalResponse } from '../docs/engineering.mjs';

const { values } = parseArgs({ options: {
  route: { type: 'string', default: 'bypass' }, budget: { type: 'string', default: '85' },
  velocity: { type: 'string', default: '6' }, gain: { type: 'string', default: '1950' },
  step: { type: 'string', default: '30' }, out: { type: 'string', default: 'results' },
  model: { type: 'string' }, baseline: { type: 'boolean' }
} });
const input = values.model ?? new URL('../docs/data/office.json', import.meta.url);
const model = JSON.parse(await readFile(input, 'utf8'));
const ducts = solveDucts(model, { route: values.route, budget: Number(values.budget), limit: Number(values.velocity), optimize: !values.baseline });
const thermal = thermalResponse(model, { gain: Number(values.gain), stepMinutes: Number(values.step) });
const out = resolve(values.out);
await mkdir(out, { recursive: true });
const csv = ['segment,from,to,length_m,flow_m3_s,diameter_mm,velocity_m_s,reynolds,darcy_f,loss_pa', ...ducts.segments.map(s => [s.id, s.from, s.to, s.length, s.flow, s.diameter * 1000, s.velocity, s.reynolds, s.friction, s.pressure].join(','))].join('\n');
await Promise.all([
  writeFile(join(out, 'report.json'), JSON.stringify({ model: model.name, ducts, thermal }, null, 2) + '\n'),
  writeFile(join(out, 'duct-schedule.csv'), csv + '\n'),
  writeFile(join(out, 'thermal.csv'), ['hour,exact_degC,backward_euler_degC', ...thermal.series.map(x => [x.hour, x.exact, x.numerical].join(','))].join('\n') + '\n')
]);
console.log(`${ducts.route}: ${ducts.passes ? 'passes constraints' : 'fails constraints'} · ${ducts.pressure.toFixed(1)} Pa · ${ducts.clashes.length} clash(es)`);
console.log(`Outputs: ${out}`);
