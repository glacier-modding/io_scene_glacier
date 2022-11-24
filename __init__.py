# ##### BEGIN LICENSE BLOCK #####
#
# io_scene_glacier
# Copyright (c) 2022+, The Glacier Modding Team
# All rights reserved.

# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.

# * Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ##### END LICENSE BLOCK #####

bl_info = {
    "name": "Glacier 2 Engine Tools",
    "description": "Tools for the Glacier 2 Engine",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "wiki_url": "",
    "tracker_url": "",
}

import bpy
from . import file_prim
from . import file_mjba
from . import file_borg


from bpy.props import (BoolVectorProperty,
                       PointerProperty,
                       )

from bpy.types import (PropertyGroup,
                       )

# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class GlacierSettings(PropertyGroup):

    def show_lod_update(self, context):

        mesh_obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        for obj in mesh_obs:

            should_show = False
            for bit in range(8):
                if self.show_lod[bit]:
                    if obj.data.prim_properties.lod[bit] == self.show_lod[bit]:
                        should_show = True

            obj.hide_set(not should_show)

        return None

    show_lod: BoolVectorProperty(
        name='show_lod',
        description='Set which LOD levels should be shown',
        default=(True, True, True, True, True, True, True, True),
        size=8,
        subtype='LAYER',
        update=show_lod_update,
    )


# ------------------------------------------------------------------------
#    Panels
# ------------------------------------------------------------------------
class GLACIER_PT_settingsPanel(bpy.types.Panel):
    bl_idname = 'GLACIER_PT_settingsPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Glacier'
    bl_label = 'Settings'

    def draw(self, context):
        glacier_settings = context.scene.glacier_settings

        layout = self.layout
        layout.label(text="show LOD:")

        row = layout.row(align=True)
        for i, name in enumerate(["high", "   ", "   ", "   ", "   ", "   ", "   ", "low"]):
            row.prop(glacier_settings, "show_lod", index=i, text=name, toggle=True)

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = [
    GlacierSettings,
    GLACIER_PT_settingsPanel
]

modules = [
    file_prim,
    # file_mjba, # WIP module. enable at own risk
    file_borg
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
