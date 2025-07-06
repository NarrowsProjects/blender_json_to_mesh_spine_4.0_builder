# **Spine 4.0 Mesh Builder for Blender 3.4**  
## **Overview**  
This Blender plugin allows you to build **Spine 4.0** meshes and submeshes by processing:  
1. A **JSON skeleton file** (Spine 4.0 animation data).  
2. A **complete atlas file** (texture atlas metadata).  
3. A **texture file** (the actual image used for rendering).  

The plugin constructs a mesh in Blender based on the Spine skeleton data, applying the correct UV mapping and texture assignments.  

Additionally, it includes an optional **size adjustment** feature to correct discrepancies in atlas dimensions caused by texture compression.

---

## **Installation**  
1. **Download the Plugin**  
   - Obtain the `.zip` file containing the plugin.  

2. **Install in Blender**  
   - Open Blender 3.4.  
   - Go to **Edit > Preferences > Add-ons**.  
   - Click **Install…** and select the plugin `.zip` file.  
   - Enable the add-on by checking the box next to its name.  

3. **Verify Installation**  
   - The plugin should now be available in Blender’s **Side Panel (press N)** under the dedicated tab.  

---

## **Usage**  

### **Step 1: Prepare Your Files**  
Ensure you have:  
- A **Spine 4.0 JSON skeleton file** (`.json`).  
- A **matching atlas file** (`.atlas`).  
- The **texture file** (`.png`, `.jpg`, etc.) referenced in the atlas.  

### **Step 2: Open the Plugin Panel**  
- In Blender, open the **Side Panel (N Panel)**.  
- Locate the **Spine Builder** tab.  

### **Step 3: Load Files**  
1. **Skeleton JSON** – Browse and select your Spine JSON file.  
2. **Atlas File** – Select the corresponding `.atlas` file.  
3. **Texture File** – Choose the texture image.  

### **Step 4: Adjust Settings (If Needed)**  
- **Size Adjustment** – If the mesh appears distorted due to incorrect atlas dimensions, adjust the scale values (X, Y) to compensate.  

### **Step 5: Generate Mesh**  
- Click **"Create Spine Mesh"**.  
- The mesh will be generated in the Blender viewport with proper UVs and textures.  

---

## **Troubleshooting**  

### **Common Issues & Fixes**  
| Issue | Possible Solution |  
|-------|------------------|  
| **Mesh appears distorted** | Adjust the **Size Adjustment** values in the plugin. |  
| **UVs are misaligned** | Check if the atlas file has incorrect `size` or `xy` values. by comparing them to the actual texture file |  



## **Limitations**  
⚠ **Only Supports Spine 4.0** – Both earlier, and later versions of spine change the json skeleton structure. This can be amended by changing the navigation in create_spine_mesh(), but the base implementation is purely for spine 4.0.  
⚠ **Basic Mesh Reconstruction** – Advanced Spine features (e.g., deform animations) are not build.  
⚠ **Blender 3.4 Only** – It likely still works with later versions, but that has not been tested.  
