"""Create an IFC4 reference model in metres from the same review geometry."""
import argparse
import json
from pathlib import Path

import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit


def export(payload, output):
    api=ifcopenshell.api
    model=api.project.create_file(version="IFC4")
    def new(kind,name):
        return api.root.create_entity(model,ifc_class=kind,name=name)
    project=new("IfcProject","Lecture 7 cabin study")
    site=new("IfcSite","Synthetic site")
    building=new("IfcBuilding","Raised gable cabin")
    level=new("IfcBuildingStorey","Cabin")
    for parent,child in ((project,site),(site,building),(building,level)):
        api.aggregate.assign_object(model,products=[child],relating_object=parent)
    api.unit.assign_unit(model,units=[api.unit.add_si_unit(model,unit_type=x) for x in ("LENGTHUNIT","AREAUNIT","VOLUMEUNIT")])
    model_context=api.context.add_context(model,context_type="Model")
    body=api.context.add_context(model,context_type="Model",context_identifier="Body",target_view="MODEL_VIEW",parent=model_context)
    for part in payload["parts"]:
        product=new(part["ifc_class"],part["name"])
        mesh=api.geometry.add_mesh_representation(model,context=body,
            vertices=[[tuple(v/1000 for v in xyz) for xyz in part["vertices"]]],faces=[part["faces"]])
        api.geometry.assign_representation(model,product=product,representation=mesh)
        api.spatial.assign_container(model,products=[product],relating_structure=level)
        api.geometry.edit_object_placement(model,product=product)
        pset=api.pset.add_pset(model,product=product,name="Lecture7_Study")
        values={"GeometryGroup":part["group"],"Status":"Concept reference geometry"}
        if part["blank"]:
            values["BlankArea_m2"] = part["blank"][0]*part["blank"][1]/1e6
        api.pset.edit_pset(model,pset=pset,properties=values)
    model.write(str(output))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=Path("outputs/model.json"))
    parser.add_argument("--out",type=Path,default=Path("outputs/cabin.ifc"))
    args=parser.parse_args()
    export(json.loads(args.input.read_text(encoding="utf-8")),args.out)
