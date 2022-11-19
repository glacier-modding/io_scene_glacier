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

        if not ".prim" in self.filepath.lower():
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
                    if f: f.close()

        layout.row(align=True)

        # row.prop(self, "use_aloc")
        # row = layout.row(align=True)
        # row.enabled = self.use_aloc is not False
        # row.prop(self, "aloc_filepath")

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

        meshes = bl_import_prim.load_prim(self, context, self.filepath, self.use_rig, self.rig_filepath)

        if not meshes:
            return {'CANCELLED'}

        for mesh in meshes:
            obj = bpy.data.objects.new(mesh.name, mesh)
            if self.use_rig and arma_obj:
                obj.modifiers.new(name='Glacier Bonerig', type='ARMATURE')
                obj.modifiers['Glacier Bonerig'].object = arma_obj
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

        if not ".prim" in self.filepath.lower():
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


class Prim_Properties(PropertyGroup):
    lod: BoolVectorProperty(
        name='lod_mask',
        description='Set which LOD levels should be shown',
        default=(True, True, True, True, True, True, True, True),
        size=8,
        subtype='LAYER'
    )


class GLACIER_PT_PrimPropertiesPanel(bpy.types.Panel):
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


classes = [
    Prim_Properties,
    GLACIER_PT_PrimPropertiesPanel,
    ImportPRIM,
    ExportPRIM
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.Mesh.prim_properties = PointerProperty(type=Prim_Properties)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    del bpy.types.Mesh.prim_properties


def menu_func_import(self, context):
    self.layout.operator(ImportPRIM.bl_idname, text="Glacier RenderPrimitve (.prim)")


def menu_func_export(self, context):
    self.layout.operator(ExportPRIM.bl_idname, text="Glacier RenderPrimitve (.prim)")


if __name__ == '__main__':
    register()
