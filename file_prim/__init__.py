import bpy
import os

from . import bl_utils_prim
from .. import BlenderUI
from ..file_aloc import format as aloc_format
from ..file_mat import materials as mat_materials
import mathutils
import threading

from bpy_extras.io_utils import ImportHelper, ExportHelper

from bpy.props import (
    StringProperty,
    BoolProperty,
    BoolVectorProperty,
    CollectionProperty,
    PointerProperty,
    IntProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntVectorProperty,
)

from bpy.types import (
    Context,
    Panel,
    Operator,
    PropertyGroup,
)

materials = mat_materials.Materials()


class ImportPRIM(bpy.types.Operator, ImportHelper):
    """Load a PRIM file"""

    bl_idname = "import_mesh.prim"
    bl_label = "Import PRIM Mesh"
    filename_ext = ".prim"

    filter_glob: StringProperty(
        default="*.prim",
        options={"HIDDEN"},
    )

    files: CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    use_rig: BoolProperty(
        name="Use BoneRig", description="Use a BORG file on the chosen prim file"
    )

    rig_filepath: StringProperty(
        name="BoneRig Path",
        description="Path to the BoneRig (BORG) file",
    )

    use_aloc: BoolProperty(
        name="Use Collision", description="Use a ALOC file on the chosen prim file"
    )

    aloc_filepath: StringProperty(
        name="Collision Path",
        description="Path to the Collision (ALOC) file",
    )

    def draw(self, context):
        if ".prim" not in self.filepath.lower():
            return

        layout = self.layout
        if os.path.exists(self.filepath):
            layout.label(text="import options:")
            is_weighted_prim = bl_utils_prim.is_weighted(self.filepath)
            if not is_weighted_prim:
                layout.label(
                    text="The selected prim does not support a rig", icon="ERROR"
                )
            elif len(self.files) - 1:
                layout.label(text="Rigs are not supported when batch importing")
            else:
                row = layout.row(align=True)
                row.prop(self, "use_rig")
                row = layout.row(align=True)
                row.enabled = self.use_rig
                row.prop(self, "rig_filepath")

                if self.use_rig:
                    f = None
                    try:
                        f = open(
                            os.fsencode(self.rig_filepath.replace(os.sep, "/")), "rb"
                        )
                    except IOError:
                        layout.label(text="Given filepath not valid", icon="ERROR")
                    finally:
                        if f:
                            f.close()

        layout.row(align=True)

    def execute(self, context):
        from . import bl_import_prim

        prim_paths = [
            "%s\\%s" % (os.path.dirname(self.filepath), meshPaths.name)
            for meshPaths in self.files
        ]
        for prim_path in prim_paths:
            collection = bpy.data.collections.new(
                bpy.path.display_name_from_filepath(prim_path)
            )

            self.rig_filepath = self.rig_filepath.replace(os.sep, "/")

            arma_obj = None
            if self.use_rig:
                from ..file_borg import bl_import_borg

                armature = bl_import_borg.load_borg(self, context, self.rig_filepath)
                arma_obj = bpy.data.objects.new(armature.name, armature)
                collection.objects.link(arma_obj)

            objects = bl_import_prim.load_prim(
                self, context, collection, prim_path, self.use_rig, self.rig_filepath
            )

            if not objects:
                BlenderUI.MessageBox(
                    'Failed to import "%s"' % prim_path, "Importing error", "ERROR"
                )
                return {"CANCELLED"}

            for obj in objects:
                if self.use_rig and arma_obj:
                    obj.modifiers.new(name="Glacier Bonerig", type="ARMATURE")
                    obj.modifiers["Glacier Bonerig"].object = arma_obj

                obj.data.polygons.foreach_set(
                    "use_smooth", [True] * len(obj.data.polygons)
                )

                collection.objects.link(obj)

            context.scene.collection.children.link(collection)
            layer = bpy.context.view_layer
            layer.update()

        return {"FINISHED"}


