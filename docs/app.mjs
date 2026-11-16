import { solveDucts, thermalResponse } from './engineering.mjs';

const $ = id => document.getElementById(id);
const button = (value, click) => {
  const element = document.createElement('button');
  element.type = 'button';
  element.textContent = value;
  element.addEventListener('click', click);
  return element;
};
function plot(canvas, thermal) {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  const scale = Math.min(devicePixelRatio, 2);
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext('2d');
  ctx.scale(scale, scale);
  const series = thermal.series;
  const zone = { x: 40, y: 15, width: width - 58, height: height - 45 };
  const values = series.flatMap(point => [point.exact, point.numerical]);
  const min = Math.floor(Math.min(...values) - 0.35);
  const max = Math.ceil(Math.max(...values) + 0.35);
  const duration = series.at(-1).hour;
  const mapX = x => zone.x + x / duration * zone.width;
  const mapY = y => zone.y + (max - y) / (max - min) * zone.height;
  ctx.font = '11px Instrument Sans, system-ui';
  ctx.fillStyle = '#52645a';
  for (let i = 0; i <= 4; i++) {
    const temperature = min + (max - min) * i / 4;
    const y = mapY(temperature);
    ctx.strokeStyle = '#dbe2d8';
    ctx.beginPath();ctx.moveTo(zone.x, y);ctx.lineTo(zone.x + zone.width, y);ctx.stroke();
    ctx.fillText(`${temperature.toFixed(1)}°`, 0, y + 4);
    const hour = i * duration / 4;
    ctx.fillText(`${Number(hour.toFixed(2))}h`, mapX(hour) - 5, height - 7);
  }
  const exact = Array.from({ length: 81 }, (_, index) => {
    const hour = duration * index / 80;
    return { hour, exact: thermal.equilibrium + (series[0].exact - thermal.equilibrium) * Math.exp(-hour / thermal.timeConstantHours) };
  });
  for (const [points, key, color, dash] of [[exact, 'exact', '#277a64', []], [series, 'numerical', '#a75f19', [6, 4]]]) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.6;
    ctx.setLineDash(dash);
    ctx.beginPath();
    for (const point of points) ctx.lineTo(mapX(point.hour), mapY(point[key]));
    ctx.stroke();
  }
}

try {
  const response = await fetch('./data/office.json');
  if (!response.ok) throw new Error('The model data could not be loaded.');
  const model = await response.json();
  let report;
  let thermal;
  let selected;
  let viewer;
  const redrawSchedule = (focus) => {
    const table = $('schedule');
    table.replaceChildren();
    for (const segment of report.segments) {
      const row = table.insertRow();
      const active = segment.id === selected;
      row.classList.toggle('selected', active);
      const select = button(segment.id, () => {
        selected = active ? undefined : segment.id;
        viewer?.update(report, selected);
        redrawSchedule(segment.id);
      });
      select.setAttribute('aria-pressed', String(active));
      row.insertCell().append(select);
      for (const value of [segment.diameter * 1000, Math.round(segment.flow * 1000), segment.velocity.toFixed(2), segment.pressure.toFixed(1)]) row.insertCell().textContent = value;
      if (focus === segment.id) select.focus({ preventScroll: true });
    }
  };
  const calculate = () => {
    report = solveDucts(model, {
      route: document.querySelector('input[name=route]:checked').value,
      budget: Number($('budget').value), limit: Number($('velocity').value), optimize: $('optimize').checked
    });
    if (!report.segments.some(s => s.id === selected)) selected = undefined;
    $('budget-value').value = `${report.budget} Pa`;
    $('velocity-value').value = `${report.limit.toFixed(1)} m/s`;
    $('airflow').textContent = `${Math.round(report.airflow * 1000)} L/s`;
    $('pressure').textContent = `${report.pressure.toFixed(1)} Pa`;
    $('critical').textContent = `Critical: ${report.critical.name}`;
    $('power').textContent = `${Math.round(report.power)} W`;
    $('area').textContent = `${report.area.toFixed(2)} m²`;
    const status = $('status');
    status.classList.toggle('fail', !report.passes);
    const reasons = [];
    if (report.clashes.length) reasons.push(...report.clashes.map(c => `${c.segment} ${c.type} clash with ${c.obstacle}`));
    if (report.pressure > report.budget) reasons.push('pressure over budget');
    if (report.segments.some(segment => segment.velocity > report.limit)) reasons.push('velocity over limit');
    status.textContent = report.passes ? (report.optimumFound ? `Optimum found · ${report.feasible.toLocaleString()} feasible combinations` : 'Velocity-sized baseline passes') : `${report.optimize ? 'No feasible design' : 'Baseline fails'}. ${reasons.join(' · ')}.`;
    $('schedule-note').textContent = report.optimize && !report.optimumFound ? 'Showing the velocity-sized baseline for diagnosis.' : 'Select a segment to highlight it in the model.';
    viewer?.update(report, selected);
    redrawSchedule();
  };
  const updateThermal = () => {
    thermal = thermalResponse(model, { gain: Number($('gain').value), stepMinutes: Number($('step').value) });
    $('gain-value').value = `${thermal.gain.toLocaleString()} W`;
    $('thermal-summary').textContent = `Equilibrium ${thermal.equilibrium.toFixed(2)} °C · time constant ${thermal.timeConstantHours.toFixed(2)} h · maximum sample error ${thermal.maxError.toFixed(3)} °C`;
    plot($('chart'), thermal);
  };
  new ResizeObserver(() => { if (thermal) plot($('chart'), thermal); }).observe($('chart'));
  document.fonts.ready.then(() => { if (thermal) plot($('chart'), thermal); });
  for (const input of document.querySelectorAll('.control input')) input.addEventListener('input', calculate);
  $('gain').addEventListener('input', updateThermal);
  $('step').addEventListener('input', updateThermal);
  $('download').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify({ model: model.name, ducts: report, thermal }, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a');
    anchor.download = 'office-west-report.json';
    anchor.href = url;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  calculate();
  updateThermal();
  try {
    const { createViewer } = await import('./viewer.mjs');
    await document.fonts.ready;
    viewer = createViewer($('scene'), model);
    viewer.update(report, selected);
    $('reset').addEventListener('click', () => viewer.reset());
  } catch {
    const fallback = document.createElement('p');
    fallback.className = 'fallback';
    fallback.textContent = '3D view unavailable. You can still change the route, inspect the schedule and download results.';
    $('scene').append(fallback);
    $('reset').disabled = true;
  }
} catch (error) {
  $('error').hidden = false;
  $('error').classList.add('fail');
  $('error').textContent = error.message;
}
