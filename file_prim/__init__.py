import bpy
import os

from . import bl_utils_prim

from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper
)

from bpy.props import (StringProperty,
                       BoolProperty,
                       BoolVectorProperty,
                       PointerProperty,
                       IntProperty,
                       EnumProperty
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

    filepath: StringProperty(
        name="PRIM",
        description="Set path for the PRIM file",
        subtype="FILE_PATH"
    )

    use_rig: BoolProperty(
        name="Use BoneRig",
        description="Use a BORG file on the chosen prim file"
    )

    rig_filepath: StringProperty(
        name="BoneRig Path"
    )

    use_aloc: BoolProperty(
        name="Use Collision",
        description="Use a ALOC file on the chosen prim file"
    )

    aloc_filepath: StringProperty(
        name="Collision Path"
    )

    def draw(self, context):

        if ".prim" not in self.filepath.lower():
            return

        layout = self.layout
        layout.label(text="import options:")

        is_weighted_prim = bl_utils_prim.is_weighted(self.filepath)
        if not is_weighted_prim:
            layout.label(text="The selected prim does not support a rig", icon="ERROR")
        else:
            row = layout.row(align=True)
            row.prop(self, "use_rig")
            row = layout.row(align=True)
            row.enabled = self.use_rig is not False
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

        collection = bpy.data.collections.new(bpy.path.display_name_from_filepath(self.filepath))

        self.rig_filepath = self.rig_filepath.replace(os.sep, '/')

        arma_obj = None
        if self.use_rig:
            from ..file_borg import bl_import_borg
            armature = bl_import_borg.load_borg(self, context, self.rig_filepath)
            arma_obj = bpy.data.objects.new(armature.name, armature)
            collection.objects.link(arma_obj)

        meshes = bl_import_prim.load_prim(self, context, collection, self.filepath, self.use_rig, self.rig_filepath)

        if not meshes:
            return {'CANCELLED'}

        for mesh in meshes:
            obj = bpy.data.objects.new(mesh.name, mesh)
            if self.use_rig and arma_obj:
                obj.modifiers.new(name='Glacier Bonerig', type='ARMATURE')
                obj.modifiers['Glacier Bonerig'].object = arma_obj

            obj.data.polygons.foreach_set('use_smooth',  [True] * len(obj.data.polygons))

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

    def draw(self, context):
        if ".prim" not in self.filepath.lower():
            return

        layout = self.layout
        layout.label(text="export options:")

    def execute(self, context):
        from . import bl_export_prim
        keywords = self.as_keywords(ignore=(
            'check_existing',
            'filter_glob'
        ))
        return bl_export_prim.save_prim(self, context, **keywords)


class Prim_Collection_Properties(PropertyGroup):
    is_weighted: BoolProperty(
        name='Weighted',
        description='The prim is weigthed',
    )

    is_linked: BoolProperty(
        name='Linked',
        description='The prim is linked',
    )

class GLACIER_PT_PrimCollectionPropertiesPanel(bpy.types.Panel):
    bl_idname = 'GLACIER_PT_PrimCollectionPropertiesPanel'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'collection'
    bl_category = 'Glacier'
    bl_label = 'Prim Properties'

    @classmethod
    def poll(self, context):
        return context.collection is not None

    def draw(self, context):
        coll = context.collection
        layout = self.layout

        layout.label(text="Flags:")
        row = layout.row(align=True)
        row.prop(coll.prim_collection_properties, "is_weighted")
        row.prop(coll.prim_collection_properties, "is_linked")
        row.enabled = False



class PrimProperties(PropertyGroup):
    """"Stored exposed variables relevant to the RenderPrimitive files"""

    lod: BoolVectorProperty(
        name='lod_mask',
        description='Set which LOD levels should be shown',
        default=(True, True, True, True, True, True, True, True),
        size=8,
        subtype='LAYER'
    )

    material_id: IntProperty(
        name='',
        description='Set the Material ID',
        default=0,
        min=0,
        max=255
    )

    prim_type: EnumProperty(
        name='',
        description='The type of the prim',
        items=[
            ("PrimType.Unknown", "Unknown", "lmao idk"),
            ("PrimType.ObjectHeader", "Object Header", "The header of an Object"),
            ("PrimType.Mesh", "Mesh", ""),
            ("PrimType.Decal", "Decal", ""),
            ("PrimType.Sprites", "Sprite", ""),
            ("PrimType.Shape", "Shape", ""),
        ],
        default="PrimType.Mesh",
    )

    prim_subtype: EnumProperty(
        name='',
        description='The type of the prim',
        items=[
            ("PrimObjectSubtype.Standard", "Standard", "pretty normal"),
            ("PrimObjectSubtype.Linked", "Linked", ""),
            ("PrimObjectSubtype.Weighted", "Weighted", "watch out for the skeleton"),
        ],
        default="PrimObjectSubtype.Standard",
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

        layout.label(text="Material ID:")
        row = layout.row(align=True)
        row.prop(mesh.prim_properties, "material_id")

        layout.label(text="Type:")
        row = layout.row(align=True)
        row.prop(mesh.prim_properties, "prim_type")
        row.enabled = False

        layout.label(text="Sub-Type:")
        row = layout.row(align=True)
        row.prop(mesh.prim_properties, "prim_subtype")
        row.enabled = False


classes = [
    PrimProperties,
    Prim_Collection_Properties,
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
    bpy.types.Collection.prim_collection_properties = PointerProperty(type=Prim_Collection_Properties)


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
