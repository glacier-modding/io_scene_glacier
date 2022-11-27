import bpy
import os

from . import bl_utils_prim
from .. import BlenderUI

from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper
)

from bpy.props import (StringProperty,
                       BoolProperty,
                       BoolVectorProperty,
                       CollectionProperty,
                       PointerProperty,
                       IntProperty,
                       EnumProperty,
                       FloatVectorProperty,
                       IntVectorProperty
                       )

from bpy.types import (Panel,
                       Operator,
                       PropertyGroup,
                       )


class ImportPRIM(bpy.types.Operator, ImportHelper):
    """Load a PRIM file"""
    bl_idname = "import_mesh.prim"
    bl_label = "Import PRIM Mesh"
    filename_ext = ".prim"

    filter_glob: StringProperty(
        default="*.prim",
        options={'HIDDEN'},
    )

    files: CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    use_rig: BoolProperty(
        name="Use BoneRig",
        description="Use a BORG file on the chosen prim file"
    )

    rig_filepath: StringProperty(
        name="BoneRig Path",
        description="Path to the BoneRig (BORG) file",
    )

    use_aloc: BoolProperty(
        name="Use Collision",
        description="Use a ALOC file on the chosen prim file"
    )

    aloc_filepath: StringProperty(
        name="Collision Path",
        description="Path to the Collision (ALOC) file",
    )

    def draw(self, context):

        if ".prim" not in self.filepath.lower():
            return

        layout = self.layout
        layout.label(text="import options:")

        is_weighted_prim = bl_utils_prim.is_weighted(self.filepath)
        if not is_weighted_prim:
            layout.label(text="The selected prim does not support a rig", icon="ERROR")
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
                    f = open(os.fsencode(self.rig_filepath.replace(os.sep, '/')), "rb")
                except IOError:
                    layout.label(text="Given filepath not valid", icon="ERROR")
                finally:
                    if f:
                        f.close()

        layout.row(align=True)

    def execute(self, context):
        from . import bl_import_prim

        prim_paths = ["%s\\%s" % (os.path.dirname(self.filepath), meshPaths.name) for meshPaths in self.files]
        for prim_path in prim_paths:

            collection = bpy.data.collections.new(bpy.path.display_name_from_filepath(prim_path))

            self.rig_filepath = self.rig_filepath.replace(os.sep, '/')

            arma_obj = None
            if self.use_rig:
                from ..file_borg import bl_import_borg
                armature = bl_import_borg.load_borg(self, context, self.rig_filepath)
                arma_obj = bpy.data.objects.new(armature.name, armature)
                collection.objects.link(arma_obj)

            meshes = bl_import_prim.load_prim(self, context, collection, prim_path, self.use_rig, self.rig_filepath)

            if not meshes:
                BlenderUI.MessageBox("Failed to import \"%s\"" % prim_path, "Importing error", 'ERROR')
                return {'CANCELLED'}

            for mesh in meshes:
                obj = bpy.data.objects.new(mesh.name, mesh)
                if self.use_rig and arma_obj:
                    obj.modifiers.new(name='Glacier Bonerig', type='ARMATURE')
                    obj.modifiers['Glacier Bonerig'].object = arma_obj

                obj.data.polygons.foreach_set('use_smooth', [True] * len(obj.data.polygons))

                collection.objects.link(obj)

            context.scene.collection.children.link(collection)
            layer = bpy.context.view_layer
            layer.update()

        return {'FINISHED'}


class ExportPRIM(bpy.types.Operator, ExportHelper):
    """Export to a PRIM file"""
    bl_idname = 'export_mesh.prim'
    bl_label = 'Export PRIM Mesh'
    check_extension = True
    filename_ext = '.prim'
    filter_glob: StringProperty(default='*.prim', options={'HIDDEN'})

    def get_collections(self, context):
        items = [(col.name, col.name, "") for col in bpy.data.collections]

        for i, coll_name in enumerate(items):
            if coll_name[0] == bpy.context.collection.name:
                items[0], items[i] = items[i], items[0]

        return items

    export_collection: EnumProperty(
        name='',
        description='The collection to turn into a prim',
        items=get_collections,
        default=None,
    )

    def draw(self, context):
        if ".prim" not in self.filepath.lower():
            return

        layout = self.layout
        layout.label(text="export options:")
        row = layout.row(align=True)
        row.prop(self, "export_collection")

    def execute(self, context):
        from . import bl_export_prim
        keywords = self.as_keywords(ignore=(
            'check_existing',
            'filter_glob',
            'export_collection'
        ))

        return bl_export_prim.save_prim(bpy.data.collections[self.export_collection], **keywords)


class PrimCollectionProperties(PropertyGroup):
    draw_destination: IntProperty(
        name="Draw Destination",
        description="",
        min=0,
        max=255,
        step=1,
    )

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
        name='Linked',
        description='The prim is linked',
    )

    is_weighted: BoolProperty(
        name='Weighted',
        description='The prim is weighted',
    )