class ExportPRIM(bpy.types.Operator, ExportHelper):
    """Export to a PRIM file"""

    bl_idname = "export_mesh.prim"
    bl_label = "Export PRIM Mesh"
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {"PRESET"}
    check_extension = True
    filename_ext = ".prim"
    filter_glob: StringProperty(default="*.prim", options={"HIDDEN"})

    def get_collections(self, context):
        items = [(col.name, col.name, "") for col in bpy.data.collections]

        for i, coll_name in enumerate(items):
            if coll_name[0] == bpy.context.collection.name:
                items[0], items[i] = items[i], items[0]

        return items

    export_collection: EnumProperty(
        name="",
        description="The collection to turn into a prim",
        items=get_collections,
        default=None,
    )

    export_scene: BoolProperty(
        name="Export Scene",
        description="Export PRIMs, Materials, Textures, Geomentities, and Collisions",
        default=False,
    )

    export_all_collections: BoolProperty(
        name="Export All Collections",
        description="Exports all of the 'root' collections in main Scene Collection as PRIMs",
        default=True,
    )

    collection_folders: BoolProperty(
        name="Export Collection(s) To Named Folders",
        description="Exports collection(s) to folders having the same name as the collection",
        default=True,
    )

    export_materials_textures: BoolProperty(
        name="Export Materials/Textures",
        description="Exports materials/textures linked to a given collection and creates the files for use in SMF, including:\n  - material.json\n  - TEXTHASH~TEXDHASH.tga\n  - TEXTHASH~TEXDHASH.tga.meta",
        default=True,
    )

    export_geomentity: BoolProperty(
        name="Export Geomentities",
        description="Exports geomentities for each PRIM and links it to an ALOC if one was generated for the given PRIM",
        default=True,
    )

    hitbox_slider: IntVectorProperty(
        name="",
        description="Configures the hitbox density of the output PRIM.\nLower values equal higher density and vice versa",
        default=(32,),
        size=1,
        min=1,
        max=512,
    )

    force_highres_flag: BoolProperty(
        name="Force high resolution flag",
        description="Forces the PRIM to be saved with the high resolution flag set",
        default=False,
    )

    def draw(self, context):
        if ".prim" not in self.filepath.lower():
            return

        layout = self.layout
        layout.label(text="Export options:")
        row = layout.row(align=True)
        row.prop(self, "export_collection")
        layout.label(text="Advanced options:")
        layout.label(text="Hitbox density value:")
        row = layout.row(align=True)
        row.prop(self, "hitbox_slider")
        row = layout.row(align=True)
        row.prop(self, "force_highres_flag")
        if self.export_scene:
            row = layout.row(align=True)
            row.prop(self, "export_all_collections")
            row = layout.row(align=True)
            row.prop(self, "collection_folders")
            row = layout.row(align=True)
            row.prop(self, "export_materials_textures")
            row = layout.row(align=True)
            row.prop(self, "export_geomentity")

    def execute(self, context):
        from . import bl_export_prim

        keywords = self.as_keywords(
            ignore=("check_existing", "filter_glob", "export_collection")
        )

        return bl_export_prim.save_prim(
            bpy.data.collections[self.export_collection], **keywords
        )


