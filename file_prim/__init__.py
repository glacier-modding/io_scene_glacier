import bpy

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
    filter_glob = StringProperty(
        default="*.prim",
        options={'HIDDEN'},
    )

    filepath: StringProperty(
        name="PRIM",
        description="Set path for the PRIM file",
        subtype="FILE_PATH"
    )

    rig_filepath: StringProperty(
        name="BORG",
        description="Set path for the BORG file",
        subtype="FILE_PATH"
    )

    ignore_rig: BoolProperty(
        name='ignore BoneRig',
        description='ignore the referenced BoneRig file',
        default=True
    )

    def execute(self, context):
        from . import import_prim
        from ..file_borg import format as borg
        keywords = self.as_keywords(ignore=(
            'filter_glob',
            'rig_filepath',
            'ignore_rig'
        ))

        if not self.ignore_rig:
            rig = borg.BoneRig()

        meshes = import_prim.load_prim(self, context, **keywords)
        if not meshes:
            return {'CANCELLED'}

        scene = bpy.context.scene
        for mesh in meshes:
            obj = bpy.data.objects.new(mesh.name, mesh)
            scene.collection.objects.link(obj)
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

    def execute(self, context):
        from . import export_prim
        keywords = self.as_keywords(ignore=(
            'check_existing',
            'filter_glob',
        ))
        return export_prim.save_prim(self, context, **keywords)


class Prim_Properties(PropertyGroup):
    lod: BoolVectorProperty(
        name='show_lod',
        description='Set which LOD levels should be shown',
        default=(True, True, True, True, True, True, True, True),
        size=8,
        subtype='LAYER',
        # update=show_lod_update,
        # get=None,
        # set=None
    )


class Prim_Properties_Panel(bpy.types.Panel):
    bl_idname = 'Prim_Properties_Panel'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'
    bl_category = 'Glacier'
    bl_label = 'Prim Properties'

    def draw(self, context):
        obj = bpy.context.view_layer.objects.active
        if obj.type != 'MESH':
            return

        mesh = obj.to_mesh()

        layout = self.layout
        layout.label(text="show LOD:")

        row = layout.row(align=True)
        for i, name in enumerate(["high", "   ", "   ", "   ", "   ", "   ", "   ", "low"]):
            row.prop(mesh.prim_properties, "lod", index=i, text=name, toggle=True)


classes = [
    ImportPRIM,
    ExportPRIM,
    Prim_Properties,
    Prim_Properties_Panel
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
    self.layout.operator(ImportPRIM.bl_idname, text="Hitman RenderPrimitve (.prim)")


def menu_func_export(self, context):
    self.layout.operator(ExportPRIM.bl_idname, text="Hitman RenderPrimitve (.prim)")


if __name__ == '__main__':
    register()
