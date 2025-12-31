from . import format as aloc_format
from .format import PhysicsCollisionType, PhysicsDataType, PhysicsCollisionPrimitiveType
import bpy
import bmesh


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


def get_triangle_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers):
    objects = []
    for mesh_index in range(aloc.triangle_mesh_count):
        obj = create_new_object(aloc_name, aloc.collision_type, aloc.data_type)
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


def get_convex_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers):
    objects = []
    for mesh_index in range(aloc.convex_mesh_count):
        log("DEBUG", " " + aloc_name + " convex mesh " + str(mesh_index) + " / " + str(aloc.convex_mesh_count),
            "load_aloc")
        obj = create_new_object(aloc_name, aloc.collision_type, aloc.data_type)
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


def get_primitive_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers):
    objects = []
    log("DEBUG", "Primitive Type", "load_aloc")
    log("DEBUG", "Primitive count: " + str(aloc.primitive_count), "load_aloc")
    log("DEBUG", "Primitive Box count: " + str(aloc.primitive_boxes_count), "load_aloc")
    log("DEBUG", "Primitive Spheres count: " + str(aloc.primitive_spheres_count), "load_aloc")
    log("DEBUG", "Primitive Capsules count: " + str(aloc.primitive_capsules_count), "load_aloc")
    for mesh_index, box in enumerate(aloc.primitive_boxes):
        if include_non_collidable_layers or collidable_layer(box.collision_layer):
            log("DEBUG", "Primitive Box", "load_aloc")
            obj = create_new_object(aloc_name, aloc.collision_type, aloc.data_type)
            bm = bmesh.new()
            bmv = []
            x = box.position[0]
            y = box.position[1]
            z = box.position[2]
            rx = box.rotation[0]
            ry = box.rotation[1]
            rz = box.rotation[2]
            if rx != 0 or ry != 0 or rz != 0:
                log("DEBUG", "Box has rotation value. Hash: " + aloc_name, "load_aloc")
            sx = box.half_extents[0]
            sy = box.half_extents[1]
            sz = box.half_extents[2]
            vertices = [
                [x + sx, y + sy, z - sz],
                [x + sx, y - sy, z - sz],
                [x - sx, y - sy, z - sz],
                [x - sx, y + sy, z - sz],
                [x + sx, y + sy, z + sz],
                [x + sx, y - sy, z + sz],
                [x - sx, y - sy, z + sz],
                [x - sx, y + sy, z + sz]
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
            bpy.ops.mesh.primitive_ico_sphere_add(
                subdivisions=2,
                radius=sphere.radius,
                location=(sphere.position[0], sphere.position[1], sphere.position[2]),
                rotation=(sphere.rotation[0], sphere.rotation[1], sphere.rotation[2]),
            )
            link_new_object(aloc_name, context)
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
            bpy.ops.mesh.primitive_ico_sphere_add(
                subdivisions=2,
                radius=capsule.radius,
                location=(capsule.position[0], capsule.position[1], capsule.position[2] + capsule.length),
                rotation=(capsule.rotation[0], capsule.rotation[1], capsule.rotation[2]),
            )
            link_new_object(aloc_name + "_top", context)
            obj = bpy.context.active_object
            set_mesh_aloc_properties(obj.data, aloc.collision_type, aloc.data_type,
                                     PhysicsCollisionPrimitiveType.CAPSULE)
            objects.append(obj)
            bpy.ops.mesh.primitive_cylinder_add(
                radius=capsule.radius,
                depth=capsule.length,
                end_fill_type='NOTHING',
                location=(capsule.position[0], capsule.position[1], capsule.position[2]),
                rotation=(capsule.rotation[0], capsule.rotation[1], capsule.rotation[2])
            )
            link_new_object(aloc_name + "_cylinder", context)
            obj = bpy.context.active_object
            set_mesh_aloc_properties(obj.data, aloc.collision_type, aloc.data_type,
                                     PhysicsCollisionPrimitiveType.CAPSULE)
            objects.append(obj)
            bpy.ops.mesh.primitive_ico_sphere_add(
                subdivisions=2,
                radius=capsule.radius,
                location=(capsule.position[0], capsule.position[1], capsule.position[2] - capsule.length),
                rotation=(capsule.rotation[0], capsule.rotation[1], capsule.rotation[2]),
            )
            link_new_object(aloc_name + "_bottom", context)
            obj = bpy.context.active_object
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
    log("DEBUG", "Converting ALOC: " + aloc_name + " to blender mesh.", aloc_name)

    collection = context.scene.collection
    objects = []
    if aloc.collision_type == PhysicsCollisionType.RIGIDBODY:
        log("DEBUG", "Skipping RigidBody ALOC " + aloc_name, "load_aloc")
        return PhysicsCollisionType.RIGIDBODY, objects
    if aloc.data_type == aloc_format.PhysicsDataType.CONVEX_MESH_AND_TRIANGLE_MESH:
        log("DEBUG", "Converting Convex Mesh and Triangle Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        objects += get_convex_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
        objects += get_triangle_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.CONVEX_MESH:
        log("DEBUG", "Converting Convex Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        objects += get_convex_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.TRIANGLE_MESH:
        log("DEBUG", "Converting Triangle Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        objects += get_triangle_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.PRIMITIVE:
        log("DEBUG", "Converting Primitive Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        objects += get_primitive_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.CONVEX_MESH_AND_PRIMITIVE:
        log("DEBUG", "Converting Convex Mesh and Primitive Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        objects += get_convex_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
        objects += get_primitive_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    elif aloc.data_type == aloc_format.PhysicsDataType.TRIANGLE_MESH_AND_PRIMITIVE:
        log("DEBUG", "Converting Vertex Mesh and Primitive Mesh ALOC " + aloc_name + " to blender mesh", "load_aloc")
        objects += get_triangle_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
        objects += get_primitive_mesh_objects(aloc, aloc_name, collection, context, include_non_collidable_layers)
    else:
        log("ERROR", "Unknown data type: " + str(aloc.data_type) + " for Mesh ALOC " + aloc_name, "load_aloc")

    log("DEBUG", "Finished converting ALOC: " + aloc_name + " to blender mesh.", aloc_name)
    log("DEBUG", "objects: " + str(objects), aloc_name)

    return aloc.collision_type, objects
