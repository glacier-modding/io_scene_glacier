import os
import bpy
import bmesh
import numpy as np
import mathutils as mu

from . import format as aloc_format


def save_aloc(
    selected_collection,
    filepath: str,
    export_all_collections: bool = False,
):
    """
    Export the selected collection to an aloc
    Writes to the given path.
    Returns "FINISHED" when successful
    """
    export_file = os.fsencode(filepath)
    collections = []
    print(selected_collection)
    print(export_all_collections)
    if selected_collection == bpy.data.scenes[0].collection:
        print("selected collection is None")

        collections.append(bpy.data.scenes[0].collection)
        print(bpy.data.scenes[0].collection)
    else:
        if export_all_collections:
            for collection in bpy.data.scenes[0].collection.children:
                collections.append(collection)
        else:
            collections.append(selected_collection)
    print(collections)

    for collection in collections:
        print(collection)
        mesh_obs = [o for o in collection.all_objects if o.type == "MESH"]
        print(mesh_obs)

        write_aloc = False
        # Only export to ALOC if data and collision types are both not set to NONE
        physics_data_type = int(
            collection.prim_collection_properties.physics_data_type
        )
        physics_collision_type = int(
            collection.prim_collection_properties.physics_collision_type
        )
        if physics_data_type > 0 and physics_collision_type > 0:
            aloc = aloc_format.Physics()
            collision_settings = aloc_format.PhysicsCollisionSettings()
            collision_settings.data_type = physics_data_type
            collision_settings.collider_type = physics_collision_type
            aloc.set_collision_settings(collision_settings)
            for ob in mesh_obs:
                if ob.name.startswith("ConvexMeshCollider"):
                    vertices, indices = get_vertices_and_indices(ob)
                    aloc.add_convex_mesh(
                        vertices,
                        indices,
                        int(ob.data.prim_physics_properties.collision_layer_type),
                    )
                    write_aloc = True
                    del vertices
                    del indices
                elif ob.name.startswith("TriangleMeshCollider"):
                    vertices, indices = get_vertices_and_indices(ob)
                    aloc.add_triangle_mesh(
                        vertices,
                        indices,
                        int(ob.data.prim_physics_properties.collision_layer_type),
                    )
                    write_aloc = True
                    del vertices
                    del indices
                elif ob.name.startswith("BoxCollider"):
                    aloc.add_primitive_box(
                        list(ob.dimensions / 2),
                        int(ob.data.prim_physics_properties.collision_layer_type),
                        list(ob.matrix_world.to_translation())[:3],
                        list(ob.matrix_world.to_quaternion()),
                    )
                    write_aloc = True
                elif ob.name.startswith("CapsuleCollider"):
                    radius = (ob.dimensions[0] + ob.dimensions[1]) / 4
                    length = ob.dimensions[2]
                    aloc.add_primitive_capsule(
                        radius,
                        length,
                        int(ob.data.prim_physics_properties.collision_layer_type),
                        list(ob.matrix_world.to_translation())[:3],
                        list(ob.matrix_world.to_quaternion()),
                    )
                    write_aloc = True
                elif ob.name.startswith("SphereCollider"):
                    radius = (ob.dimensions[0] + ob.dimensions[1]) / 4
                    aloc.add_primitive_sphere(
                        radius,
                        int(ob.data.prim_physics_properties.collision_layer_type),
                        list(ob.matrix_world.to_translation())[:3],
                        list(ob.matrix_world.to_quaternion()),
                    )
                    write_aloc = True
            if write_aloc:
                aloc.write(
                    export_file
                )
    return {"FINISHED"}


def get_positions(mesh, matrix):
    # read the vertex locations
    locs = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    source = mesh.vertices

    for vert in source:
        vert.co = matrix @ vert.co

    source.foreach_get("co", locs)
    locs = locs.reshape(len(mesh.vertices), 3)
    locs = np.c_[locs, np.ones(len(mesh.vertices), dtype=int)]

    return locs


def get_vertices_and_indices(blender_obj):
    if len(blender_obj.modifiers) == 0:
        mesh = blender_obj.to_mesh()
    else:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh_owner = blender_obj.evaluated_get(depsgraph)
        mesh = mesh_owner.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

    locs = get_positions(mesh, blender_obj.matrix_world.copy())

    dot_fields = [("vertex_index", np.uint32)]

    dots = np.empty(len(mesh.loops), dtype=np.dtype(dot_fields))

    vidxs = np.empty(len(mesh.loops))
    mesh.loops.foreach_get("vertex_index", vidxs)
    dots["vertex_index"] = vidxs
    del vidxs

    # Calculate triangles and sort them into primitives.
    mesh.calc_loop_triangles()
    loop_indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.uint32)
    mesh.loop_triangles.foreach_get("loops", loop_indices)

    prim_dots = dots[loop_indices]
    prim_dots, indices = np.unique(prim_dots, return_inverse=True)
    indices = indices.tolist()

    blender_idxs = prim_dots["vertex_index"]
    vertices = np.empty((len(prim_dots), 3), dtype=np.float32)
    vertices[:, 0] = locs[blender_idxs, 0]
    vertices[:, 1] = locs[blender_idxs, 1]
    vertices[:, 2] = locs[blender_idxs, 2]
    vertices = vertices.tolist()
    vertices = [i for v in vertices for i in v]

    return vertices, indices
