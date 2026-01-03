from . import format as aloc_format
from .format import PhysicsCollisionType, PhysicsDataType, PhysicsCollisionPrimitiveType
import bpy
import bmesh
import math


def log(level, msg, filter_field):
    enabled = ["ERROR", "WARNING", "INFO", "DEBUG"]  # Log levels are "DEBUG", "INFO", "WARNING", "ERROR"
    if level in enabled:  # and filter_field == "0031CDA11AFD98A9":
        print("[" + str(level) + "] " + str(filter_field) + ": " + str(msg))


def read_aloc(filepath):
    aloc = aloc_format.Physics()
    return_val = aloc.read(filepath)
    if return_val == -1:
        log("ERROR", "Failed to read ALOC from file: " + filepath + ".", "read_aloc")
        return -1
    log("DEBUG", "Finished reading ALOC from file: " + filepath + ".", "read_aloc")

    return aloc


def convex_hull(bm):
    bmesh.ops.convex_hull(bm, input=bm.verts)


def to_mesh(bm, mesh, obj, collection, context):
    bm.to_mesh(mesh)
    obj.data = mesh
    bm.free()
    collection.objects.link(obj)
    context.view_layer.objects.active = obj
    obj.select_set(True)


def set_mesh_aloc_properties(mesh, collision_type, data_type, sub_data_type):
    mask = []
    for col_type in PhysicsCollisionType:
        mask.append(collision_type == col_type.value)
    mesh.aloc_properties.collision_type = mask
    pdt = PhysicsDataType(data_type)
    mesh.aloc_properties.aloc_type = f"{pdt.__class__.__name__}.{pdt.name}"
    pcpt = PhysicsCollisionPrimitiveType(sub_data_type)
    mesh.aloc_properties.aloc_subtype = f"{pcpt.__class__.__name__}.{pcpt.name}"


def create_new_object(aloc_name, collision_type, data_type):
    mesh = bpy.data.meshes.new(aloc_name)
    set_mesh_aloc_properties(mesh, collision_type, data_type, PhysicsCollisionPrimitiveType.NONE)
    obj = bpy.data.objects.new(aloc_name, mesh)
    return obj


def link_new_object(aloc_name, context):
    obj = bpy.context.active_object
    obj.name = aloc_name
    mesh = obj.data
    mesh.name = aloc_name
    context.view_layer.objects.active = obj
    obj.select_set(True)


def collidable_layer(collision_layer):
    excluded_collision_layer_types = [
        # PhysicsCollisionLayerType.SHOT_ONLY_COLLISION,
        # PhysicsCollisionLayerType.ACTOR_DYN_BODY,
        # PhysicsCollisionLayerType.ACTOR_PROXY,
        # PhysicsCollisionLayerType.ACTOR_RAGDOLL,
        # PhysicsCollisionLayerType.AI_VISION_BLOCKER,
        # PhysicsCollisionLayerType.AI_VISION_BLOCKER_AMBIENT_ONLY,
        # PhysicsCollisionLayerType.COLLISION_VOLUME_HITMAN_OFF,
        # PhysicsCollisionLayerType.DYNAMIC_COLLIDABLES_ONLY,
        # PhysicsCollisionLayerType.DYNAMIC_COLLIDABLES_ONLY_NO_CHARACTER,
        # PhysicsCollisionLayerType.DYNAMIC_COLLIDABLES_ONLY_NO_CHARACTER_TRANSPARENT,
        # PhysicsCollisionLayerType.DYNAMIC_TRASH_COLLIDABLES,
        # PhysicsCollisionLayerType.HERO_DYN_BODY,
        # PhysicsCollisionLayerType.ITEMS,
        # PhysicsCollisionLayerType.KINEMATIC_COLLIDABLES_ONLY,
        # PhysicsCollisionLayerType.KINEMATIC_COLLIDABLES_ONLY_TRANSPARENT,
        # PhysicsCollisionLayerType.WEAPONS
    ]
    return collision_layer not in excluded_collision_layer_types


def load_triangle_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers):
    objects = []
    for mesh_index in range(aloc.triangle_mesh_count):
        obj = create_new_object("TriangleMeshCollider", aloc.collision_type, aloc.data_type)
        bm = bmesh.new()
        m = aloc.triangle_meshes[mesh_index]
        bmv = []
        if include_non_collidable_layers or collidable_layer(m.collision_layer):
            for v in m.vertices:
                bmv.append(bm.verts.new(v))
            d = m.triangle_data
            for i in range(0, len(d), 3):
                face = (bmv[d[i]], bmv[d[i + 1]], bmv[d[i + 2]])
                try:
                    bm.faces.new(face)
                except ValueError as err:
                    log("DEBUG", "[ERROR] Could not add face to TriangleMesh: " + str(err), "load_aloc")
        else:
            log("DEBUG", "Skipping Non-collidable ALOC mesh: " + aloc_name + " with mesh index: " + str(
                mesh_index) + " and collision layer type: " + str(m.collision_layer), "load_aloc")
        mesh = obj.data
        to_mesh(bm, mesh, obj, collection, context)
        objects.append(obj)
    return objects


