bl_info = {
    "name": "Spine 4.0 mesh builder",
    "author": "Narrow",
    "version": (1, 0, 0),
    "blender": (3, 4, 0),
    "location": "View3D > Sidebar > Spine 4.0 importer",
    "description": "Construct Spine 4.0 meshes (no ik, nor bones) from json files",
    "warning": "",
    "doc_url": "",
    "category": "Mesh",
}

from . import convert_skel_json_to_mesh

def register():
    convert_skel_json_to_mesh.register()

def unregister():
    convert_skel_json_to_mesh.unregister()