class PrimCollectionProperties(PropertyGroup):
    bone_rig_resource_index: IntProperty(
        name="Bone Rig Resource Index",
        description="",
        default=-1,
        min=-1,
        max=1000,
        step=1,
    )

    has_bones: BoolProperty(
        name="Has Bones",
        description="The prim has bones",
    )

    has_frames: BoolProperty(
        name="Has Frames",
    )

    is_linked: BoolProperty(
        name="Linked",
        description="The prim is linked",
    )

    is_weighted: BoolProperty(
        name="Weighted",
        description="The prim is weighted",
    )

    physics_data_type_items = [
        (str(layer.value), layer.name, "") for layer in aloc_format.PhysicsDataType
    ]

    physics_collision_type_items = [
        (str(layer.value), layer.name, "") for layer in aloc_format.PhysicsCollisionType
    ]

    physics_data_type: EnumProperty(
        name="Physics Data Type",
        description="Physics Data Types",
        items=physics_data_type_items,
    )

    physics_collision_type: EnumProperty(
        name="Physics Collision Type",
        description="Physics Collision Types",
        items=physics_collision_type_items,
    )

    # Entity Properties
    # static and rigid body
    m_bRemovePhysics: BoolProperty(
        name="Remove Physics", description="Remove physics", default=False
    )

    # rigid body
    m_bKinematic: BoolProperty(name="Kinematic", description="Kinematic", default=False)

    # rigid body
    m_bStartSleeping: BoolProperty(
        name="Start Sleeping", description="Start Sleeping", default=False
    )

    # rigid body
    m_bIgnoreCharacters: BoolProperty(
        name="Ignore Characters", description="Ignore Characters", default=False
    )

    # rigid body
    m_bEnableCollision: BoolProperty(
        name="Enable Collision", description="Enable Collision", default=True
    )

    # rigid body
    m_bAllowKinematicKinematicContactNotification: BoolProperty(
        name="Allow Kinematic to Kinematic Contact Notification",
        description="Allow Kinematic to Kinematic Contact Notification",
        default=False,
    )

    # rigid body
    m_fMass: FloatProperty(name="Mass", description="Mass", default=1.0, min=0.1)

    # rigid body
    m_fFriction: FloatProperty(
        name="Friction", description="Friction", default=0.5, min=0
    )

    # rigid body
    m_fRestitution: FloatProperty(
        name="Restitution", description="Restitution", default=0.4, min=0, max=0.95
    )

    # rigid body
    m_fLinearDampening: FloatProperty(
        name="Linear Dampening", description="Linear Dampening", default=0.05, min=0
    )

    # rigid body
    m_fAngularDampening: FloatProperty(
        name="Angular Dampening", description="Angular Dampening", default=0.05, min=0
    )

    # rigid body
    m_fSleepEnergyThreshold: FloatProperty(
        name="Sleep Energy Threshold",
        description="Sleep Energy Threshold",
        default=0.05,
        min=0,
    )

    # rigid body
    m_ePriority: EnumProperty(
        name="Collision Priority",
        description="Collision Priority",
        items=[
            ("ECOLLISIONPRIORITY_LOW", "Low", ""),
            ("ECOLLISIONPRIORITY_NORMAL", "Normal", ""),
            ("ECOLLISIONPRIORITY_HIGH", "High", ""),
            ("ECOLLISIONPRIORITY_CRITICAL", "Critical", ""),
        ],
        default="ECOLLISIONPRIORITY_NORMAL",
    )

    # rigid body
    m_eCCD: EnumProperty(
        name="CCD",
        description="CCD",
        items=[
            ("ECCDUSAGE_DISABLED", "Disabled", ""),
            ("ECCDUSAGE_AGAINST_STATIC", "Against Static", ""),
            ("ECCDUSAGE_AGAINST_STATIC_DYNAMIC", "Against Static Dynamic", ""),
        ],
        default="ECCDUSAGE_DISABLED",
    )

    # rigid body
    m_eCenterOfMass: EnumProperty(
        name="Center Of Mass",
        description="Center Of Mass",
        items=[
            ("ECOMUSAGE_AUTOCOMPUTE", "Auto Compute", ""),
            ("ECOMUSAGE_PIVOT", "Pivot", ""),
        ],
        default="ECOMUSAGE_AUTOCOMPUTE",
    )


