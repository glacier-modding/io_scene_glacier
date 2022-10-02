# ##### BEGIN LICENSE BLOCK #####
#
# io_scene_glacier
# Copyright (c) 2020+, REDACTED
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
from .GlacierEngine import GlacierEngine
from .. import BlenderUI

from bpy.props import (StringProperty,
                       BoolProperty,
                       BoolVectorProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Operator,
                       PropertyGroup,
                       )

# ------------------------------------------------------------------------
#    Global Animation Object
# ------------------------------------------------------------------------

glacier_engine = GlacierEngine()


# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class MyProperties(PropertyGroup):
    mjbaimport_path: StringProperty(
        name="MJBA Import Path",
        description="Path to the MJBA file to import",
        default="",
        maxlen=1024,
        subtype='FILE_PATH',
    )

    mjbaexport_path: StringProperty(
        name="MJBA Export Path",
        description="Choose where to save the MJBA file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )

    mrtrimport_path: StringProperty(
        name="MRTR Import Path",
        description="Path to the MRTR file to import",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )

    mrtrexport_path: StringProperty(
        name="MRTR Export Path",
        description="Choose where to save the MRTR file",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )

    mjba_hash: StringProperty(
        name="MJBA Hash/Path",
        description="Hash or path of the MJBA file",
        default="",
        maxlen=1024,
    )

    mrtr_dependencyhash: StringProperty(
        name="MRTR Hash/Path",
        description="Specify the hash or path to a MRTR resource",
        default="[assembly:/geometry/characters/_export_rigs/biped~~.xml].pc_rtr",
        maxlen=1024,
    )

    atmd_dependencyhash: StringProperty(
        name="ATMD Hash/Path",
        description="Specify a hash or path to a ATMD resource",
        default="",
        maxlen=1024,
    )

    mjba_worldtransform: BoolProperty(
        name="World Transform",
        description="Toggle whether World Transform is applied to the animation",
        default=False
    )

    meshpicker: PointerProperty(
        name="Mesh Picker",
        description="Choose a mesh",
        type=bpy.types.Object
    )

    animationpicker: PointerProperty(
        name="Animation Picker",
        description="Choose an animation",
        type=bpy.types.Action
    )


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class Glacier_ImportMJBA(Operator):
    bl_label = "Import MJBA/MRTR"
    bl_idname = "glacier.importmjba"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool
        if mytool.mjbaimport_path == "" or mytool.mrtrimport_path == "":
            BlenderUI.MessageBox("You must import an MJBA and it's corresponding MRTR!", icon="ERROR")
            return {'FINISHED'}
        if mytool.meshpicker == None:
            BlenderUI.MessageBox("No object selected!", icon="ERROR")
            return {'FINISHED'}
        if mytool.meshpicker.type != 'ARMATURE':
            BlenderUI.MessageBox(mytool.meshpicker.name + " does not have an armature!", icon="ERROR")
            return {'FINISHED'}
        global animation
        glacier_engine.import_animation(mytool.meshpicker, bpy.path.abspath(mytool.mjbaimport_path),
                                        bpy.path.abspath(mytool.mrtrimport_path))
        return {'FINISHED'}


class Glacier_ExportMJBA(Operator):
    bl_label = "Export MJBA JSON"
    bl_idname = "glacier.exportmjba"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool
        if mytool.meshpicker == None:
            BlenderUI.MessageBox("No object selected!", icon="ERROR")
            return {'FINISHED'}
        if mytool.meshpicker.type != 'ARMATURE':
            BlenderUI.MessageBox(mytool.meshpicker.name + " does not have an armature!", icon="ERROR")
            return {'FINISHED'}
        if mytool.meshpicker.animation_data == None:
            BlenderUI.MessageBox(mytool.meshpicker.name + " does not have any animation data!", icon="ERROR")
            return {'FINISHED'}
        if mytool.meshpicker.animation_data.action == None:
            BlenderUI.MessageBox(mytool.meshpicker.name + " does not have any animation data action!", icon="ERROR")
            return {'FINISHED'}
        if mytool.meshpicker.animation_data.action.fcurves == None:
            BlenderUI.MessageBox(mytool.meshpicker.name + " does not have any animation data action fcurves!",
                                 icon="ERROR")
            return {'FINISHED'}
        global animation
        glacier_engine.export_animation(mytool.meshpicker)

        return {'FINISHED'}


class Glacier_ExportMRTR(Operator):
    bl_label = "Export MRTR JSON"
    bl_idname = "glacier.exportmrtr"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool
        global animation
        glacier_engine.export_animation(mytool.meshpicker)

        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Panels
# ------------------------------------------------------------------------

class GLACIER_PT_AnimImportPanel(Panel):
    bl_label = "Glacier Engine Import"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        layout.prop(mytool, "meshpicker")
        layout.prop(mytool, "mjbaimport_path")
        layout.prop(mytool, "mrtrimport_path")
        layout.operator("glacier.importmjba")
        layout.separator()
        layout.label(text="Note: You will first need to import a GLB model from the game.")
        layout.label(text="Or you can use the supplied template model")
        layout.label(text="if you are making an animation for the default character rig.")


class GLACIER_PT_AnimExportPanel(Panel):
    bl_label = "Glacier Engine Export"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        layout.label(text="Metadata Setup:")
        layout.prop(mytool, "mjba_hash")
        layout.prop(mytool, "mrtr_dependencyhash")
        layout.prop(mytool, "atmd_dependencyhash")
        layout.label(text="Note: You only need a custom ATMD file if you have want custom audio events")
        layout.separator()
        layout.prop(mytool, "meshpicker")
        layout.prop(mytool, "mjbaexport_path")
        layout.label(text="Location to save the MJBA JSON file")
        layout.operator("glacier.exportmjba")
        layout.prop(mytool, "mjba_worldtransform")
        layout.separator()
        layout.prop(mytool, "mrtrexport_path")
        layout.label(text="Location to save the MRTR JSON file")
        layout.label(text="Note: You only need a custom MRTR file if you have added/removed any of the bones")
        layout.operator("glacier.exportmrtr")


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    MyProperties,
    Glacier_ImportMJBA,
    Glacier_ExportMJBA,
    Glacier_ExportMRTR,
    GLACIER_PT_AnimImportPanel,
    GLACIER_PT_AnimExportPanel
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.types.Scene.my_tool = PointerProperty(type=MyProperties)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.my_tool


if __name__ == "__main__":
    register()
