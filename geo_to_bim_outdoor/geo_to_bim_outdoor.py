# title: geo_to_bim for scan to BIM
# created date: 2022.5.10, taewook kang, laputa99999@gmail.com
# 
import os, sys, re, json, numpy, uuid, argparse
import numpy as np, pandas as pd, ifcopenshell
import ifcopenshell.api

run = ifcopenshell.api.run

def assign_product(usecase, ifc, product, **kwargs):
    # ifcopenshell 0.8 takes a list of products, 0.7 a single product
    try:
        return run(usecase, ifc, products=[product], **kwargs)
    except TypeError:
        return run(usecase, ifc, product=product, **kwargs)

def create_swept_solid(ifc, subcontext, storey, polygon, pset, bx = 0.0, by = 0.0, ground = 0.0):
    ifc_points = []
    for p in polygon:
        p[0] = p[0] - bx
        p[1] = p[1] - by
        ifc_point = ifc.createIfcCartesianPoint(p)
        ifc_points.append(ifc_point)

    # profile = ifc.createIfcArbitraryClosedProfileDef("AREA", None, ifc.createIfcPolyline([ifc.createIfcCartesianPoint((1.0, 0.1)), ifc.createIfcCartesianPoint((4.0, 0.2)), ifc.createIfcCartesianPoint((4.0, 3.1)), ifc.createIfcCartesianPoint((1.0, 0.1))]))
    profile = ifc.createIfcArbitraryClosedProfileDef("AREA", None, ifc.createIfcPolyline(ifc_points))
    
    # extrude
    axis = ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None)  # default coordinate system    
    direction = ifc.createIfcDirection([0.0, 0.0, 1.0]) # Z positive up direction
    solid = ifc.createIfcExtrudedAreaSolid(profile, axis, direction, pset['elevation'])   # extrude the profile with elevation
    shape = ifc.createIfcShapeRepresentation(subcontext, "Body", "SweptSolid", [solid])  # solid needs to be put in a shape

    # create an mass using building element proxy
    element = run("root.create_entity", ifc, ifc_class="IfcBuildingElementProxy", name="building from 3D scan")
    run("geometry.assign_representation", ifc, product=element, representation=shape)   # assign the shape created earlier as the element representation
    matrix = numpy.eye(4)
    matrix[2][3] = ground   # extrude from the ground elevation, not from z=0
    run("geometry.edit_object_placement", ifc, product=element, matrix=matrix)

    return element

def set_object_property(ifc, owner_history, element, pset):
    create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid1().hex)

    # values measured from the scan. Pset_ names are reserved for buildingSMART property sets
    property_values = [
        ifc.createIfcPropertySingleValue("BuildingID", None, ifc.create_entity("IfcInteger", pset['building_ID']), None),
        ifc.createIfcPropertySingleValue("Height", None, ifc.create_entity("IfcLengthMeasure", pset['elevation']), None),
        ifc.createIfcPropertySingleValue("GroundElevation", None, ifc.create_entity("IfcLengthMeasure", pset['ground']), None),
        ifc.createIfcPropertySingleValue("FootprintArea", None, ifc.create_entity("IfcAreaMeasure", pset['area']), None),
        ifc.createIfcPropertySingleValue("Perimeter", None, ifc.create_entity("IfcLengthMeasure", pset['length']), None)
    ]
    property_set = ifc.createIfcPropertySet(create_guid(), owner_history, "ScanToBIM", None, property_values)
    ifc.createIfcRelDefinesByProperties(create_guid(), owner_history, None, None, [element], property_set)

    # Add quantity information
    quantity_values = [
        ifc.createIfcQuantityLength("Length", "Perimeter of the footprint", None, pset['length']),
        ifc.createIfcQuantityArea("Area", "Area of the element", None, pset['area']),
        ifc.createIfcQuantityVolume("Volume", "Volume of the element", None, pset['area'] * pset['elevation'])
    ]
    element_quantity = ifc.createIfcElementQuantity(create_guid(), owner_history, "BaseQuantities", None, None, quantity_values)
    ifc.createIfcRelDefinesByProperties(create_guid(), owner_history, None, None, [element], element_quantity)
        
def get_epsg(projection_file):
    # the WKT written by dtm_to_geo. the last authority entry names the CRS itself
    if not os.path.isfile(projection_file):
        return None
    with open(projection_file, 'r') as f:
        wkt = f.read()
    codes = re.findall(r'(?:AUTHORITY|ID)\["EPSG",\s*"?(\d+)"?\]', wkt)
    return codes[-1] if codes else None

