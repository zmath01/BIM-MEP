import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { frictionFactor, solveDucts, thermalResponse } from '../docs/engineering.mjs';

const model = JSON.parse(readFileSync(new URL('../docs/data/office.json', import.meta.url), 'utf8'));
const close = (actual, expected, tolerance = 1e-8) => assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected}`);

test('junctions conserve airflow and the report includes the fixed pressure once', () => {
  const result = solveDucts(model);
  close(result.airflow, 0.65);
  const segment = new Map(result.segments.map(s => [s.id, s]));
  close(segment.get('B03').flow, segment.get('S02').flow + segment.get('S03').flow);
  close(segment.get('S02').flow, segment.get('S04').flow + segment.get('S05').flow);
  for (const terminal of result.terminals) close(terminal.pressure, 50 + terminal.path.reduce((sum, id) => sum + segment.get(id).pressure, 0));
  close(result.power, result.airflow * result.pressure / 0.62);
});

test('default feasible optimum corrects a pressure-budget failure; stricter budget can be impossible', () => {
  const baseline = solveDucts(model, { optimize: false });
  const optimum = solveDucts(model);
  assert.equal(baseline.passes, false);
  close(baseline.pressure, 94.73818, 0.01);
  assert.equal(optimum.optimumFound, true);
  close(optimum.pressure, 82.94549, 0.01);
  close(optimum.area, 18.23380376);
  assert.equal(optimum.feasible, 63);
  assert.equal(solveDucts(model, { budget: 60 }).optimumFound, false);
});

test('direct route hard-clashes; a moved obstacle can cause a clearance-only clash', () => {
  assert.deepEqual(solveDucts(model, { route: 'direct' }).clashes, [{ segment: 'S01', obstacle: 'BEAM-01', type: 'hard' }]);
  const modified = structuredClone(model);
  modified.obstacles[0].min[2] = 0.28;
  modified.obstacles[0].max[2] = 0.55;
  assert.equal(solveDucts(modified, { route: 'direct', optimize: false }).clashes[0].type, 'clearance');
});

test('invalid routes and malformed graphs fail explicitly', () => {
  assert.throws(() => solveDucts(model, { route: 'missing' }), /Unknown route/);
  const invalid = structuredClone(model);
  invalid.downstream[1].to = 'J2';
  assert.throws(() => solveDucts(invalid), /unique, orthogonal/);
  assert.throws(() => thermalResponse(model, { stepMinutes: 0 }), /time step/);
});

test('friction factor has the expected laminar limit and positive turbulent value', () => {
  close(frictionFactor(1000, 0.0004), 0.064);
  assert.ok(frictionFactor(100000, 0.0004) > 0.017 && frictionFactor(100000, 0.0004) < 0.022);
});

test('backward Euler converges to the analytic solution and handles a final partial step', () => {
  const coarse = thermalResponse(model, { stepMinutes: 60 });
  const fine = thermalResponse(model, { stepMinutes: 7 });
  close(fine.series.at(-1).hour, 8);
  close(fine.equilibrium, 27.72819134760593);
  assert.ok(fine.maxError < coarse.maxError / 4);
  assert.ok(fine.series.at(-1).numerical < fine.equilibrium);
});
