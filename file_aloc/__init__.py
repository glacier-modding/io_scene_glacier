import bpy
import os
from bpy.utils import register_class
from bpy.utils import unregister_class
from . import bl_import_aloc

from .. import BlenderUI
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


class AlocProperties(PropertyGroup):
    """ "Stored exposed variables relevant to the Physics files"""

    collision_type: BoolVectorProperty(
        name="collision_type_mask",
        description="Set which Collision Types should be shown",
        default=(True, True, True, True, True, True),
        size=6,
        subtype="LAYER",
    )

    aloc_type: EnumProperty(
        name="Type",
        description="The type of the aloc",
        items=[
            ("PhysicsDataType.NONE", "None", ""),
            ("PhysicsDataType.CONVEX_MESH", "Convex Mesh", "The header of an Object"),
            ("PhysicsDataType.TRIANGLE_MESH", "Triangle Mesh", ""),
            ("PhysicsDataType.CONVEX_MESH_AND_TRIANGLE_MESH", "Convex Mesh and Triangle Mesh", ""),
            ("PhysicsDataType.PRIMITIVE", "Primitive", ""),
            ("PhysicsDataType.CONVEX_MESH_AND_PRIMITIVE", "Convex Mesh and Primitive", ""),
            ("PhysicsDataType.TRIANGLE_MESH_AND_PRIMITIVE", "Triangle Mesh and Primitive", ""),
            ("PhysicsDataType.KINEMATIC_LINKED", "Kinematic Linked", ""),
            ("PhysicsDataType.SHATTER_LINKED", "Shatter Linked", ""),
            ("PhysicsDataType.KINEMATIC_LINKED_2", "Kinematic Linked 2", ""),
        ],
        default="PhysicsDataType.NONE",
    )

    aloc_subtype: EnumProperty(
        name="Sub-Type",
        description="The subtype of the aloc",
        items=[
            ("PhysicsCollisionPrimitiveType.BOX", "Box", ""),
            ("PhysicsCollisionPrimitiveType.CAPSULE", "Capsule", ""),
            ("PhysicsCollisionPrimitiveType.SPHERE", "Sphere", ""),
            ("PhysicsCollisionPrimitiveType.NONE", "None", ""),
        ],
        default="PhysicsCollisionPrimitiveType.NONE",
    )


class GLACIER_PT_AlocPropertiesPanel(bpy.types.Panel):
    """ "Adds a panel to the object window to show the Aloc_Properties"""

    bl_idname = "GLACIER_PT_AlocPropertiesPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_category = "Glacier"
    bl_label = "Aloc Properties"

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        obj = context.object
        if obj.type != "MESH":
            return

        mesh = obj.data

        layout = self.layout

        layout.label(text="Collision Type mask:")
        row = layout.row(align=True)
        for i, name in enumerate(
            ["N", "S", "R", "SL", "KL", "BC"]
        ):
            row.prop(mesh.aloc_properties, "collision_type", index=i, text=name, toggle=True)

        row = layout.row(align=True)
        row.prop(mesh.aloc_properties, "aloc_type")
        row.enabled = False

        row = layout.row()
        row.prop(mesh.aloc_properties, "aloc_subtype")
        row.enabled = False


class ImportALOC(bpy.types.Operator, ImportHelper):
    """Load a collision .aloc file"""

    bl_idname = "import_collision.aloc"
    bl_label = "Import Collision ALOC"
    filename_ext = ".aloc"

    filter_glob: StringProperty(
        default="*.aloc",
        options={"HIDDEN"},
    )

    files: CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    def draw(self, context):
        if ".aloc" not in self.filepath.lower():
            return

        layout = self.layout

        layout.row(align=True)

    def execute(self, context):
        aloc_paths = [
            "%s\\%s" % (os.path.dirname(self.filepath), aloc_paths.name)
            for aloc_paths in self.files
        ]
        for aloc_path in aloc_paths:
            aloc_result = bl_import_aloc.load_aloc(
                self, context, aloc_path, True
            )

            if aloc_result == -1:
                BlenderUI.MessageBox(
                    'Failed to import ALOC "%s"' % aloc_path, "Importing error", "ERROR"
                )
                return {"CANCELLED"}

            layer = bpy.context.view_layer
            layer.update()

        return {"FINISHED"}


class ExportALOC(bpy.types.Operator, ExportHelper):
    """Export to a ALOC file"""

    bl_idname = "export_mesh.aloc"
    bl_label = "Export ALOC Mesh"
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_parent_id = "FILE_PT_operator"
    bl_options = {"PRESET"}
    check_extension = True
    filename_ext = ".aloc"
    filter_glob: StringProperty(default="*.aloc", options={"HIDDEN"})

    def get_collections(self, context):
        items = [(col.name, col.name, "") for col in bpy.data.collections]

        if not items:
            return [("NONE", "None", "")]

        for i, coll_name in enumerate(items):
            if coll_name[0] == bpy.context.collection.name:
                items[0], items[i] = items[i], items[0]

        return items

    export_collection: EnumProperty(
        name="",
        description="The collection to turn into an aloc",
        items=get_collections,
        default=None,
    )

    export_all_collections: BoolProperty(
        name="Export All Collections",
        description="Exports all of the 'root' collections in main Scene Collection as PRIMs",
        default=True,
    )

    def draw(self, context):
        if ".aloc" not in self.filepath.lower():
            return
        layout = self.layout
        layout.label(text="Export options:")
        row = layout.row(align=True)
        row.prop(self, "export_collection")
        row = layout.row(align=True)
        row.prop(self, "export_all_collections")


    def execute(self, context):
        from . import bl_export_aloc

        if self.export_collection == "NONE":
            collection = bpy.data.scenes[0].collection
        else:
            collection = bpy.data.collections[self.export_collection]
        keywords = self.as_keywords(
            ignore=("check_existing", "filter_glob", "export_collection")
        )
        return bl_export_aloc.save_aloc(
            collection, **keywords
        )

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------


classes = [
    AlocProperties,
    GLACIER_PT_AlocPropertiesPanel,
    ImportALOC,
    ExportALOC
]


def register():
    for cls in classes:
        register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_aloc)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_aloc)
    bpy.types.Mesh.aloc_properties = PointerProperty(type=AlocProperties)


def unregister():
    for cls in classes:
        unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_aloc)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_aloc)
    del bpy.types.Mesh.aloc_properties


def menu_func_import_aloc(self, context):
    self.layout.operator(ImportALOC.bl_idname, text="Glacier Collision Mesh (.aloc)")


def menu_func_export_aloc(self, context):
    self.layout.operator(
        ExportALOC.bl_idname, text="Glacier Collision Mesh (.aloc)"
    )



if __name__ == "__main__":
    register()
