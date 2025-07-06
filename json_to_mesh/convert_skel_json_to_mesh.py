import bpy
import json
import os
import math
from mathutils import Vector, Matrix
from bpy.props import StringProperty, IntProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup

class SpineImportProperties(PropertyGroup):
    json_file_path: StringProperty(
        name="JSON File",
        description="Path to Spine JSON file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    
    atlas_file_path: StringProperty(
        name="Atlas File",
        description="Path to the .atlas.txt file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    
    texture_file_path: StringProperty(
        name="Texture File",
        description="Path to the texture image file (.png)",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    
    texture_size_adjustment: IntProperty(
        name="Texture Size Adjustment",
        description="Adjustment factor for texture size",
        default=2,
        min=1,
        max=10
    )

class SPINE_OT_import(Operator):
    """Create Spine Mesh"""
    bl_idname = "import_scene.spine_animation"
    bl_label = "Create Spine Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.spine_build_props
        
        if not props.json_file_path:
            self.report({'ERROR'}, "No JSON file selected")
            return {'CANCELLED'}
            
        # Initialize your importer
        importer = SpineBuilder(
            json_file_path=props.json_file_path,
            atlas_file_path=props.atlas_file_path,
            texture_file_path=props.texture_file_path,
            texture_size_adjustment=props.texture_size_adjustment
        )
        
        importer.create_spine_mesh()
        
        self.report({'INFO'}, "Spine animation imported successfully")
        return {'FINISHED'}

class SPINE_PT_import_panel(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Spine Mesh Builder"
    bl_idname = "SPINE_PT_import_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Spine Tools'  # This will create a new tab in the sidebar
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.spine_build_props
        
        # File selection
        layout.label(text="File Paths:")
        layout.prop(props, "json_file_path")
        layout.prop(props, "atlas_file_path")
        layout.prop(props, "texture_file_path")
        
        # Settings
        layout.label(text="Settings:")
        layout.prop(props, "texture_size_adjustment")
        
        layout.operator(SPINE_OT_import.bl_idname, text="Build Spine Mesh")


class SpineBuilder:
    """Main class for building Spine Meshe"""
    
    def __init__(self, json_file_path, atlas_file_path, texture_file_path, texture_size_adjustment):
        self.json_file_path = json_file_path
        self.atlas_file_path = atlas_file_path
        self.texture_file_path = texture_file_path
        self.texture_size_adjustment = texture_size_adjustment

        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)

        created_objects = self.create_spine_mesh()

    def build_bone_global_transforms(self, bones_data):
        """
        Build global transformation matrices for all bones in the skeleton.
        
        This function calculates the global transformation matrix for each bone by
        combining its local transformation with its parent's global transformation.
        The global transforms are used to position vertices correctly in world space.
        
        Args:
            bones_data (list): List of bone dictionaries containing bone information
                            including name, position, rotation, scale, and parent relationships.
        
        Returns:
            dict: Dictionary mapping bone indices to their global transformation matrices.
                Key: int (bone index), Value: Matrix (4x4 transformation matrix)
        """
        bone_transforms = {}
        bone_name_to_index = {}
        
        for i, bone in enumerate(bones_data):
            bone_name_to_index[bone['name']] = i
            
        # Calculate global transforms for all bones
        for i in range(len(bones_data)):
            self.get_bone_global_transform(i, bone_transforms, bones_data, bone_name_to_index)
        
        return bone_transforms

    def get_bone_global_transform(self, bone_index, bone_transforms, bones_data, bone_name_to_index):
        """
        Recursively calculate the global transformation matrix for a specific bone.
        
        This function uses memoization to avoid recalculating transforms and handles
        the parent-child relationship hierarchy. It combines translation, rotation,
        and scaling to create the final transformation matrix.
        
        Args:
            bone_index (int): Index of the bone to calculate transform for
            bone_transforms (dict): Cache of already calculated bone transforms
            bones_data (list): List of all bone data dictionaries
            bone_name_to_index (dict): Mapping of bone names to their indices
        
        Returns:
            Matrix: 4x4 global transformation matrix for the specified bone
        """
        if bone_index in bone_transforms:
            return bone_transforms[bone_index]
        
        bone = bones_data[bone_index]
        
        # Local transform
        x = bone.get('x', 0.0)
        y = bone.get('y', 0.0)
        rotation = math.radians(bone.get('rotation', 0.0))
        scale_x = bone.get('scaleX', 1.0)
        scale_y = bone.get('scaleY', 1.0)
        
        local_transform = Matrix.Translation((x, y, 0.0)) @ Matrix.Rotation(rotation, 4, 'Z')
        local_transform[0][0] *= scale_x
        local_transform[1][1] *= scale_y
        
        # If bone has parent, multiply by parent's global transform
        if 'parent' in bone:
            parent_index = bone_name_to_index[bone['parent']]
            parent_global_transform = self.get_bone_global_transform(parent_index, bone_transforms, bones_data, bone_name_to_index)
            global_transform = parent_global_transform @ local_transform
        else:
            global_transform = local_transform
        
        bone_transforms[bone_index] = global_transform
        return global_transform


    def calculate_weighted_vertex_position(self, bone_influences, bone_global_transforms):
        """
        Calculate the final world position of a vertex using weighted bone influences.
        
        This function implements skeletal animation vertex skinning by transforming
        the vertex's local coordinates relative to each influencing bone, then
        blending the results based on the bone weights.
        
        Args:
            bone_influences (list): List of tuples containing (bone_index, local_x, local_y, weight)
                                representing how each bone influences this vertex
            bone_global_transforms (dict): Dictionary of bone indices to their global transform matrices
        
        Returns:
            tuple: (final_x, final_y) - The calculated world position of the vertex
        """
        final_x = 0.0
        final_y = 0.0
        
        for bone_index, local_x, local_y, weight in bone_influences:
            # Transform local coordinates by bone's global matrix
            if bone_index in bone_global_transforms:
                global_transform = bone_global_transforms[bone_index]
                local_pos = Vector((local_x, local_y, 0.0, 1.0))
                global_pos = global_transform @ local_pos
                
                # Add weighted contribution
                final_x += global_pos.x * weight
                final_y += global_pos.y * weight
            else:
                final_x += local_x * weight
                final_y += local_y * weight
        
        return (final_x, final_y)

    def parse_spine_vertices(self, vertices_array, bone_global_transforms):
        """
        Parse Spine's vertex data format and convert to world-space vertex positions.
        
        Spine stores vertices in a specific format where each vertex has one or more
        bone influences. This function parses that format and calculates the final
        world positions using the bone transformations.
        
        Args:
            vertices_array (list): Raw vertex data from Spine JSON in the format:
                                [bone_count, bone_index, local_x, local_y, weight, ...]
            bone_global_transforms (dict): Dictionary of bone global transformation matrices
        
        Returns:
            list: List of vertex positions as tuples (x, y, z) in world space
        """
        vertices = []
        i = 0
        
        while i < len(vertices_array):
            bone_count = int(vertices_array[i])
            i += 1
            
            bone_influences = []
            
            for j in range(bone_count):
                bone_index = int(vertices_array[i])
                local_x = vertices_array[i + 1]
                local_y = vertices_array[i + 2]
                weight = vertices_array[i + 3]
                i += 4
                
                bone_influences.append((bone_index, local_x, local_y, weight))
            
            # Calculate weighted global position
            final_x, final_y = self.calculate_weighted_vertex_position(bone_influences, bone_global_transforms)
            vertices.append((final_x, final_y, 0.0))
        
        return vertices

    def atlas_to_dict(self):
        """
        Parse a Spine texture atlas file and convert it to a dictionary structure.
        
        Spine atlas files contain information about how individual images are packed
        into a larger texture atlas. This function parses that text format and creates
        a structured dictionary for easier access to region information.
        
        Returns:
            dict: Nested dictionary structure with atlas data:
                {texture_file: {region_name: {property: value}}}
                Properties include xy, size, rotate, orig, offset, etc.
        """
        with open(self.atlas_file_path, 'r') as atlas_file:
            lines = atlas_file.readlines()

        sections = []
        current_section = []

        for line in lines:
            line = line.strip()
            if line.endswith('.png'):
                if current_section:
                    sections.append(current_section)
                    current_section = []
                current_section.append(line)
            else:
                if line:
                    current_section.append(line)
        sections.append(current_section)

        atlas_data = {}
        current_texture = None
        for section in sections:
            atlas_data[section[0]] = {}
            for line in section:
                if not line or line.startswith("#"): 
                    continue
                if not line.startswith(("rotate:", "xy:", "size:", "orig:", "offset:", "index:", "format:", "filter:", "repeat:")):
                    current_texture = line
                    atlas_data[section[0]][current_texture] = {}
                else:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    atlas_data[section[0]][current_texture][key] = value

        return atlas_data

    def get_atlas_texture_info(self):
        """
        Extract texture size and region information from the atlas data.
        
        This function processes the parsed atlas data to extract the main texture
        dimensions and create a lookup table for all texture regions with their
        positions, sizes, and rotation information.
        
        Returns:
            tuple: (texture_size, attachment_regions) where:
                - texture_size is a tuple (width, height) of the main texture
                - attachment_regions is a dict mapping region names to their properties
                    including x, y, width, height, and rotation status
        """
        atlas_data = self.atlas_to_dict()

        texture_file = None
        for key in atlas_data.keys():
            if key.endswith('.png'):
                texture_file = key
                break
        
        if not texture_file:
            print("No texture file found in atlas")
            return None, {}
        
        # Extract texture size
        texture_size = (2048, 2048)  # Common spine texture size in case it isn't listed for some reason
        if 'size' in atlas_data[texture_file]:
            size_str = atlas_data[texture_file]['size']
            if ',' in size_str:
                width, height = map(int, size_str.split(','))
                texture_size = (width, height)
        
        attachment_regions = {}
        for attachment_name, props in atlas_data[texture_file].items():
            if isinstance(props, dict) and 'xy' in props and 'size' in props:
                xy_str = props['xy']
                x, y = map(int, xy_str.split(','))
                
                size_str = props['size']
                width, height = map(int, size_str.split(','))
                is_rotated = props.get('rotate', 'false').lower() == 'true'
                
                attachment_regions[attachment_name] = {
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height,
                    'rotated': is_rotated
                }
        
        return texture_size, attachment_regions

    def transform_uv_with_atlas(self, uvs, attachment_name, texture_size, attachment_regions):
        """
        Transform UV coordinates from local attachment space to atlas texture space.
        
        This function takes UV coordinates that are normalized to a single attachment
        and transforms them to the correct coordinates within the larger texture atlas.
        It also handles rotated attachments by applying the necessary UV rotation.
        
        Args:
            uvs (list): List of UV coordinates in the format [u1, v1, u2, v2, ...]
            attachment_name (str): Name of the attachment/region to transform UVs for
            texture_size (tuple): (width, height) of the full atlas texture
            attachment_regions (dict): Dictionary containing region information
        
        Returns:
            list: Transformed UV coordinates mapped to the atlas texture space
        """
        if attachment_name not in attachment_regions:
            print(f"Atlas region not found for attachment: {attachment_name}")
            return uvs
        
        region = attachment_regions[attachment_name]
        atlas_width, atlas_height = texture_size
        
        region_x = region['x'] / atlas_width / self.texture_size_adjustment
        region_y = region['y'] / atlas_height / self.texture_size_adjustment
        region_width = region['width'] / atlas_width / self.texture_size_adjustment
        region_height = region['height'] / atlas_height / self.texture_size_adjustment
        
        transformed_uvs = []
        
        for i in range(0, len(uvs), 2):
            u = uvs[i]
            v = uvs[i + 1]
            
            if region['rotated']:
                rotated_u = v
                rotated_v = 1.0 - u
                
                new_u = region_x + rotated_u * region_height
                new_v = region_y + rotated_v * region_width
            else:
                # Normal case: map UV to the atlas region
                new_u = region_x + u * region_width
                new_v = region_y + v * region_height
            
            transformed_uvs.extend([new_u, new_v])
        
        return transformed_uvs

    def create_spine_mesh(self):
        """
        Main function to create Blender mesh objects from Spine animation data.
        
        This function orchestrates the entire import process by:
        1. Loading and parsing the Spine JSON data
        2. Building bone transformation matrices
        3. Loading atlas texture information
        4. Creating mesh objects for each slot/attachment
        5. Applying proper UV mapping and materials
        
        Returns:
            list: List of created Blender objects
        """
        with open(self.json_file_path, 'r') as file:
            json_data = json.load(file)
        
        bone_global_transforms = self.build_bone_global_transforms(json_data['bones'])
        
        # Get atlas information
        texture_size, attachment_regions = self.get_atlas_texture_info()
        print(f"Atlas texture size: {texture_size}")
        print(f"Found {len(attachment_regions)} attachment regions")
        
        skin = json_data['skins'][0]
        slots = json_data['slots']
        created_objects = []

        atlas_image = self.load_texture_image(self.texture_file_path)

        for slot in slots:
            slot_name = slot['name']
            attachments = skin['attachments'].get(slot_name, {})
            result = next(((a_n, m_d) for a_n, m_d in attachments.items() if a_n == slot_name), None)

            if result == None:
                continue

            attachment_name, mesh_data = result
            mesh_name = f"{slot_name}:{attachment_name}"
            
            # Skip if not a mesh type
            if mesh_data.get('type') != 'mesh':
                continue
            
            # Parse vertices and triangles
            vertices = self.parse_spine_vertices(mesh_data['vertices'], bone_global_transforms)
            triangles = mesh_data['triangles']
            uvs = mesh_data['uvs']
            
            transformed_uvs = self.transform_uv_with_atlas(uvs, attachment_name, texture_size, attachment_regions)
            
            # Create faces from the triangle list
            faces = []
            for i in range(0, len(triangles), 3):
                face = [triangles[i], triangles[i + 1], triangles[i + 2]]
                faces.append(face)
            
            mesh, obj = self.create_mesh_obj(mesh_name, vertices, faces)
            
            material = self.create_material_with_texture(f"Material_{mesh_name}", atlas_image)
            mesh.materials.append(material)

            if transformed_uvs and len(transformed_uvs) >= len(vertices) * 2:
                uv_layer = mesh.uv_layers.new(name="UVMap")
                
                # Apply UV coordinates to each face
                for poly in mesh.polygons:
                    for loop_idx in poly.loop_indices:
                        vert_idx = mesh.loops[loop_idx].vertex_index
                        
                        u = transformed_uvs[vert_idx * 2]
                        v = 1.0 - transformed_uvs[vert_idx * 2 + 1]  # Blender starts at a different corner from spine.
                        
                        uv_layer.data[loop_idx].uv = (u, v)
                
                print(f"Applied atlas-transformed UV coordinates to {mesh_name}")
                if attachment_name in attachment_regions:
                    region = attachment_regions[attachment_name]
                    print(f"  Atlas region: {region}")
            else:
                print(f"No UV data or insufficient UV data for {mesh_name}")
            
            created_objects.append(obj)
            print(f"Created mesh: {mesh_name} with {len(vertices)} vertices and {len(faces)} faces")
        
        return created_objects

    def create_mesh_obj(self, mesh_name, vertices, faces):
        """
        Create a Blender mesh object from vertex and face data.
        
        This function creates a new Blender mesh and object, populates it with
        the provided geometry data, and adds it to the current scene collection.
        
        Args:
            mesh_name (str): Name for the mesh and object
            vertices (list): List of vertex positions as tuples (x, y, z)
            faces (list): List of face indices as lists of vertex indices
        
        Returns:
            tuple: (mesh, obj) - The created Blender mesh and object
        """
        mesh = bpy.data.meshes.new(mesh_name)
        obj = bpy.data.objects.new(mesh_name, mesh)
        bpy.context.collection.objects.link(obj)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        
        return mesh, obj


    def create_material_with_texture(self, material_name, texture_image):
        """
        Create a Blender material with a texture image using shader nodes.
        
        This function creates a material with a proper shader node setup for
        displaying textured meshes with alpha transparency support.
        
        Args:
            material_name (str): Name for the created material
            texture_image (bpy.types.Image): Blender image object to use as texture
        
        Returns:
            bpy.types.Material: The created material with shader nodes configured
        """
        material = bpy.data.materials.new(name=material_name)
        material.use_nodes = True
        
        nodes = material.node_tree.nodes
        nodes.clear()
        
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        tex_image = nodes.new(type='ShaderNodeTexImage')
        output = nodes.new(type='ShaderNodeOutputMaterial')
        
        tex_image.image = texture_image
        
        links = material.node_tree.links
        links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
        links.new(tex_image.outputs['Alpha'], bsdf.inputs['Alpha'])
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        material.blend_method = 'BLEND'
        
        return material

    def load_texture_image(self, texture_path):
        """
        Load a texture image file into Blender, with caching support.
        
        This function loads an image file for use as a texture, checking first
        if the image is already loaded in Blender to avoid duplicates.
        
        Args:
            texture_path (str): Full file path to the texture image
        
        Returns:
            bpy.types.Image or None: The loaded image object, or None if loading failed
        """
        if not os.path.exists(texture_path):
            print(f"Texture not found: {texture_path}")
            return None
        
        image_name = os.path.basename(texture_path)
        if image_name in bpy.data.images:
            return bpy.data.images[image_name]
        
        # Load new image
        try:
            image = bpy.data.images.load(texture_path)
            print(f"Loaded texture: {texture_path}")
            return image
        except Exception as e:
            print(f"Failed to load texture {texture_path}: {e}")
            return None
        
# Registration
classes = (
    SpineImportProperties,
    SPINE_OT_import,
    SPINE_PT_import_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add properties to the scene
    bpy.types.Scene.spine_build_props = PointerProperty(type=SpineImportProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Remove properties from the scene
    del bpy.types.Scene.spine_build_props
