# name: geo to bim pipe
# programmer: taewook kang (laputa99999@gmail.com)
# date: 2026.11.
# desc: maps the pipes and elbows of cylinder_to_pipe to IFC elements with a rule file. pipes are
#       extruded circles (IfcPipeSegment), elbows disks swept along an arc (IfcPipeFitting BEND)

import os, sys, json, glob, argparse, operator
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OPERATORS = {'==': operator.eq, '!=': operator.ne, '<': operator.lt, '<=': operator.le,
             '>': operator.gt, '>=': operator.ge, 'in': lambda a, b: a in b}

def resolve(path):
    if not path or os.path.isabs(path) or os.path.exists(path):
        return path
    return os.path.join(ROOT, path)

def orientation(axis):
    z = abs(axis[2])
    return 'vertical' if z > 0.9 else 'horizontal' if z < 0.1 else 'inclined'

def pipe_params(p):
    axis = np.subtract(p['end'], p['start'])
    axis /= np.linalg.norm(axis)
    return {'kind': 'pipe', 'radius': p['radius'], 'diameter': 2 * p['radius'], 'length': p['length'],
            'nominal': p['nominal'] or '', 'orientation': orientation(axis), 'angle': 0.0,
            'points': p['points'], 'coverage': p['coverage']}

def elbow_params(e):
    return {'kind': 'elbow', 'radius': e['radius'], 'diameter': 2 * e['radius'],
            'length': np.radians(e['angle']) * e['bend_radius'], 'nominal': e['nominal'] or '',
            'orientation': '', 'angle': e['angle'], 'points': 0, 'coverage': 0.0}

def match(rules, params):
    for rule in rules:
        tests = [OPERATORS[op](params.get(key), value) for key, op, value in rule.get('condition', [])]
        if (any if rule.get('logic', 'and') == 'or' else all)(tests):
            return rule
    return None

def assign_product(run, usecase, ifc, product, **kwargs):
    # ifcopenshell 0.8 takes a list of products, 0.7 a single product
    try:
        return run(usecase, ifc, products=[product], **kwargs)
    except TypeError:
        return run(usecase, ifc, product=product, **kwargs)

def placement(ifc, origin, z, x):
    return ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint([float(c) for c in origin]),
                                         ifc.createIfcDirection([float(c) for c in z]),
                                         ifc.createIfcDirection([float(c) for c in x]))

def perpendicular(axis):
    ref = np.eye(3)[np.argmin(np.abs(axis))]
    x = np.cross(axis, ref)
    return x / np.linalg.norm(x)

def pipe_solid(ifc, p):
    start, end = np.array(p['start']), np.array(p['end'])
    axis = (end - start) / np.linalg.norm(end - start)
    profile = ifc.createIfcCircleProfileDef('AREA', None, None, float(p['radius']))
    return ifc.createIfcExtrudedAreaSolid(profile, placement(ifc, start, axis, perpendicular(axis)),
                                          ifc.createIfcDirection([0.0, 0.0, 1.0]), float(p['length']))

def elbow_solid(ifc, e):
    # a disk swept along an arc of the bend circle. the circle starts at the elbow start and runs
    # toward the start direction, so it is trimmed from 0 to the bend angle
    start, center = np.array(e['start']), np.array(e['center'])
    x = (start - center) / np.linalg.norm(start - center)
    z = np.cross(x, np.array(e['start_direction']))
    circle = ifc.createIfcCircle(placement(ifc, center, z / np.linalg.norm(z), x), float(e['bend_radius']))
    arc = ifc.createIfcTrimmedCurve(circle, [ifc.createIfcParameterValue(0.0)],
                                    [ifc.createIfcParameterValue(float(np.radians(e['angle'])))], True, 'PARAMETER')
    return ifc.createIfcSweptDiskSolid(arc, float(e['radius']), None, None, None)

def save_ifc(fname, items, rules, args):
    import ifcopenshell, ifcopenshell.api
    run = ifcopenshell.api.run

    ifc = run("project.create_file")
    project = run("root.create_entity", ifc, ifc_class="IfcProject", name=args.project_name)
    units = [run("unit.add_si_unit", ifc, unit_type=t) for t in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT", "PLANEANGLEUNIT")]
    run("unit.assign_unit", ifc, units=units)
    model = run("context.add_context", ifc, context_type="Model")
    body = run("context.add_context", ifc, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model)

    site = run("root.create_entity", ifc, ifc_class="IfcSite", name=args.site_name)
    building = run("root.create_entity", ifc, ifc_class="IfcBuilding", name=args.building_name)
    storey = run("root.create_entity", ifc, ifc_class="IfcBuildingStorey", name=args.storey_name)
    assign_product(run, "aggregate.assign_object", ifc, product=site, relating_object=project)
    assign_product(run, "aggregate.assign_object", ifc, product=building, relating_object=site)
    assign_product(run, "aggregate.assign_object", ifc, product=storey, relating_object=building)

    counts = {}
    for item, params, solid in items:
        rule = match(rules, params)
        if rule is None:
            continue
        name = rule.get('name', rule['type']).format(**params).strip()
        element = run("root.create_entity", ifc, ifc_class=rule['type'], name=name,
                      predefined_type=rule.get('predefined_type'))
        shape = solid(ifc, item)
        kind = 'AdvancedSweptSolid' if shape.is_a('IfcSweptDiskSolid') else 'SweptSolid'
        representation = ifc.createIfcShapeRepresentation(body, 'Body', kind, [shape])
        run("geometry.assign_representation", ifc, product=element, representation=representation)
        run("geometry.edit_object_placement", ifc, product=element, matrix=np.eye(4))   # solids are in world coordinates
        assign_product(run, "spatial.assign_container", ifc, product=element, relating_structure=storey)
        pset = run("pset.add_pset", ifc, product=element, name="ScanToBIM")
        values = {k: (float(v) if isinstance(v, (float, np.floating)) else v) for k, v in params.items() if v != ''}
        values.update(rule.get('properties', {}))
        run("pset.edit_pset", ifc, pset=pset, properties=values)
        counts[rule['type']] = counts.get(rule['type'], 0) + 1

    ifc.write(fname)
    print(f'{sum(counts.values())} elements saved to {fname}: {counts}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--mapping_rule', type=str, default='geo_to_bim_pipe/pipe_mapping_rule.json')
    parser.add_argument('--project_name', type=str, default='Scan to BIM project')
    parser.add_argument('--site_name', type=str, default='My Site')
    parser.add_argument('--building_name', type=str, default='My Building')
    parser.add_argument('--storey_name', type=str, default='My Storey')
    args = parser.parse_args()

    files = glob.glob(args.input + "*_pipe.json")
    print("input files = ", files)
    if not files:
        print("no pipe file")
        sys.exit(1)
    with open(resolve(args.mapping_rule)) as f:
        rules = json.load(f)['rules']

    items = []
    for fname in files:
        with open(fname) as f:
            network = json.load(f)
        items += [(p, pipe_params(p), pipe_solid) for p in network['pipes']]
        items += [(e, elbow_params(e), elbow_solid) for e in network['elbows']]
    save_ifc(args.output + '.ifc', items, rules, args)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(1)
