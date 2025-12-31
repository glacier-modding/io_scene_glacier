bl_info = {
    "name": "Glacier 2 Engine Tools",
    "description": "Tools for the Glacier 2 Engine",
    "version": (0, 6, 0),
    "blender": (3, 0, 0),
    "doc_url": "https://glaciermodding.org/docs/blender/",
    "tracker_url": "https://github.com/glacier-modding/io_scene_glacier/issues",
    "category": "Import-Export",
}

import bpy
from . import file_prim
from . import file_aloc
from . import file_mjba
from . import file_borg


from bpy.props import (
    BoolVectorProperty,
    PointerProperty,
)

from bpy.types import (
    PropertyGroup,
)

# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------


class GlacierSettings(PropertyGroup):
    def show_lod_update(self, context):
        mesh_obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        for obj in mesh_obs:
            should_show = False
            for bit in range(8):
                if self.show_lod[bit]:
                    if obj.data.prim_properties.lod[bit] == self.show_lod[bit]:
                        should_show = True

            obj.hide_set(not should_show)

        return None

    show_lod: BoolVectorProperty(
        name="show_lod",
        description="Set which LOD levels should be shown",
        default=(True, True, True, True, True, True, True, True),
        size=8,
        subtype="LAYER",
        update=show_lod_update,
    )

    def show_collision_type_update(self, context):
        mesh_obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        for obj in mesh_obs:
            should_show = False
            for bit in range(6):
                if self.show_collision_type[bit]:
                    if obj.data.aloc_properties.collision_type[bit] == self.show_collision_type[bit]:
                        should_show = True

            obj.hide_set(not should_show)

        return None

    show_collision_type: BoolVectorProperty(
        name="show_collision_type",
        description="Set which Collision types should be shown",
        default=(True, True, True, True, True, True),
        size=6,
        subtype="LAYER",
        update=show_collision_type_update,
    )


# ------------------------------------------------------------------------
#    Panels
# ------------------------------------------------------------------------
class GLACIER_PT_settingsPanel(bpy.types.Panel):
    bl_idname = "GLACIER_PT_settingsPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Glacier"
    bl_label = "Settings"

    def draw(self, context):
        glacier_settings = context.scene.glacier_settings

        layout = self.layout
        layout.label(text="show LOD:")

        row = layout.row(align=True)
        for i, name in enumerate(
            ["high", "   ", "   ", "   ", "   ", "   ", "   ", "low"]
        ):
            row.prop(glacier_settings, "show_lod", index=i, text=name, toggle=True)

        layout.label(text="show Collision Types:")

        row = layout.row(align=True)
        for i, name in enumerate(
            ["N", "S", "R", "ShL", "KiL", "BC"]
        ):
            row.prop(glacier_settings, "show_collision_type", index=i, text=name, toggle=True)


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = [GlacierSettings, GLACIER_PT_settingsPanel]

modules = [
    file_prim,
    file_aloc,
    # file_mjba, # WIP module. enable at own risk
    file_borg,
]


def register():
    from bpy.utils import register_class

    for module in modules:
        module.register()

    for cls in classes:
        register_class(cls)

    bpy.types.Scene.glacier_settings = PointerProperty(type=GlacierSettings)


def unregister():
    from bpy.utils import unregister_class

    for module in reversed(modules):
        module.unregister()

    for cls in classes:
        unregister_class(cls)

    del bpy.types.Scene.glacier_settings


if __name__ == "__main__":
    register()