class GLACIER_PT_PrimCollectionPropertiesPanel(bpy.types.Panel):
    bl_idname = "GLACIER_PT_PrimCollectionPropertiesPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "collection"
    bl_category = "Glacier"
    bl_label = "Global Prim Properties"

    @classmethod
    def poll(self, context):
        return context.collection is not None

    def draw(self, context):
        coll = context.collection
        layout = self.layout

        layout.row(align=True).prop(
            coll.prim_collection_properties, "bone_rig_resource_index"
        )

        layout.label(text="Flags:")

        row = layout.row(align=True)
        row.prop(coll.prim_collection_properties, "has_bones")
        row.prop(coll.prim_collection_properties, "has_frames")
        row.enabled = False

        row = layout.row(align=True)
        row.prop(coll.prim_collection_properties, "is_linked")
        row.prop(coll.prim_collection_properties, "is_weighted")
        row.enabled = False

        layout.label(text="Physics Data Type:")
        row = layout.row(align=True)
        row.prop(coll.prim_collection_properties, "physics_data_type", text="")

        layout.label(text="Physics Collision Type:")
        row = layout.row(align=True)
        row.prop(coll.prim_collection_properties, "physics_collision_type", text="")

        if int(coll.prim_collection_properties.physics_collision_type) == int(
            aloc_format.PhysicsCollisionType.STATIC
        ):
            layout.prop(coll.prim_collection_properties, "m_bRemovePhysics")

        if int(coll.prim_collection_properties.physics_collision_type) == int(
            aloc_format.PhysicsCollisionType.RIGIDBODY
        ):
            layout.prop(coll.prim_collection_properties, "m_bRemovePhysics")
            layout.prop(coll.prim_collection_properties, "m_bKinematic")
            layout.prop(coll.prim_collection_properties, "m_bStartSleeping")
            layout.prop(coll.prim_collection_properties, "m_bIgnoreCharacters")
            layout.prop(coll.prim_collection_properties, "m_bEnableCollision")
            layout.prop(
                coll.prim_collection_properties,
                "m_bAllowKinematicKinematicContactNotification",
            )
            layout.prop(coll.prim_collection_properties, "m_fMass")
            layout.prop(coll.prim_collection_properties, "m_fFriction")
            layout.prop(coll.prim_collection_properties, "m_fRestitution")
            layout.prop(coll.prim_collection_properties, "m_fLinearDampening")
            layout.prop(coll.prim_collection_properties, "m_fAngularDampening")
            layout.prop(coll.prim_collection_properties, "m_fSleepEnergyThreshold")
            layout.prop(coll.prim_collection_properties, "m_ePriority")
            layout.prop(coll.prim_collection_properties, "m_eCCD")
            layout.prop(coll.prim_collection_properties, "m_eCenterOfMass")


class PrimProperties(PropertyGroup):
    """ "Stored exposed variables relevant to the RenderPrimitive files"""

    lod: BoolVectorProperty(
        name="lod_mask",
        description="Set which LOD levels should be shown",
        default=(True, True, True, True, True, True, True, True),
        size=8,
        subtype="LAYER",
    )

    material_id: IntProperty(
        name="Material ID", description="Set the Material ID", default=0, min=0, max=255
    )

    prim_type: EnumProperty(
        name="Type",
        description="The type of the prim",
        items=[
            ("PrimType.Unknown", "Unknown", ""),
            ("PrimType.ObjectHeader", "Object Header", "The header of an Object"),
            ("PrimType.Mesh", "Mesh", ""),
            ("PrimType.Decal", "Decal", ""),
            ("PrimType.Sprites", "Sprite", ""),
            ("PrimType.Shape", "Shape", ""),
        ],
        default="PrimType.Mesh",
    )

    prim_subtype: EnumProperty(
        name="Sub-Type",
        description="The type of the prim",
        items=[
            ("PrimObjectSubtype.Standard", "Standard", ""),
            ("PrimObjectSubtype.Linked", "Linked", ""),
            ("PrimObjectSubtype.Weighted", "Weighted", ""),
        ],
        default="PrimObjectSubtype.Standard",
    )

    axis_lock: BoolVectorProperty(
        name="", description="Locks an axis", size=3, subtype="LAYER"
    )

    no_physics: BoolProperty(
        name="No physics",
    )

    # properties found in PrimSubMesh

    variant_id: IntProperty(
        name="Variant ID", description="Set the Variant ID", default=0, min=0, max=255
    )

    z_bias: IntProperty(
        name="Z Bias", description="Set the Z Bias", default=0, min=0, max=255
    )

    z_offset: IntProperty(
        name="Z Offset", description="Set the Z Offset", default=0, min=0, max=255
    )

    use_mesh_color: BoolProperty(name="Use Mesh Color")

    mesh_color: FloatVectorProperty(
        name="Mesh Color",
        description="Applies a global color to the mesh. Will replace all vertex colors!",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
    )


