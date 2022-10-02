import bpy

from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper
)

from bpy.props import (
    StringProperty
)


class ImportVTXD(bpy.types.Operator, ImportHelper):
    """Load a VTXD file"""
    bl_idname = "import_mesh.vtxd"
    bl_label = "Import VTXD Mesh"
    filename_ext = ".vtxd"
    filter_glob = StringProperty(
        default="*.vtxd",
        options={'HIDDEN'},
    )

    filepath: StringProperty(
        name="VTXD",
        description="Set path for the VTXD file",
        subtype="FILE_PATH"
    )

    def execute(self, context):
        from . import bl_import
        keywords = self.as_keywords(ignore=(
            'filter_glob',
        ))

        meshes = bl_import.load_vtxd(self, context, **keywords)

        if not meshes:
            return {'CANCELLED'}

        scene = bpy.context.scene
        for mesh in meshes:
            obj = bpy.data.objects.new(mesh.name, mesh)
            scene.collection.objects.link(obj)
        layer = bpy.context.view_layer
        layer.update()
        return {'FINISHED'}


class ExportVTXD(bpy.types.Operator, ExportHelper):
    """Export to a VTXD file"""
    bl_idname = 'export_mesh.vtxd'
    bl_label = 'Export VTXD Mesh'
    check_extension = True
    filename_ext = '.vtxd'
    filter_glob: StringProperty(default='*.vtxd', options={'HIDDEN'})

    def execute(self, context):
        from . import bl_export
        keywords = self.as_keywords(ignore=(
            'check_existing',
            'filter_glob',
        ))
        return bl_export.save_vtxd(self, context, **keywords)


classes = [
    ImportVTXD,
    ExportVTXD
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


def menu_func_import(self, context):
    self.layout.operator(ImportVTXD.bl_idname, text="Glacier VertexData (.vtxd)")


def menu_func_export(self, context):
    self.layout.operator(ExportVTXD.bl_idname, text="Glacier VertexData (.vtxd)")


if __name__ == '__main__':
    register()
