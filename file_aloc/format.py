import enum
import os
import sys
import ctypes


class PhysicsDataType(enum.IntEnum):
    NONE = 0
    CONVEX_MESH = 1
    TRIANGLE_MESH = 2
    CONVEX_MESH_AND_TRIANGLE_MESH = 3
    PRIMITIVE = 4
    CONVEX_MESH_AND_PRIMITIVE = 5
    TRIANGLE_MESH_AND_PRIMITIVE = 6


class PhysicsCollisionType(enum.IntEnum):
    NONE = 0
    STATIC = 1
    RIGIDBODY = 2


class PhysicsCollisionLayerType(enum.IntEnum):
    COLLIDE_WITH_ALL = 0
    STATIC_COLLIDABLES_ONLY = 1
    DYNAMIC_COLLIDABLES_ONLY = 2
    STAIRS = 3
    SHOT_ONLY_COLLISION = 4
    DYNAMIC_TRASH_COLLIDABLES = 5
    KINEMATIC_COLLIDABLES_ONLY = 6
    STATIC_COLLIDABLES_ONLY_TRANSPARENT = 7
    DYNAMIC_COLLIDABLES_ONLY_TRANSPARENT = 8
    KINEMATIC_COLLIDABLES_ONLY_TRANSPARENT = 9
    STAIRS_STEPS = 10
    STAIRS_SLOPE = 11
    HERO_PROXY = 12
    ACTOR_PROXY = 13
    HERO_VR = 14
    CLIP = 15
    ACTOR_RAGDOLL = 16
    CROWD_RAGDOLL = 17
    LEDGE_ANCHOR = 18
    ACTOR_DYN_BODY = 19
    HERO_DYN_BODY = 20
    ITEMS = 21
    WEAPONS = 22
    COLLISION_VOLUME_HITMAN_ON = 23
    COLLISION_VOLUME_HITMAN_OFF = 24
    DYNAMIC_COLLIDABLES_ONLY_NO_CHARACTER = 25
    DYNAMIC_COLLIDABLES_ONLY_NO_CHARACTER_TRANSPARENT = 26
    COLLIDE_WITH_STATIC_ONLY = 27
    AI_VISION_BLOCKER = 28
    AI_VISION_BLOCKER_AMBIENT_ONLY = 29
    UNUSED_LAST = 30


class PhysicsCollisionPrimitiveType(enum.IntEnum):
    BOX = 0
    CAPSULE = 1
    SPHERE = 2


class PhysicsCollisionSettings(ctypes.Structure):
    _fields_ = [
        ("data_type", ctypes.c_uint32),
        ("collider_type", ctypes.c_uint32),
    ]


class Physics:
    def __init__(self):
        self.data_type = PhysicsDataType.NONE
        self.collision_type = PhysicsCollisionType.NONE
        if not os.environ["PATH"].startswith(
            os.path.abspath(os.path.dirname(__file__))
        ):
            os.environ["PATH"] = (
                os.path.abspath(os.path.dirname(__file__))
                + os.pathsep
                + os.environ["PATH"]
            )
        self.lib = ctypes.CDLL(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "alocgen.dll")),
            winmode=0,
        )
        self.lib.AddConvexMesh.argtypes = (
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_uint64,
        )
        self.lib.AddConvexMesh.restype = ctypes.c_int
        self.lib.AddTriangleMesh.argtypes = (
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_uint64,
        )
        self.lib.AddTriangleMesh.restype = ctypes.c_int
        self.lib.AddPrimitiveBox.argtypes = (
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        )
        self.lib.AddPrimitiveBox.restype = ctypes.c_int
        self.lib.AddPrimitiveCapsule.argtypes = (
            ctypes.c_float,
            ctypes.c_float,
            ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        )
        self.lib.AddPrimitiveCapsule.restype = ctypes.c_int
        self.lib.AddPrimitiveSphere.argtypes = (
            ctypes.c_float,
            ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
        )
        self.lib.AddPrimitiveSphere.restype = ctypes.c_int
        self.lib.SetCollisionSettings.argtypes = (
            ctypes.POINTER(PhysicsCollisionSettings),
        )
        self.lib.SetCollisionSettings.restype = ctypes.c_int
        self.lib.NewPhysics()

    def write(self, filepath):
        self.lib.Write(filepath)

    def set_collision_settings(self, settings):
        self.lib.SetCollisionSettings(ctypes.byref(settings))

    def add_convex_mesh(self, vertices_list, indices_list, collider_layer):
        vertices = (ctypes.c_float * len(vertices_list))(*vertices_list)
        indices = (ctypes.c_uint32 * len(indices_list))(*indices_list)
        self.lib.AddConvexMesh(
            len(vertices_list),
            vertices,
            int(len(indices_list) / 3),
            indices,
            collider_layer,
        )

    def add_triangle_mesh(self, vertices_list, indices_list, collider_layer):
        vertices = (ctypes.c_float * len(vertices_list))(*vertices_list)
        indices = (ctypes.c_uint32 * len(indices_list))(*indices_list)
        self.lib.AddTriangleMesh(
            len(vertices_list),
            vertices,
            int(len(indices_list) / 3),
            indices,
            collider_layer,
        )

    def add_primitive_box(
        self, half_extents_list, collider_layer, position_list, rotation_list
    ):
        half_extents = (ctypes.c_float * len(half_extents_list))(*half_extents_list)
        position = (ctypes.c_float * len(position_list))(*position_list)
        rotation = (ctypes.c_float * len(rotation_list))(*rotation_list)
        self.lib.AddPrimitiveBox(half_extents, collider_layer, position, rotation)

    def add_primitive_capsule(
        self, radius, length, collider_layer, position_list, rotation_list
    ):
        position = (ctypes.c_float * len(position_list))(*position_list)
        rotation = (ctypes.c_float * len(rotation_list))(*rotation_list)
        self.lib.AddPrimitiveCapsule(radius, length, collider_layer, position, rotation)

    def add_primitive_sphere(
        self, radius, collider_layer, position_list, rotation_list
    ):
        position = (ctypes.c_float * len(position_list))(*position_list)
        rotation = (ctypes.c_float * len(rotation_list))(*rotation_list)
        self.lib.AddPrimitiveSphere(radius, collider_layer, position, rotation)
