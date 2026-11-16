"""Run in Blender background mode after generating outputs/model.json."""
from pathlib import Path
import json
import sys

import bpy
from mathutils import Vector

root = Path(__file__).resolve().parent
directory = Path(sys.argv[sys.argv.index("--")+1]) if "--" in sys.argv else root/"outputs"
directory = directory.resolve()
model = json.loads((directory/"model.json").read_text(encoding="utf-8"))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"

PALETTE={
    "wall_skin": (0.65,0.43,0.23), "gable": (0.51,0.33,0.17),
    "roof_skin": (0.14,0.24,0.24), "floor_skin": (0.43,0.31,0.18),
    "illustrative_ribs": (0.70,0.49,0.25), "glazing": (0.32,0.53,0.61),
    "foundation_placeholders": (0.40,0.43,0.42), "access_placeholders": (0.36,0.40,0.39),
}


def material(name, color):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    shader=m.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value=(*color,1)
    shader.inputs["Roughness"].default_value=0.48
    return m


collections={}
materials={}
objects=[]
for p in model["parts"]:
    group=p["group"]
    if group not in collections:
        collection=bpy.data.collections.new(group)
        scene.collection.children.link(collection)
        collections[group]=collection
    index=sum(p["name"].encode())%3 if group=="wall_skin" else 0
    key=(group,index)
    if key not in materials:
        materials[key]=material(f"{group}-{index}",tuple(c*(1-index*0.048) for c in PALETTE[group]))
    mesh=bpy.data.meshes.new(p["name"])
    mesh.from_pydata([tuple(v/1000 for v in xyz) for xyz in p["vertices"]],[],p["faces"])
    mesh.update()
    obj=bpy.data.objects.new(p["name"],mesh)
    collections[group].objects.link(obj)
    obj.data.materials.append(materials[key])
    obj["ifc_class"]=p["ifc_class"]
    obj["model_status"]="Study geometry"
    obj.select_set(True)
    objects.append(obj)

bpy.ops.export_scene.gltf(filepath=str(directory/"cabin.glb"),export_format="GLB",use_selection=True,export_extras=True)
for obj in objects:
    obj.select_set(False)
scene.world=bpy.data.worlds.new("Soft sky")
scene.world.use_nodes=True
scene.world.node_tree.nodes.get("Background").inputs["Color"].default_value=(0.75,0.83,0.9,1)
scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value=0.5
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-0.015))
ground=bpy.context.object
ground.name="Presentation surface"
ground.data.materials.append(material("Warm white ground",(0.79,0.77,0.71)))


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def light(name,position,power,size,color):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power
    data.shape="DISK"
    data.size=size
    data.color=color
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=position
    aim(obj,(1.5,1.6,1.3))


light("Key",(0,-4,8),1150,5,(1,0.89,0.72))
light("Fill",(6,3,5),600,5,(0.76,0.86,1))
camera=bpy.data.cameras.new("Cabin orthographic")
cam=bpy.data.objects.new("Cabin orthographic",camera)
scene.collection.objects.link(cam)
cam.location=(8,-9,6.7)
aim(cam,(1.45,1.35,1.85))
camera.type="ORTHO"
camera.ortho_scale=7.3
scene.camera=cam
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=48
scene.cycles.use_denoising=False
scene.render.resolution_x=1080
scene.render.resolution_y=780
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="JPEG"
scene.render.image_settings.quality=87
scene.render.filepath=str(directory/"cabin.jpg")
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(directory/"cabin.blend"),compress=True)
bpy.ops.render.render(write_still=True)