class GLACIER_PT_PrimPropertiesPanel(bpy.types.Panel):
    """ "Adds a panel to the object window to show the Prim_Properties"""

    bl_idname = "GLACIER_PT_PrimPropertiesPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_category = "Glacier"
    bl_label = "Prim Properties"

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        obj = context.object
        if obj.type != "MESH":
            return

        mesh = obj.data

        layout = self.layout

        layout.label(text="Lod mask:")
        row = layout.row(align=True)
        for i, name in enumerate(
            ["high", "   ", "   ", "   ", "   ", "   ", "   ", "low"]
        ):
            row.prop(mesh.prim_properties, "lod", index=i, text=name, toggle=True)

        layout.label(text="Lock Axis:")
        row = layout.row(align=True)
        for i, name in enumerate(["X", "Y", "Z"]):
            row.prop(mesh.prim_properties, "axis_lock", index=i, text=name, toggle=True)

        layout.use_property_split = True
        layout.row(align=True).label(text="")

        row = layout.row(align=True)
        row.prop(mesh.prim_properties, "material_id")

        row = layout.row(align=True)
        row.prop(mesh.prim_properties, "no_physics")

        row = layout.row(align=True)
        row.prop(mesh.prim_properties, "prim_type")
        row.enabled = False

        row = layout.row()
        row.prop(mesh.prim_properties, "prim_subtype")
        row.enabled = False

        # properties for PrimSubMesh
        row = layout.row()
        row.prop(mesh.prim_properties, "variant_id")

        row = layout.row()
        row.prop(mesh.prim_properties, "z_bias")

        row = layout.row()
        row.prop(mesh.prim_properties, "z_offset")

        row = layout.row()
        row.prop(mesh.prim_properties, "use_mesh_color")

        row = layout.row()
        row.prop(mesh.prim_properties, "mesh_color")
        row.enabled = mesh.prim_properties.use_mesh_color

        # TODO: add mesh buttons here
        # This will act as a temporary way to edit cloth. at least until a in-blender editor is made.
        # Button to export cloth data to json
        # Button to import cloth data from json

        # TODO: add trigger collision stuff
        # A mesh picker to select the collision mesh
        # A button to generate a new collision mesh


class PrimPhysicsProperties(PropertyGroup):
    """ "Stored exposed variables relevant to the RenderPrimitive Physics Properties"""

    collision_layer_items = [
        (str(layer.value), layer.name, "")
        for layer in aloc_format.PhysicsCollisionLayerType
    ]

    collision_layer_type: EnumProperty(
        name="Collision Layer Type",
        description="Collision Layer Types",
        items=collision_layer_items,
    )


class PrimPhysicsGenerateBoxCollider(Operator):
    bl_label = "Add Box Collider"
    bl_idname = "add_collider.box"

    def execute(self, context):
        current_obj = bpy.context.selected_objects[0]
        parent = current_obj
        bpy.ops.mesh.primitive_cube_add(size=1)
        cube = bpy.context.selected_objects[0]
        cube.name = "BoxCollider"
        cube.parent = parent
        cube.display_type = "WIRE"
        collection = current_obj.users_collection[0]
        collection.objects.link(cube)
        bpy.context.collection.objects.unlink(cube)
        return {"FINISHED"}


class PrimPhysicsGenerateCapsuleCollider(Operator):
    bl_label = "Add Capsule Collider"
    bl_idname = "add_collider.capsule"

    def execute(self, context):
        current_obj = bpy.context.selected_objects[0]
        parent = current_obj
        bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1)
        cylinder = bpy.context.selected_objects[0]
        cylinder.name = "CapsuleCollider"
        cylinder.parent = parent
        cylinder.display_type = "WIRE"
        collection = current_obj.users_collection[0]
        collection.objects.link(cylinder)
        bpy.context.collection.objects.unlink(cylinder)
        return {"FINISHED"}


class PrimPhysicsGenerateSphereCollider(Operator):
    bl_label = "Add Sphere Collider"
    bl_idname = "add_collider.sphere"

    def execute(self, context):
        current_obj = bpy.context.selected_objects[0]
        parent = current_obj
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5)
        sphere = bpy.context.selected_objects[0]
        sphere.name = "SphereCollider"
        sphere.parent = parent
        sphere.display_type = "WIRE"
        collection = current_obj.users_collection[0]
        collection.objects.link(sphere)
        bpy.context.collection.objects.unlink(sphere)

        return {"FINISHED"}


