# title: geo_to_bim for scan to BIM
# created date: 2022.5.10, taewook kang, laputa99999@gmail.com
# 
import os, sys, json, glob, numpy, uuid, re, argparse, readline, trimesh, time, tempfile
import numpy as np, sympy as sp, pandas as pd, matplotlib.pyplot as plt, ifcopenshell
from telnetlib import theNULL
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from ast import literal_eval
from ifcopenshell.api import run
from math import sin, cos
# import ifc_building

run = ifcopenshell.api.run

def create_basic_wall(self):
    length = self.convert_si_to_unit(self.settings["length"])
    thickness = self.convert_si_to_unit(self.settings["thickness"])
    thickness *= 1 / cos(self.settings["x_angle"])
    points = (
        (0.0, 0.0),
        (0.0, thickness),
        (length, thickness),
        (length, 0.0),
        (0.0, 0.0),
    )
    if self.file.schema == "IFC2X3":
        curve = self.file.createIfcPolyline([self.file.createIfcCartesianPoint(p) for p in points])
    else:
        curve = self.file.createIfcIndexedPolyCurve(self.file.createIfcCartesianPointList2D(points), None, False)
    if self.settings["x_angle"]:
        extrusion_direction = self.file.createIfcDirection(
            (0.0, sin(self.settings["x_angle"]), cos(self.settings["x_angle"]))
        )
    else:
        extrusion_direction = self.file.createIfcDirection((0.0, 0.0, 1.0))
    extrusion = self.file.createIfcExtrudedAreaSolid(
        self.file.createIfcArbitraryClosedProfileDef("AREA", None, curve),
        self.file.createIfcAxis2Placement3D(
            self.file.createIfcCartesianPoint((0.0, self.convert_si_to_unit(self.settings["offset"]), 0.0)),
            self.file.createIfcDirection((0.0, 0.0, 1.0)),
            self.file.createIfcDirection((1.0, 0.0, 0.0)),
        ),
        extrusion_direction,
        self.convert_si_to_unit(self.settings["height"]) * (1 / cos(self.settings["x_angle"])),
    )
    if self.settings["booleans"]:
        extrusion = self.apply_booleans(extrusion)
    if self.settings["clippings"]:
        extrusion = self.apply_clippings(extrusion)
    return extrusion

def create_building(ifc, subcontext, storey, polygon, pset, bx = 0.0, by = 0.0):
    model = ifcopenshell.file() # TBD. https://blenderbim.org/docs-python/ifcopenshell-python/code_examples.html
    project = run("root.create_entity", model, ifc_class="IfcProject", name="My Project")
    run("unit.assign_unit", model)  # Assigning without arguments defaults to metric units
    context = run("context.add_context", model, context_type="Model")   # Let's create a modeling geometry context, so we can store 3D geometry (note: IFC supports 2D too!)
    body = run("context.add_context", model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=context)

    # Create a site, building, and storey. Many hierarchies are possible.
    site = run("root.create_entity", model, ifc_class="IfcSite", name="My Site")
    building = run("root.create_entity", model, ifc_class="IfcBuilding", name="Building A")
    storey = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Ground Floor")

    # the site is our top level location, assign it to the project. 
    run("aggregate.assign_object", model, relating_object=project, product=site)
    run("aggregate.assign_object", model, relating_object=site, product=building)
    run("aggregate.assign_object", model, relating_object=building, product=storey)

    # Create wall
    wall = run("root.create_entity", model, ifc_class="IfcWall")
    representation = run("geometry.add_wall_representation", model, context=body, length=5, height=3, thickness=0.2)    # Add a new wall-like body geometry, 5 meters long, 3 meters high, and 200mm thick
    run("geometry.assign_representation", model, product=wall, representation=representation)   # Assign our new body geometry back to our wall

    run("spatial.assign_container", model, relating_structure=storey, product=wall) # Place our wall in the ground floor

    model.write("model.ifc")
    pass

def create_swept_solid(ifc, subcontext, storey, polygon, pset, bx = 0.0, by = 0.0):
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

    # placement
    local_axis = ifc.createIfcAxis2Placement3D(ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None)
    localplacement = ifc.createIfcLocalPlacement(axis, local_axis)

    # create an mass using building element proxy
    element = run("root.create_entity", ifc, ifc_class="IfcBuildingElementProxy", name="building from 3D scan")
    run("geometry.assign_representation", ifc, product=element, representation=shape)   # assign the shape created earlier as the element representation
    run("geometry.edit_object_placement", ifc, product=element, matrix=numpy.eye(4))    # place the ifcslab, but an identity matrix doesn't do anything

    return element