def add_georeferencing(ifc, epsg, bx, by):
    name = 'EPSG:' + str(epsg)
    try:
        run("georeference.add_georeferencing", ifc, name=name)
    except TypeError:   # ifcopenshell 0.7 takes no name
        run("georeference.add_georeferencing", ifc)
    run("georeference.edit_georeferencing", ifc,
        projected_crs={"Name": name},
        coordinate_operation={"Eastings": bx, "Northings": by, "OrthogonalHeight": 0.0})

def get_base_point(df):
    # lower left corner of all footprints, rounded down to whole meters
    xs, ys = [], []
    for footprint in df['footprint']:
        for x, y in json.loads(footprint.replace('(', '[').replace(')', ']')):
            xs.append(x)
            ys.append(y)
    if len(xs) == 0:
        return 0.0, 0.0
    return float(np.floor(min(xs))), float(np.floor(min(ys)))

def geo_to_bim(in_fname, out_fname, bx, by, epsg = None, project_name = "Scan to BIM project", site_name = "My Site"):
    try:
        df = pd.read_csv(in_fname)
        if bx is None or by is None:
            bx, by = get_base_point(df)
        print(f'base point = ({bx}, {by}), crs = EPSG:{epsg}')

        ifc = run("project.create_file")

        # set up ownerhistory
        #myperson = run("owner.add_person", ifc)
        # myorganisation = run("owner.add_organisation", ifc)
        ownerhistory = run(
            "owner.create_owner_history",
            ifc,
            # person=myperson,
            # organisation=myorganisation,
        ) 

        # create a "project > site > building > storey" hierarchy
        project = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcProject",
            name=project_name,
        )

        run("unit.assign_unit", ifc, length={"is_metric": True, "raw": "METERS"})

        # a body subcontext under a model context. georeferencing attaches to the model context
        model_context = run("context.add_context", ifc, context_type="Model")
        subcontext = run(
            "context.add_context",
            ifc,
            context_type="Model",
            context_identifier="Body",
            target_view="MODEL_VIEW",
            parent=model_context,
        )

        if epsg is not None:
            add_georeferencing(ifc, epsg, bx, by)

        site = run("root.create_entity", ifc, ifc_class="IfcSite", name=site_name)
        assign_product("aggregate.assign_object", ifc, product=site, relating_object=project)

        for index, row in df.iterrows():
            polygon = row['footprint']
            polygon = polygon.replace('(', '[')
            polygon = polygon.replace(')', ']')
            polygon = json.loads(polygon)
            
            building = run("root.create_entity", ifc, ifc_class="IfcBuilding", name="My Building")
            assign_product("aggregate.assign_object", ifc, product=building, relating_object=site)

            storey = run("root.create_entity", ifc, ifc_class="IfcBuildingStorey", name="My Storey")
            assign_product("aggregate.assign_object", ifc, product=storey, relating_object=building)

            ground = float(row['ground']) if 'ground' in row else 0.0   # older dimension files have no ground column
            pset = {'building_ID': int(row['ID']), 'area': float(row['area']), 'length': float(row['length']), 'elevation': float(row['elevation']), 'ground': ground}
            
            solid = create_swept_solid(ifc, subcontext, storey, polygon, pset, bx, by, ground)
            assign_product("spatial.assign_container", ifc, product=solid, relating_structure=storey)

            set_object_property(ifc, ownerhistory, solid, pset)
            
            storey = None
            building = None

        ifc.write(out_fname)
    except Exception as e:
        print(e)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--link_pset', default="link_propertyset.json", type=str, required=False)    # not read. kept so older SBDL files still parse
    parser.add_argument('--base_point', default="", type=str, required=False)   # [x, y] subtracted from map coordinates. empty: lower left of the footprints
    parser.add_argument('--crs', default="", type=str, required=False)   # EPSG code. empty: read from the dtm_to_geo projection file
    parser.add_argument('--project_name', default="Scan to BIM project", type=str, required=False)
    parser.add_argument('--site_name', default="My Site", type=str, required=False)
    args = parser.parse_args()

    bx = by = None
    if len(args.base_point.strip()):
        args.base_point = json.loads(args.base_point)
        bx = args.base_point[0]
        by = args.base_point[1]
    epsg = args.crs.replace('EPSG:', '') if len(args.crs.strip()) else get_epsg(args.input + "_projection.txt")
    input_fname = args.input + "_dimension.csv"     
    output_fname = args.output + ".ifc"
    geo_to_bim(input_fname, output_fname, bx, by, epsg, args.project_name, args.site_name)

    # output_fname = args.output + "_sample_building.ifc"
    # ifc_building.create_sample_building(output_fname)    # TBD. test. not working

if __name__ == '__main__':
    main()

