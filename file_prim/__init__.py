#import bpy
#
#from bpy_extras.io_utils import (
#        ImportHelper,
#        ExportHelper
#        )
#
#from bpy.props import (
#        StringProperty
#        )
#
#class ImportPRIM(bpy.types.Operator, ImportHelper):
#    """Load a PRIM file"""
#    bl_idname = "import_mesh.prim"
#    bl_label = "Import PRIM Mesh"
#    filename_ext = ".prim"
#    filter_glob = StringProperty(
#        default="*.prim",
#        options={'HIDDEN'},
#    )
#
#    filepath: StringProperty(
#        name="PRIM",
#        description="Set path for the PRIM file",
#        subtype="FILE_PATH"
#    )
#
#    def execute(self, context):
#        from . import import_prim
#        keywords = self.as_keywords(ignore=(
#            'filter_glob',
#        ))
#        meshes = import_prim.load_prim(self, context, **keywords)
#        if not meshes:
#            return {'CANCELLED'}
#
#        scene = bpy.context.scene
#        for mesh in meshes:
#            obj = bpy.data.objects.new(mesh.name, mesh)
#            scene.collection.objects.link(obj)
#        layer = bpy.context.view_layer
#        layer.update()
#        return {'FINISHED'}
#
#class ExportPRIM(bpy.types.Operator, ExportHelper):
#    """Export to a PRIM file"""
#    bl_idname = 'export_mesh.prim'
#    bl_label = 'Export PRIM Mesh'
#    check_extension = True
#    filename_ext = '.prim'
#    filter_glob: StringProperty(default='*.prim', options={'HIDDEN'})
#
#    def execute(self, context):
#        from . import export_prim
#        keywords = self.as_keywords(ignore=(
#            'check_existing',
#            'filter_glob',
#        ))
#        return export_prim.save_prim(self, context, **keywords)
#
#classes = [
#    ImportPRIM,
#    ExportPRIM
#]
#
#def register():
#    for c in classes:
#        bpy.utils.register_class(c)
#    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
#    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
#
#
#def unregister():
#    for c in reversed(classes):
#        bpy.utils.unregister_class(c)
#    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
#    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
#
#def menu_func_import(self, context):
#    self.layout.operator(ImportPRIM.bl_idname, text="Hitman RenderPrimitve (.prim)")
#def menu_func_export(self, context):
#    self.layout.operator(ExportPRIM.bl_idname, text="Hitman RenderPrimitve (.prim)")
#
#if __name__ == '__main__':
#    register()
