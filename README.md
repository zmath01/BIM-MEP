# MEP Coordination Lab

An interactive office HVAC coordination case. Compare a straight trunk with a beam bypass, find stock duct sizes under a pressure budget, and inspect analytic and numerical predictions for room temperature. The browser and the local CLI run the same engineering model.

**[GitHub Pages demo](https://zmath01.github.io/BIM-MEP/)** · **[Engineering methods and verification](engineering/METHODS.md)** · **[Sample IFC4 model](docs/data/office-west.ifc)**

## Run locally

Requires Node.js 22+ and a recent browser. Use Python 3 for the local server and the optional IFC exporter.

```sh
npm ci
npm test
npm run simulate
npm run build
python -m http.server 8000 --directory dist
```

Open <http://localhost:8000>. After npm installs Three.js, the built viewer runs locally without external runtime services. Javascript computes the results in the browser.

### Reproduce the design comparison

```sh
npm run simulate -- --route direct --out results/direct
npm run simulate -- --baseline --out results/baseline
npm run simulate -- --route bypass --budget 85 --velocity 6 --gain 1950 --step 30
```

Each run writes `report.json`, `duct-schedule.csv`, and `thermal.csv`. The direct route flags a clash with `BEAM-01`. The velocity-sized bypass needs about **94.7 Pa**. The optimised bypass gives **82.9 Pa**, **650 L/s**, **18.23 m²** of straight duct sheet area, and about **87 W** at the assumed fan efficiency. It meets the model's **85 Pa** pressure limit with no clash candidates. Vary the gain and step size to see the error relative to the analytic thermal solution.

### Open the layout in an IFC tool

The sample IFC4 contains seven `IfcDuctSegment` entities, one `IfcBeam`, and calculated duct properties in an IFC spatial hierarchy. It records the result geometry for one layout. Flow topology is in `office.json`; IFC ports and fittings are outside this exchange example.

```sh
python -m venv .venv
# macOS / Linux
. .venv/bin/activate
# Windows PowerShell equivalent
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements-ifc.txt
python scripts/export_ifc.py
python -m ifcopenshell.validate results/office-west.ifc --rules
```

To export a report downloaded from the viewer, run `python scripts/export_ifc.py --report path/to/office-west-report.json`. Open the IFC in Bonsai or another IFC4 viewer. The case uses invented inputs and simplified geometry. Use it for learning, portfolio review and concept testing.

## Publish to GitHub Pages

In **Settings → Pages**, select **GitHub Actions** as the source. Run the **Portfolio Pages** workflow. It tests the solver, builds a static bundle and deploys `dist/` without a backend. The same bundle is served by the local command above.
