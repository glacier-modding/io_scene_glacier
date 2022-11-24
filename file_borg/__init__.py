import bpy

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = []
modules = []


def register():
    from bpy.utils import register_class

    for module in modules:
        module.register()

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for module in reversed(modules):
        module.unregister()

    for cls in classes:
        unregister_class(cls)


if __name__ == "__main__":
    register()