def set_object_property(ifc, owner_history, element, pset):
    create_guid = lambda: ifcopenshell.guid.compress(uuid.uuid1().hex)

    # Define and associate the wall material
    material = ifc.createIfcMaterial("wall material")
    material_layer = ifc.createIfcMaterialLayer(material, 0.2, None)
    material_layer_set = ifc.createIfcMaterialLayerSet([material_layer], None)
    material_layer_set_usage = ifc.createIfcMaterialLayerSetUsage(material_layer_set, "AXIS2", "POSITIVE", -0.1)
    ifc.createIfcRelAssociatesMaterial(create_guid(), owner_history, RelatedObjects=[element], RelatingMaterial=material_layer_set_usage)

    # Create and assign property set
    property_values = [
        ifc.createIfcPropertySingleValue("Reference", "Reference", ifc.create_entity("IfcText", "Describe the Reference"), None),
        ifc.createIfcPropertySingleValue("IsExternal", "IsExternal", ifc.create_entity("IfcBoolean", True), None),
        ifc.createIfcPropertySingleValue("ThermalTransmittance", "ThermalTransmittance", ifc.create_entity("IfcReal", 2.569), None),
        ifc.createIfcPropertySingleValue("IntValue", "IntValue", ifc.create_entity("IfcInteger", 2), None)
    ]
    property_set = ifc.createIfcPropertySet(create_guid(), owner_history, "Pset_WallCommon", None, property_values)
    ifc.createIfcRelDefinesByProperties(create_guid(), owner_history, None, None, [element], property_set)

    # Add quantity information
    quantity_values = [
        ifc.createIfcQuantityLength("Length", "Length of the eleement", None, pset['length']),
        ifc.createIfcQuantityArea("Area", "Area of the element", None, pset['area']),
        ifc.createIfcQuantityVolume("Volume", "Volume of the element", None, pset['area'] * pset['elevation'])
    ]
    element_quantity = ifc.createIfcElementQuantity(create_guid(), owner_history, "BaseQuantities", None, None, quantity_values)
    ifc.createIfcRelDefinesByProperties(create_guid(), owner_history, None, None, [element], element_quantity)
        
def geo_to_bim(in_fname, out_fname, bx, by):
    try:
        df = pd.read_csv(in_fname)

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
            name="Scan to BIM project",
        )

        run("unit.assign_unit", ifc, length={"is_metric": True, "raw": "METERS"})

        # mycontext = run("context.add_context", ifc)
        subcontext = run(
            "context.add_context",
            ifc,
            # context="Model",
            # subcontext="Body",
            target_view="MODEL_VIEW",
        )

        site = run("root.create_entity", ifc, ifc_class="IfcSite", name="My Site")
        run("aggregate.assign_object", ifc, product=site, relating_object=project)

        for index, row in df.iterrows():
            polygon = row['footprint']
            polygon = polygon.replace('(', '[')
            polygon = polygon.replace(')', ']')
            polygon = json.loads(polygon)
            elevation = float(row['elevation'])
            
            building = run("root.create_entity", ifc, ifc_class="IfcBuilding", name="My Building")
            run("aggregate.assign_object", ifc, product=building, relating_object=site)

            storey = run("root.create_entity", ifc, ifc_class="IfcBuildingStorey", name="My Storey")
            run("aggregate.assign_object", ifc, product=storey, relating_object=building)

            pset = {'building_ID': int(row['ID']), 'area': float(row['area']), 'length': float(row['length']), 'elevation': float(row['elevation'])}
            
            solid = create_swept_solid(ifc, subcontext, storey, polygon, pset, bx, by)
            run("spatial.assign_container", ifc, product=solid, relating_structure=storey)

            set_object_property(ifc, ownerhistory, solid, pset)
            
            storey = None
            building = None

        ifc.write(out_fname)
    except Exception as e:
        print(e)

def intersect_mesh(args):
    mesh = trimesh.Trimesh(vertices=[[0, 0, 0], [0, 0, 10], [0, 10, 0]],
                        faces=[[0, 1, 2]])

    plane_normal = [0, 0, 1]
    plane_origin = [0, 0, 6]
    isect, face_inds = trimesh.intersections.mesh_plane(mesh, plane_normal, plane_origin, return_faces=True)
    ints = np.array(*isect)
    print(ints)
    print(ints[:, 1])

    ax = plt.axes(projection='3d')
    ax.plot(ints[:, 0], ints[:, 1], ints[:, 2], 'r') # https://note.nkmk.me/python-slice-usage/, https://thispointer.com/python-numpy-select-rows-columns-by-index-from-a-2d-ndarray-multi-dimension/
    ax.plot_trisurf(mesh.vertices[:, 0], mesh.vertices[:,1], triangles=mesh.faces, Z=mesh.vertices[:,2], alpha=0.5)
    # ax.add_collection(Poly3DCollection([plane1], alpha=0.5, edgecolors='r'))
    plt.show()

    # https://compas.dev/examples/example-mesh-subdivision-schemes/doc.html
    # https://towardsdatascience.com/5-step-guide-to-generate-3d-meshes-from-point-clouds-with-python-36bad397d8ba
    # https://trimsh.org/examples/quick_start.html
    # https://githubhot.com/repo/mikedh/trimesh/issues/1492

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default="/home/ktw/projects/pcd_pl/output/punktsky/dtm_to_geo/dtm_to_geo", type=str, required=False)
    parser.add_argument('--output', default="/home/ktw/projects/pcd_pl/output/punktsky/geo_to_bim_outdoor/geo_to_bim_outdoor", type=str, required=False)
    parser.add_argument('--link_pset', default="link_propertyset.json", type=str, required=False)
    parser.add_argument('--base_point', default="[724840.0, 6181000.0]", type=str, required=False)   
    args = parser.parse_args()

    args.base_point = json.loads(args.base_point)
    bx = args.base_point[0]
    by = args.base_point[1]
    input_fname = args.input + "_dimension.csv"     
    output_fname = args.output + ".ifc"
    geo_to_bim(input_fname, output_fname, bx, by)

    # output_fname = args.output + "_sample_building.ifc"
    # ifc_building.create_sample_building(output_fname)    # TBD. test. not working

if __name__ == '__main__':
    main()

