"""Export a simulated layout as IFC4 for visual review in Bonsai or an IFC viewer."""
import argparse
import json
import math
from pathlib import Path

import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit


def ifc_coords(point):
    """Convert Three.js Y-up to IFC Z-up with a proper rotation."""
    x, y, z = point
    return x, -z, y


def round_duct(start, end, radius, sides=32):
    axis = next(i for i in range(3) if start[i] != end[i])
    u, v = (axis + 1) % 3, (axis + 2) % 3
    if start[axis] > end[axis]:
        start, end = end, start
    vertices = []
    for center in (start, end):
        for side in range(sides):
            angle = math.tau * side / sides
            point = list(center)
            point[u] += radius * math.cos(angle)
            point[v] += radius * math.sin(angle)
            vertices.append(ifc_coords(point))
    faces = [tuple(reversed(range(sides))), tuple(range(sides, 2 * sides))]
    for side in range(sides):
        other = (side + 1) % sides
        faces.append((side, other, sides + other, sides + side))
    return vertices, faces


def beam_mesh(bounds):
    lo, hi = bounds['min'], bounds['max']
    corners = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))
    vertices = [ifc_coords([hi[i] if bit else lo[i] for i, bit in enumerate(corner)]) for corner in corners]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return vertices, faces


def export(report, model_data, path):
    api = ifcopenshell.api
    model = api.project.create_file(version='IFC4')
    new = lambda kind, name: api.root.create_entity(model, ifc_class=kind, name=name)
    project = new('IfcProject', 'Office West supply coordination')
    site = new('IfcSite', 'Synthetic site')
    building = new('IfcBuilding', 'Office West')
    storey = new('IfcBuildingStorey', 'Level 01')
    metre = api.unit.add_si_unit(model, unit_type='LENGTHUNIT')
    api.unit.assign_unit(model, units=[metre, api.unit.add_si_unit(model, unit_type='AREAUNIT'), api.unit.add_si_unit(model, unit_type='VOLUMEUNIT')])
    for parent, child in ((project, site), (site, building), (building, storey)):
        api.aggregate.assign_object(model, products=[child], relating_object=parent)
    context = api.context.add_context(model, context_type='Model')
    body = api.context.add_context(model, context_type='Model', context_identifier='Body', target_view='MODEL_VIEW', parent=context)

    def add_product(kind, name, mesh):
        product = new(kind, name)
        vertices, faces = mesh
        shape = api.geometry.add_mesh_representation(model, context=body, vertices=[vertices], faces=[faces])
        api.geometry.assign_representation(model, product=product, representation=shape)
        api.spatial.assign_container(model, products=[product], relating_structure=storey)
        api.geometry.edit_object_placement(model, product=product)
        return product

    for segment in report['ducts']['segments']:
        radius = segment['diameter'] / 2
        product = add_product('IfcDuctSegment', segment['id'], round_duct(segment['a'], segment['b'], radius))
        product.PredefinedType = 'RIGIDSEGMENT'
        properties = api.pset.add_pset(model, product=product, name='CoordinationLab_DesignResults')
        api.pset.edit_pset(model, pset=properties, properties={
            'Diameter_mm': 1000.0 * segment['diameter'], 'Length_m': float(segment['length']),
            'Airflow_m3_per_s': float(segment['flow']), 'PressureLoss_Pa': float(segment['pressure']),
            'Insulation_mm': 1000.0 * model_data['duct']['insulation']
        })
    for obstacle in model_data['obstacles']:
        add_product('IfcBeam', obstacle['id'], beam_mesh(obstacle))
    path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(path))
    print(f'Wrote {len(report["ducts"]["segments"])} duct segments to {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=Path('results/report.json'))
    parser.add_argument('--model', type=Path, default=Path('docs/data/office.json'))
    parser.add_argument('--out', type=Path, default=Path('results/office-west.ifc'))
    args = parser.parse_args()
    export(json.loads(args.report.read_text(encoding='utf-8')), json.loads(args.model.read_text(encoding='utf-8')), args.out)