class PrimPhysicsGenerateConvexMeshCollider(Operator):
    bl_label = "Add Convex Mesh Collider"
    bl_idname = "add_collider.convex_mesh"

    def execute(self, context):
        current_obj = bpy.context.selected_objects[0]
        parent = current_obj
        convex_mesh_obj = current_obj.copy()
        convex_mesh_obj.data = current_obj.data.copy()
        collection = current_obj.users_collection[0]
        collection.objects.link(convex_mesh_obj)
        convex_mesh_obj.name = "ConvexMeshCollider"
        convex_mesh_obj.matrix_local = mathutils.Matrix()
        convex_mesh_obj.parent = parent
        convex_mesh_obj.display_type = "WIRE"
        return {"FINISHED"}


class PrimPhysicsGenerateTriangleMeshCollider(Operator):
    bl_label = "Add Triangle Mesh Collider"
    bl_idname = "add_collider.triangle_mesh"

    def execute(self, context):
        current_obj = bpy.context.selected_objects[0]
        parent = current_obj
        triangle_mesh_obj = current_obj.copy()
        triangle_mesh_obj.data = current_obj.data.copy()
        collection = current_obj.users_collection[0]
        collection.objects.link(triangle_mesh_obj)
        triangle_mesh_obj.name = "TriangleMeshCollider"
        triangle_mesh_obj.matrix_local = mathutils.Matrix()
        triangle_mesh_obj.parent = parent
        triangle_mesh_obj.display_type = "WIRE"
        return {"FINISHED"}


class GLACIER_PT_PhysicsPropertiesPanel(bpy.types.Panel):
    """ "Adds a panel to the object window to show the Physics_Properties"""

    bl_idname = "GLACIER_PT_PhysicsPropertiesPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "physics"
    bl_category = "Glacier"
    bl_label = "Physics Properties"

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        if len(context.selected_objects) == 1:
            obj = context.object
            if obj.type != "MESH":
                return

            mesh = obj.data

            layout = self.layout

            if (
                not obj.name.startswith("BoxCollider")
                and not obj.name.startswith("CapsuleCollider")
                and not obj.name.startswith("SphereCollider")
                and not obj.name.startswith("ConvexMeshCollider")
                and not obj.name.startswith("TriangleMeshCollider")
            ):
                layout.operator("add_collider.box")
                layout.operator("add_collider.capsule")
                layout.operator("add_collider.sphere")
                layout.operator("add_collider.convex_mesh")
                layout.operator("add_collider.triangle_mesh")

            else:
                row = layout.row()
                row.prop(mesh.prim_physics_properties, "collision_layer_type")


class MaterialFloatValue(PropertyGroup):
    name: StringProperty()
    friendly_name: StringProperty()
    value: FloatProperty()


class MaterialColorValue(PropertyGroup):
    name: StringProperty()
    friendly_name: StringProperty()
    value: FloatVectorProperty(subtype="COLOR", min=0, max=1)


class MaterialInstanceFlags(PropertyGroup):
    name: StringProperty()
    value: BoolProperty()


class MaterialClassFlags(PropertyGroup):
    name: StringProperty()
    value: BoolProperty()


