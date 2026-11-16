const length = (a, b) => Math.hypot(...a.map((value, axis) => value - b[axis]));
const overlaps = (a, b) => a.min.every((value, axis) => value < b.max[axis] && a.max[axis] > b.min[axis]);

function trunk(model, route) {
  if (!Object.hasOwn(model.routes, route)) throw new RangeError(`Unknown route: ${route}`);
  const edges = [...model.routes[route].segments, ...model.downstream];
  const children = new Map();
  const inbound = new Set();
  const ids = new Set();
  for (const edge of edges) {
    const { id, from, to, k } = edge;
    const a = model.nodes[from];
    const b = model.nodes[to];
    if (!a || !b || ids.has(id) || inbound.has(to) || to === model.root || !Number.isFinite(k) || k < 0 || a.filter((x, i) => x !== b[i]).length !== 1) {
      throw new Error(`Expected unique, orthogonal supply-tree segment: ${id}`);
    }
    ids.add(id);
    inbound.add(to);
    if (!children.has(from)) children.set(from, []);
    children.get(from).push({ ...edge, a, b, length: length(a, b) });
  }
  const paths = [];
  const visited = new Set();
  const makePaths = (id, path) => {
    if (visited.has(id)) throw new Error('Cycle in supply tree');
    visited.add(id);
    const branches = children.get(id) ?? [];
    const terminal = model.terminals[id];
    if (terminal && (branches.length || !Number.isFinite(terminal.flow) || terminal.flow <= 0)) throw new Error(`Invalid terminal: ${id}`);
    if (terminal) paths.push({ id, ...terminal, path });
    if (!branches.length && !terminal) throw new Error(`Unserved leaf: ${id}`);
    let flow = terminal?.flow ?? 0;
    for (const edge of branches) {
      edge.flow = makePaths(edge.to, [...path, edge.id]);
      flow += edge.flow;
    }
    return flow;
  };
  const flow = makePaths(model.root, []);
  if (visited.size !== edges.length + 1 || paths.length !== Object.keys(model.terminals).length) throw new Error('Disconnected supply tree');
  return { flow, paths, edges: [...children.values()].flat() };
}

export function frictionFactor(reynolds, relativeRoughness) {
  if (reynolds <= 0) throw new RangeError('Reynolds number must be positive');
  const laminar = 64 / reynolds;
  if (reynolds <= 2300) return laminar;
  const turbulent = 0.25 / Math.log10(relativeRoughness / 3.7 + 5.74 / reynolds ** 0.9) ** 2;
  if (reynolds >= 4000) return turbulent;
  const weight = (reynolds - 2300) / 1700;
  return laminar * (1 - weight) + turbulent * weight;
}

function evaluate(edge, diameter, model) {
  const { density, viscosity, roughness, insulation, clearance } = model.duct;
  const velocity = edge.flow / (Math.PI * diameter ** 2 / 4);
  const reynolds = density * velocity * diameter / viscosity;
  const friction = frictionFactor(reynolds, roughness / diameter);
  const pressure = (friction * edge.length / diameter + edge.k) * density * velocity ** 2 / 2;
  const axial = edge.a.findIndex((value, axis) => value !== edge.b[axis]);
  const envelope = (padding) => {
    const radius = diameter / 2 + insulation + padding;
    return {
      min: edge.a.map((value, axis) => Math.min(value, edge.b[axis]) - (axis === axial ? padding : radius)),
      max: edge.a.map((value, axis) => Math.max(value, edge.b[axis]) + (axis === axial ? padding : radius))
    };
  };
  const bounds = envelope(0);
  const clearanceBounds = envelope(clearance);
  const clashes = [];
  for (const obstacle of model.obstacles) {
    if (overlaps(bounds, obstacle)) clashes.push({ obstacle: obstacle.id, type: 'hard' });
    else if (overlaps(clearanceBounds, obstacle)) clashes.push({ obstacle: obstacle.id, type: 'clearance' });
  }
  return { ...edge, diameter, velocity, reynolds, friction, pressure, bounds, clashes, area: Math.PI * diameter * edge.length };
}