def load_convex_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers):
    objects = []
    for mesh_index in range(aloc.convex_mesh_count):
        log("DEBUG", " " + aloc_name + " convex mesh " + str(mesh_index) + " / " + str(aloc.convex_mesh_count),
            "load_aloc")
        obj = create_new_object("ConvexMeshCollider", aloc.collision_type, aloc.data_type)
        bm = bmesh.new()
        m = aloc.convex_meshes[mesh_index]
        if include_non_collidable_layers or collidable_layer(m.collision_layer):
            for v in m.vertices:
                bm.verts.new(v)
        else:
            log("DEBUG", "Skipping Non-collidable ALOC mesh: " + aloc_name + " with mesh index: " + str(
                mesh_index) + " and collision layer type: " + str(m.collision_layer), "load_aloc")
        mesh = obj.data
        bm.from_mesh(mesh)
        convex_hull(bm)
        to_mesh(bm, mesh, obj, collection, context)
        objects.append(obj)
    return objects


def load_primitive_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers):
    objects = []
    log("DEBUG", "Primitive Type", "load_aloc")
    log("DEBUG", "Primitive count: " + str(aloc.primitive_count), "load_aloc")
    log("DEBUG", "Primitive Box count: " + str(aloc.primitive_boxes_count), "load_aloc")
    log("DEBUG", "Primitive Spheres count: " + str(aloc.primitive_spheres_count), "load_aloc")
    log("DEBUG", "Primitive Capsules count: " + str(aloc.primitive_capsules_count), "load_aloc")
    for mesh_index, box in enumerate(aloc.primitive_boxes):
        if include_non_collidable_layers or collidable_layer(box.collision_layer):
            log("DEBUG", "Primitive Box", "load_aloc")
            obj = create_new_object("BoxCollider", aloc.collision_type, aloc.data_type)
            obj.location = (box.position[0], box.position[1], box.position[2])
            if len(box.rotation) == 4:
                obj.rotation_mode = 'QUATERNION'
                obj.rotation_quaternion = (box.rotation[3], box.rotation[0], box.rotation[1], box.rotation[2])
            else:
                x = box.rotation[0]
                y = box.rotation[1]
                z = box.rotation[2]
                w = math.sqrt(max(0.0, 1.0 - (x * x + y * y + z * z)))
                obj.rotation_mode = 'QUATERNION'
                obj.rotation_quaternion = (w, x, y, z)
            bm = bmesh.new()
            bmv = []
            sx = box.half_extents[0]
            sy = box.half_extents[1]
            sz = box.half_extents[2]
            vertices = [
                [sx, sy, -sz],
                [sx, -sy, -sz],
                [-sx, -sy, -sz],
                [-sx, sy, -sz],
                [sx, sy, sz],
                [sx, -sy, sz],
                [-sx, -sy, sz],
                [-sx, sy, sz]
            ]
            for v in vertices:
                bmv.append(bm.verts.new(v))
            bm.faces.new((bmv[0], bmv[1], bmv[2], bmv[3]))  # bottom
            bm.faces.new((bmv[4], bmv[5], bmv[6], bmv[7]))  # top
            bm.faces.new((bmv[0], bmv[1], bmv[5], bmv[4]))  # right
            bm.faces.new((bmv[2], bmv[3], bmv[7], bmv[6]))
            bm.faces.new((bmv[0], bmv[3], bmv[7], bmv[4]))
            bm.faces.new((bmv[1], bmv[2], bmv[6], bmv[5]))
            mesh = obj.data
            to_mesh(bm, mesh, obj, collection, context)
            objects.append(obj)
        else:
            log("DEBUG", "Skipping Non-collidable ALOC mesh: " + aloc_name + " with mesh index: " + str(
                mesh_index) + " and collision layer type: " + str(box.collision_layer), "load_aloc")
    for mesh_index, sphere in enumerate(aloc.primitive_spheres):
        if include_non_collidable_layers or collidable_layer(sphere.collision_layer):
            log("DEBUG", "Primitive Sphere", "load_aloc")
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=sphere.radius,
                location=(sphere.position[0], sphere.position[1], sphere.position[2]),
                rotation=(sphere.rotation[0], sphere.rotation[1], sphere.rotation[2]),
            )
            link_new_object("SphereCollider", context)
            obj = bpy.context.active_object
            set_mesh_aloc_properties(obj.data, aloc.collision_type, aloc.data_type,
                                     PhysicsCollisionPrimitiveType.SPHERE)
            objects.append(obj)
        else:
            log("DEBUG", "Skipping Non-collidable ALOC mesh: " + aloc_name + " with mesh index: " + str(
                mesh_index) + " and collision layer type: " + str(sphere.collision_layer), "load_aloc")
    for mesh_index, capsule in enumerate(aloc.primitive_capsules):
        if include_non_collidable_layers or collidable_layer(capsule.collision_layer):
            log("DEBUG", "Primitive Capsule", "load_aloc")
            bpy.ops.object.select_all(action='DESELECT')
            cylinder_height = capsule.length - 2 * capsule.radius
            if cylinder_height < 0:
                cylinder_height = 0
            z_offset = cylinder_height / 2

            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=capsule.radius,
                location=(0, 0, z_offset),
            )
            top = bpy.context.active_object
            bpy.ops.mesh.primitive_cylinder_add(
                radius=capsule.radius,
                depth=cylinder_height,
                end_fill_type='NOTHING',
                location=(0, 0, 0),
            )
            cylinder = bpy.context.active_object
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=capsule.radius,
                location=(0, 0, -z_offset),
            )
            bot = bpy.context.active_object
            top.select_set(True)
            cylinder.select_set(True)
            bot.select_set(True)
            context.view_layer.objects.active = cylinder
            bpy.ops.object.join()
            obj = bpy.context.active_object
            obj.name = "CapsuleCollider"
            obj.location = (capsule.position[0], capsule.position[1], capsule.position[2])
            if len(capsule.rotation) == 4:
                obj.rotation_mode = 'QUATERNION'
                obj.rotation_quaternion = (capsule.rotation[3], capsule.rotation[0], capsule.rotation[1], capsule.rotation[2])
            else:
                x = capsule.rotation[0]
                y = capsule.rotation[1]
                z = capsule.rotation[2]
                w = math.sqrt(max(0.0, 1.0 - (x * x + y * y + z * z)))
                obj.rotation_mode = 'QUATERNION'
                obj.rotation_quaternion = (w, x, y, z)
            set_mesh_aloc_properties(obj.data, aloc.collision_type, aloc.data_type,
                                     PhysicsCollisionPrimitiveType.CAPSULE)
            objects.append(obj)
        else:
            log("DEBUG", "Skipping Non-collidable ALOC mesh: " + aloc_name + " with mesh index: " + str(
                mesh_index) + " and collision layer type: " + str(capsule.collision_layer), "load_aloc")
    return objects