class PrimMaterialProperties(PropertyGroup):
    def update_material(self, context):
        material_name = self.prim_materials
        float_values = materials.get_float_values(material_name)
        color_values = materials.get_color_values(material_name)
        instance_flags = materials.get_instance_flags(material_name)
        class_flags = materials.get_class_flags(material_name)

        print(instance_flags)

        self.material_float_values.clear()
        self.material_color_values.clear()
        self.material_instance_flags.clear()
        self.material_class_flags.clear()

        for fv in float_values:
            item = self.material_float_values.add()
            item.name = fv["Name"]
            item.friendly_name = fv["FriendlyName"]
            item.value = fv["Value"]

        for cv in color_values:
            item = self.material_color_values.add()
            item.name = cv["Name"]
            item.friendly_name = cv["FriendlyName"]
            item.value = cv["Value"]

        for flag, value in instance_flags.items():
            item = self.material_instance_flags.add()
            item.name = flag
            item.value = value

        for flag, value in class_flags.items():
            item = self.material_class_flags.add()
            item.name = flag
            item.value = value

    prim_materials: EnumProperty(
        name="Materialclass",
        description="PRIM Materials",
        default="basicmaterial",
        items=materials.get_materials(),
        update=lambda self, context: self.update_material(context),
    )

    material_float_values: CollectionProperty(
        name="Material Float Values",
        type=MaterialFloatValue,
    )

    material_color_values: CollectionProperty(
        name="Material Color Values",
        type=MaterialColorValue,
    )

    material_eres_value: StringProperty(
        name="EntityResource",
        description="EntityResource for the material (Used for bullet impact effects)",
        default="[assembly:/_pro/effects/templates/materialdescriptors/fx_md_env_stone_concrete.template?/fx_md_env_stone_concrete.entitytemplate].pc_entityresource",
    )

    material_instance_flags: CollectionProperty(
        name="Material Instance Flags",
        type=MaterialInstanceFlags,
    )

    material_class_flags: CollectionProperty(
        name="Material Class Flags",
        type=MaterialClassFlags,
    )


class GLACIER_OT_UpdateMaterial(bpy.types.Operator):
    bl_idname = "material.update_material"
    bl_label = "Show/Reset Material Properties"
    bl_description = "Update material properties"

    def execute(self, context):
        material = context.material
        properties = material.prim_material_properties
        properties.update_material(context)
        return {"FINISHED"}


class GLACIER_OT_CopyMaterialProperties(bpy.types.Operator):
    bl_idname = "material.copy_properties"
    bl_label = "Copy Material Properties"
    bl_description = "Copy material properties to selected objects"

    @classmethod
    def poll(cls, context):
        return context.material and context.active_object and context.selected_objects

    def execute(self, context):
        active_object = context.active_object
        selected_objects = [
            obj for obj in context.selected_objects if obj != active_object
        ]

        active_material = (
            active_object.material_slots[0].material
            if active_object.material_slots
            else None
        )
        if not active_material:
            self.report({"WARNING"}, "Active object has no material")
            return {"CANCELLED"}

        active_properties = active_material.prim_material_properties

        for obj in selected_objects:
            material = obj.material_slots[0].material if obj.material_slots else None
            if material:
                if material == active_material:
                    continue

                properties = material.prim_material_properties
                properties.prim_materials = active_properties.prim_materials
                properties.material_eres_value = active_properties.material_eres_value
                properties.material_float_values.clear()
                properties.material_color_values.clear()
                properties.material_instance_flags.clear()
                properties.material_class_flags.clear()

                for item in active_properties.material_float_values:
                    new_item = properties.material_float_values.add()
                    new_item.name = item.name
                    new_item.friendly_name = item.friendly_name
                    new_item.value = item.value

                for item in active_properties.material_color_values:
                    new_item = properties.material_color_values.add()
                    new_item.name = item.name
                    new_item.friendly_name = item.friendly_name
                    new_item.value = item.value

                for item in active_properties.material_instance_flags:
                    new_item = properties.material_instance_flags.add()
                    new_item.name = item.name
                    new_item.value = item.value

                for item in active_properties.material_class_flags:
                    new_item = properties.material_class_flags.add()
                    new_item.name = item.name
                    new_item.value = item.value

            else:
                self.report({"WARNING"}, f"Object {obj.name} has no material")

        return {"FINISHED"}


class GLACIER_PT_PrimMaterialPropertiesPanel(bpy.types.Panel):
    bl_idname = "GLACIER_PT_PrimMaterialPropertiesPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_category = "Glacier"
    bl_label = "Prim Material Properties"

    @classmethod
    def poll(self, context):
        return context.material is not None

    def draw(self, context):
        layout = self.layout
        material = context.material
        properties = material.prim_material_properties

        # Create a row for the materials dropdown and refresh button
        row = layout.row(align=True)
        row.prop(properties, "prim_materials")
        row.operator("material.update_material", icon="FILE_REFRESH", text="")

        layout.prop(properties, "material_eres_value")

        # Display the float values
        for item in properties.material_float_values:
            row = layout.row()
            row.prop(item, "value", text=item.friendly_name)

        # Display the color values
        for item in properties.material_color_values:
            row = layout.row()
            row.prop(item, "value", text=item.friendly_name)

        layout.operator(
            "material.copy_properties", text="Copy Properties to Selected Objects"
        )