export function solveDucts(model, { route = 'bypass', budget = 85, limit = 6, optimize = true } = {}) {
  if (!Number.isFinite(budget) || budget <= 0 || !Number.isFinite(limit) || limit <= 0) throw new RangeError('Positive pressure and velocity limits required');
  const tree = trunk(model, route);
  const diameters = [...model.duct.stockDiameters].sort((a, b) => a - b);
  if (!diameters.length || diameters.some(d => !Number.isFinite(d) || d <= 0)) throw new RangeError('Invalid stock diameters');
  const choices = tree.edges.map(edge => diameters.map(d => evaluate(edge, d, model)));
  const edgeIndex = new Map(tree.edges.map(({ id }, index) => [id, index]));
  const paths = tree.paths.map(p => ({ ...p, index: p.path.map(id => edgeIndex.get(id)) }));
  const fixed = model.duct.fixedPressure;
  const assess = (segments) => {
    const terminals = paths.map(({ index, ...p }) => ({ ...p, pressure: fixed + index.reduce((sum, i) => sum + segments[i].pressure, 0) }));
    const critical = terminals.reduce((a, b) => a.pressure >= b.pressure ? a : b);
    const clashes = segments.flatMap(s => s.clashes.map(c => ({ segment: s.id, ...c })));
    const passes = critical.pressure <= budget && clashes.length === 0 && segments.every(s => s.velocity <= limit);
    return { terminals, critical, clashes, passes };
  };
  const baseline = choices.map(options => options.find(s => s.velocity <= limit) ?? options.at(-1));
  let winner;
  let objective = Infinity;
  let evaluated = 0;
  let feasible = 0;
  const selected = [];
  const search = (index, area) => {
    if (index === choices.length) {
      evaluated++;
      if (!assess(selected).passes) return;
      feasible++;
      if (area < objective - 1e-10) {
        winner = [...selected];
        objective = area;
      }
      return;
    }
    for (const option of choices[index]) {
      selected[index] = option;
      search(index + 1, area + option.area);
    }
  };
  if (optimize && choices.every(options => options.some(s => !s.clashes.length && s.velocity <= limit))) search(0, 0);
  const segments = winner ?? baseline;
  const result = assess(segments);
  return {
    route, budget, limit, optimize, evaluated, feasible, optimumFound: Boolean(winner),
    candidateCount: diameters.length ** tree.edges.length, segments,
    airflow: tree.flow, ...result,
    pressure: result.critical.pressure, power: tree.flow * result.critical.pressure / model.duct.fanEfficiency,
    area: segments.reduce((sum, segment) => sum + segment.area, 0)
  };
}

export function thermalResponse(model, { gain = model.thermal.gain, stepMinutes = 30 } = {}) {
  const { capacity, ua, ventilation, supplyTemperature, outdoorTemperature, initialTemperature, heatCapacityAir, durationHours } = model.thermal;
  if (!Number.isFinite(gain) || gain < 0 || !Number.isFinite(stepMinutes) || stepMinutes < 1) throw new RangeError('Invalid thermal load or time step');
  const ventilationConductance = model.duct.density * ventilation * heatCapacityAir;
  const conductance = ua + ventilationConductance;
  const equilibrium = (ua * outdoorTemperature + ventilationConductance * supplyTemperature + gain) / conductance;
  const timeConstant = capacity / conductance;
  let numerical = initialTemperature;
  let second = 0;
  let maxError = 0;
  const series = [{ hour: 0, exact: initialTemperature, numerical }];
  while (second < durationHours * 3600) {
    const step = Math.min(stepMinutes * 60, durationHours * 3600 - second);
    second += step;
    numerical = equilibrium + (numerical - equilibrium) / (1 + step / timeConstant);
    const exact = equilibrium + (initialTemperature - equilibrium) * Math.exp(-second / timeConstant);
    maxError = Math.max(maxError, Math.abs(exact - numerical));
    series.push({ hour: second / 3600, exact, numerical });
  }
  return { gain, stepMinutes, equilibrium, timeConstantHours: timeConstant / 3600, maxError, series };
}