def load_aloc(operator, context, filepath, include_non_collidable_layers):
    """Imports an ALOC mesh from the given path"""

    aloc_name = bpy.path.display_name_from_filepath(filepath)
    aloc = read_aloc(filepath)
    if aloc == -1:
        log("ERROR", "Failed to read Mesh ALOC file " + filepath, "load_aloc")
        return -1


    log("DEBUG", "Converting ALOC: " + aloc_name + " to blender mesh.", aloc_name)

    collection = bpy.data.collections.new(aloc_name)
    bpy.context.scene.collection.children.link(collection)
    collection.prim_collection_properties.physics_data_type = str(PhysicsDataType(aloc.data_type))
    collection.prim_collection_properties.physics_collision_type = str(PhysicsCollisionType(aloc.collision_type))
    if aloc.data_type == aloc_format.PhysicsDataType.CONVEX_MESH_AND_TRIANGLE_MESH:
        log("DEBUG", "Converting Convex Mesh and Triangle Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        load_triangle_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.CONVEX_MESH:
        log("DEBUG", "Converting Convex Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        load_convex_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.TRIANGLE_MESH:
        log("DEBUG", "Converting Triangle Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        load_triangle_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.PRIMITIVE:
        log("DEBUG", "Converting Primitive Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        load_primitive_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.CONVEX_MESH_AND_PRIMITIVE:
        log("DEBUG", "Converting Convex Mesh and Primitive Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        load_convex_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
        load_primitive_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.TRIANGLE_MESH_AND_PRIMITIVE:
        log("DEBUG", "Converting Vertex Mesh and Primitive Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        load_triangle_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
        load_primitive_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    else:
        log("ERROR", "Unknown data type: " + str(aloc.data_type) + " for Mesh ALOC " + aloc_name, "load_aloc")
        return -1

    log("DEBUG", "Finished converting ALOC: " + aloc_name + " to blender mesh.", aloc_name)