class GLACIER_PT_PrimMaterialAdvancedPropertiesPanel(bpy.types.Panel):
    bl_idname = "GLACIER_PT_PrimMaterialAdvancedPropertiesPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_category = "Glacier"
    bl_parent_id = "GLACIER_PT_PrimMaterialPropertiesPanel"
    bl_label = "Advanced Properties"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        pass


class GLACIER_PT_PrimMaterialInstanceFlagsPanel(bpy.types.Panel):
    bl_idname = "GLACIER_PT_PrimMaterialInstanceFlagsPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_category = "Glacier"
    bl_parent_id = "GLACIER_PT_PrimMaterialAdvancedPropertiesPanel"
    bl_label = "Material Instance Flags"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = True

        material = context.material
        properties = material.prim_material_properties

        for item in properties.material_instance_flags:
            row = layout.row()
            row.prop(item, "value", text=item.name)


class GLACIER_PT_PrimMaterialClassFlagsPanel(bpy.types.Panel):
    bl_idname = "GLACIER_PT_PrimMaterialClassFlagsPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_category = "Glacier"
    bl_parent_id = "GLACIER_PT_PrimMaterialAdvancedPropertiesPanel"
    bl_label = "Material Class Flags"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = True

        material = context.material
        properties = material.prim_material_properties

        for item in properties.material_class_flags:
            row = layout.row()
            row.prop(item, "value", text=item.name)


classes = [
    PrimProperties,
    PrimCollectionProperties,
    GLACIER_PT_PrimPropertiesPanel,
    GLACIER_PT_PrimCollectionPropertiesPanel,
    MaterialFloatValue,
    MaterialColorValue,
    MaterialInstanceFlags,
    MaterialClassFlags,
    PrimMaterialProperties,
    GLACIER_OT_UpdateMaterial,
    GLACIER_OT_CopyMaterialProperties,
    GLACIER_PT_PrimMaterialPropertiesPanel,
    GLACIER_PT_PrimMaterialAdvancedPropertiesPanel,
    GLACIER_PT_PrimMaterialInstanceFlagsPanel,
    GLACIER_PT_PrimMaterialClassFlagsPanel,
    PrimPhysicsProperties,
    PrimPhysicsGenerateBoxCollider,
    PrimPhysicsGenerateCapsuleCollider,
    PrimPhysicsGenerateSphereCollider,
    PrimPhysicsGenerateConvexMeshCollider,
    PrimPhysicsGenerateTriangleMeshCollider,
    GLACIER_PT_PhysicsPropertiesPanel,
    ImportPRIM,
    ExportPRIM,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.Mesh.prim_properties = PointerProperty(type=PrimProperties)
    bpy.types.Collection.prim_collection_properties = PointerProperty(
        type=PrimCollectionProperties
    )
    bpy.types.Mesh.prim_physics_properties = PointerProperty(type=PrimPhysicsProperties)
    bpy.types.Material.prim_material_properties = PointerProperty(
        type=PrimMaterialProperties
    )


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    del bpy.types.Mesh.prim_properties
    del bpy.types.Collection.prim_collection_properties
    del bpy.types.Mesh.prim_physics_properties
    del bpy.types.Material.prim_material_properties


def menu_func_import(self, context):
    self.layout.operator(ImportPRIM.bl_idname, text="Glacier RenderPrimitve (.prim)")


def menu_func_export(self, context):
    exportprim_instance = self.layout.operator(
        ExportPRIM.bl_idname, text="Glacier RenderPrimitve (.prim)"
    )
    exportprim_instance.export_scene = False
    exportprim_instance2 = self.layout.operator(
        ExportPRIM.bl_idname,
        text="Glacier RenderPrimitve (prims, materials, textures, geomentities and collision)",
    )
    exportprim_instance2.export_scene = True


if __name__ == "__main__":
    register()