class GLACIER_PT_PrimCollectionPropertiesPanel(bpy.types.Panel):
    bl_idname = 'GLACIER_PT_PrimCollectionPropertiesPanel'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'collection'
    bl_category = 'Glacier'
    bl_label = 'Global Prim Properties'

    @classmethod
    def poll(self, context):
        return context.collection is not None

    def draw(self, context):
        coll = context.collection
        layout = self.layout

        layout.row(align=True).prop(coll.prim_collection_properties, "draw_destination")
        layout.row(align=True).prop(coll.prim_collection_properties, "bone_rig_resource_index")

        layout.label(text="Flags:")

        row = layout.row(align=True)
        row.prop(coll.prim_collection_properties, "has_bones")
        row.prop(coll.prim_collection_properties, "has_frames")
        row.enabled = False

        row = layout.row(align=True)
        row.prop(coll.prim_collection_properties, "is_linked")
        row.prop(coll.prim_collection_properties, "is_weighted")
        row.enabled = False


class PrimProperties(PropertyGroup):
    """"Stored exposed variables relevant to the RenderPrimitive files"""
    draw_destination: IntProperty(
        name="Draw Destination",
        description="",
        min=0,
        max=255,
        step=1,
    )

    lod: BoolVectorProperty(
        name='lod_mask',
        description='Set which LOD levels should be shown',
        default=(True, True, True, True, True, True, True, True),
        size=8,
        subtype='LAYER'
    )

    material_id: IntProperty(
        name='Material ID',
        description='Set the Material ID',
        default=0,
        min=0,
        max=255
    )

    prim_type: EnumProperty(
        name='Type',
        description='The type of the prim',
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
        name='Sub-Type',
        description='The type of the prim',
        items=[
            ("PrimObjectSubtype.Standard", "Standard", ""),
            ("PrimObjectSubtype.Linked", "Linked", ""),
            ("PrimObjectSubtype.Weighted", "Weighted", ""),
        ],
        default="PrimObjectSubtype.Standard",
    )

    axis_lock: BoolVectorProperty(
        name='',
        description='Locks an axis',
        size=3,
        subtype='LAYER'
    )

    no_physics: BoolProperty(
        name="No physics",
    )

    # properties found in PrimSubMesh

    variant_id: IntProperty(
        name='Variant ID',
        description='Set the Variant ID',
        default=0,
        min=0,
        max=255
    )

    z_bias: IntProperty(
        name='Z Bias',
        description='Set the Z Bias',
        default=0,
        min=0,
        max=255
    )

    z_offset: IntProperty(
        name='Z Offset',
        description='Set the Z Offset',
        default=0,
        min=0,
        max=255
    )

    use_mesh_color: BoolProperty(
        name="Use Mesh Color"
    )

    mesh_color: FloatVectorProperty(
        name="Mesh Color",
        description="Applies a global color to the mesh. Will replace all vertex colors!",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0)
    )


class GLACIER_PT_PrimPropertiesPanel(bpy.types.Panel):
    """"Adds a panel to the object window to show the Prim_Properties"""

    bl_idname = 'GLACIER_PT_PrimPropertiesPanel'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_category = 'Glacier'
    bl_label = 'Prim Properties'

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        obj = context.object
        if obj.type != 'MESH':
            return

        mesh = obj.data

        layout = self.layout

        layout.label(text="Lod mask:")
        row = layout.row(align=True)
        for i, name in enumerate(["high", "   ", "   ", "   ", "   ", "   ", "   ", "low"]):
            row.prop(mesh.prim_properties, "lod", index=i, text=name, toggle=True)

        layout.label(text="Lock Axis:")
        row = layout.row(align=True)
        for i, name in enumerate(["X", "Y", "Z"]):
            row.prop(mesh.prim_properties, "axis_lock", index=i, text=name, toggle=True)

        layout.label(text="")
        layout.use_property_split = True
        layout.row(align=True).prop(mesh.prim_properties, "draw_destination")

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


classes = [
    PrimProperties,
    PrimCollectionProperties,
    GLACIER_PT_PrimPropertiesPanel,
    GLACIER_PT_PrimCollectionPropertiesPanel,
    ImportPRIM,
    ExportPRIM
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.Mesh.prim_properties = PointerProperty(type=PrimProperties)
    bpy.types.Collection.prim_collection_properties = PointerProperty(type=PrimCollectionProperties)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    del bpy.types.Mesh.prim_properties
    del bpy.types.Collection.prim_collection_properties


def menu_func_import(self, context):
    self.layout.operator(ImportPRIM.bl_idname, text="Glacier RenderPrimitve (.prim)")


def menu_func_export(self, context):
    self.layout.operator(ExportPRIM.bl_idname, text="Glacier RenderPrimitve (.prim)")


if __name__ == '__main__':
    register()
