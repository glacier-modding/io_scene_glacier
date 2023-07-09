import os
import bpy
import bmesh
import numpy as np
import mathutils as mu
from functools import cmp_to_key
import copy
import sys

from . import format
from .. import io_binary
from .. import BlenderUI
from ..file_aloc import format as aloc_format

def save_prim(collection, filepath: str, hitbox_slider: int, force_highres_flag: bool = False):
    """
    Export the selected collection to a prim
    Writes to the given path.
    Returns "FINISHED" when successful
    """
    prim = format.RenderPrimitve()
    prim.header.bone_rig_resource_index = collection.prim_collection_properties.bone_rig_resource_index

    prim.header.object_table = []
    
    mesh_obs = [o for o in collection.all_objects if o.type == 'MESH']
    for ob in mesh_obs:
        if not ob.name.startswith("BoxCollider") and \
            not ob.name.startswith("CapsuleCollider") and \
            not ob.name.startswith("SphereCollider") and \
            not ob.name.startswith("ConvexMeshCollider") and \
            not ob.name.startswith("TriangleMeshCollider"):
            prim_obj = format.PrimMesh()
            mesh_backup = ob.data.copy()
            triangulate_object(ob)

            material_id = ob.data.prim_properties.material_id
            prim_obj.prim_object.material_id = material_id

            if ob.data.prim_properties.axis_lock[0]:
                prim_obj.prim_object.properties.setXaxisLocked()

            if ob.data.prim_properties.axis_lock[1]:
                prim_obj.prim_object.properties.setYaxisLocked()

            if ob.data.prim_properties.axis_lock[2]:
                prim_obj.prim_object.properties.setZaxisLocked()

            if ob.data.prim_properties.no_physics:
                prim_obj.prim_object.properties.setNoPhysics()

            lod = bitArrToInt(ob.data.prim_properties.lod)
            prim_obj.prim_object.lodmask = lod

            prim_obj.sub_mesh = save_prim_sub_mesh(ob, hitbox_slider[0])

            if prim_obj.sub_mesh is None:
                return {'CANCELLED'}
            # Set subMesh properties
            if len(prim_obj.sub_mesh.vertexBuffer.vertices) > 100000:
                prim_obj.prim_object.properties.setHighResolution()

            if force_highres_flag:
                prim_obj.prim_object.properties.setHighResolution()

            if ob.data.prim_properties.use_mesh_color:
                prim_obj.sub_mesh.prim_object.properties.setColor1()

            prim_obj.sub_mesh.prim_object.variant_id = ob.data.prim_properties.variant_id
            prim_obj.prim_object.zbias = ob.data.prim_properties.z_bias
            prim_obj.prim_object.zoffset = ob.data.prim_properties.z_offset
            if ob.data.prim_properties.use_mesh_color:
                prim_obj.sub_mesh.prim_object.color1[0] = round(ob.data.prim_properties.mesh_color[0] * 255)
                prim_obj.sub_mesh.prim_object.color1[1] = round(ob.data.prim_properties.mesh_color[1] * 255)
                prim_obj.sub_mesh.prim_object.color1[2] = round(ob.data.prim_properties.mesh_color[2] * 255)
                prim_obj.sub_mesh.prim_object.color1[3] = round(ob.data.prim_properties.mesh_color[3] * 255)

            prim.header.object_table.append(prim_obj)
            ob.data = mesh_backup

    export_file = os.fsencode(filepath)
    if os.path.exists(export_file):
        os.remove(export_file)
    bre = io_binary.BinaryReader(open(export_file, 'wb'))
    prim.write(bre)
    bre.close()
    
    # Only export to ALOC if data and collision types are both not set to NONE
    physics_data_type = int(collection.prim_collection_properties.physics_data_type)
    physics_collision_type = int(collection.prim_collection_properties.physics_collision_type)
    if physics_data_type > 0 and physics_collision_type > 0:
        #print(physics_data_type, physics_collision_type)
        aloc = aloc_format.Physics()
        collision_settings = aloc_format.PhysicsCollisionSettings()
        collision_settings.data_type = physics_data_type
        collision_settings.collider_type = physics_collision_type
        aloc.set_collision_settings(collision_settings)
        for ob in mesh_obs:
            if ob.name.startswith("ConvexMeshCollider"):
                vertices, indices = get_vertices_and_indices(ob)
                aloc.add_convex_mesh(vertices, indices, int(ob.data.prim_physics_properties.collision_layer_type))
                #print("convex mesh!")
                #print(vertices)
                #print(indices)
                del vertices
                del indices
            if ob.name.startswith("TriangleMeshCollider"):
                vertices, indices = get_vertices_and_indices(ob)
                aloc.add_triangle_mesh(vertices, indices, int(ob.data.prim_physics_properties.collision_layer_type))
                #print("triangular mesh!")
                #print(vertices)
                #print(indices)
                del vertices
                del indices
            if ob.name.startswith("BoxCollider"):
                #print("box", ob.dimensions, ob.data.prim_physics_properties.collision_layer_type, ob.matrix_world.to_translation(), ob.matrix_world.to_quaternion())
                aloc.add_primitive_box(list(ob.dimensions / 2), int(ob.data.prim_physics_properties.collision_layer_type), list(ob.matrix_world.to_translation())[:3], list(ob.matrix_world.to_quaternion()))
            elif ob.name.startswith("CapsuleCollider"):
                radius = (ob.dimensions[0] + ob.dimensions[1]) / 4
                length = ob.dimensions[2]
                #print("cap", radius, length, ob.matrix_world.to_translation(), ob.matrix_world.to_quaternion())
                aloc.add_primitive_capsule(radius, length, int(ob.data.prim_physics_properties.collision_layer_type), list(ob.matrix_world.to_translation())[:3], list(ob.matrix_world.to_quaternion()))
            elif ob.name.startswith("SphereCollider"):
                radius = (ob.dimensions[0] + ob.dimensions[1]) / 4
                #print("sph", radius, int(ob.data.prim_physics_properties.collision_layer_type), ob.matrix_world.to_translation(), ob.matrix_world.to_quaternion())
                aloc.add_primitive_sphere(radius, int(ob.data.prim_physics_properties.collision_layer_type), list(ob.matrix_world.to_translation())[:3], list(ob.matrix_world.to_quaternion()))
        aloc.write(export_file + b".aloc")
        
    return {'FINISHED'}


def save_prim_sub_mesh(blender_obj, max_tris_per_chunk):
    """
    Export a blender mesh to a PrimSubMesh
    Returns a PrimSubMesh
    """
    if len(blender_obj.modifiers) == 0:
        mesh = blender_obj.to_mesh()
    else:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh_owner = blender_obj.evaluated_get(depsgraph)
        mesh = mesh_owner.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    prim_mesh = format.PrimSubMesh()

    if blender_obj.data.uv_layers:
        uvmap = blender_obj.data.uv_layers.active.name
        mesh.calc_tangents(uvmap=uvmap)
    else:
        BlenderUI.MessageBox("\"%s\" is missing a UV map" % mesh.name, "Exporting error", 'ERROR')
        return None

    locs = get_positions(mesh, blender_obj.matrix_world.copy())

    dot_fields = [('vertex_index', np.uint32)]
    dot_fields += [('nx', np.float32), ('ny', np.float32), ('nz', np.float32)]
    dot_fields += [('tx', np.float32), ('ty', np.float32), ('tz', np.float32), ('tw', np.float32)]
    dot_fields += [('bx', np.float32), ('by', np.float32), ('bz', np.float32), ('bw', np.float32)]
    for uv_i in range(len(mesh.uv_layers)):
        dot_fields += [('uv%dx' % uv_i, np.float32), ('uv%dy' % uv_i, np.float32)]
    dot_fields += [
        ('colorR', np.float32),
        ('colorG', np.float32),
        ('colorB', np.float32),
        ('colorA', np.float32),
    ]

    dots = np.empty(len(mesh.loops), dtype=np.dtype(dot_fields))

    vidxs = np.empty(len(mesh.loops))
    mesh.loops.foreach_get('vertex_index', vidxs)
    dots['vertex_index'] = vidxs
    del vidxs

    normals = get_normals(mesh)
    dots['nx'] = normals[:, 0]
    dots['ny'] = normals[:, 1]
    dots['nz'] = normals[:, 2]
    del normals

    tangents = get_tangents(mesh)
    dots['tx'] = tangents[:, 0]
    dots['ty'] = tangents[:, 1]
    dots['tz'] = tangents[:, 2]
    dots['tw'] = tangents[:, 3]
    del tangents

    bitangents = get_bitangents(mesh)
    dots['bx'] = bitangents[:, 0]
    dots['by'] = bitangents[:, 1]
    dots['bz'] = bitangents[:, 2]
    dots['bw'] = bitangents[:, 3]
    del bitangents

    for uv_i in range(len(mesh.uv_layers)):
        uvs = get_uvs(mesh, uv_i)
        dots['uv%dx' % uv_i] = uvs[:, 0]
        dots['uv%dy' % uv_i] = uvs[:, 1]
        del uvs

    if len(mesh.vertex_colors) > 0:
        colors = get_colors(mesh, 0)
        dots['colorR'] = colors[:, 0]
        dots['colorG'] = colors[:, 1]
        dots['colorB'] = colors[:, 2]
        dots['colorA'] = colors[:, 3]
        del colors
    else:
        # TODO: look into converting this to color1
        colors = np.full(len(mesh.loops) * 4, 0xFF, dtype=np.float32)
        colors = colors.reshape(len(mesh.loops), 4)
        dots['colorR'] = colors[:, 0]
        dots['colorG'] = colors[:, 1]
        dots['colorB'] = colors[:, 2]
        dots['colorA'] = colors[:, 3]

    # Calculate triangles and sort them into primitives.
    mesh.calc_loop_triangles()
    loop_indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.uint32)
    mesh.loop_triangles.foreach_get('loops', loop_indices)

    prim_dots = dots[loop_indices]
    prim_dots, prim_mesh.indices = np.unique(prim_dots, return_inverse=True)
    prim_mesh.indices = prim_mesh.indices.tolist()
    prim_mesh.vertexBuffer.vertices = [0] * len(prim_dots)

    blender_idxs = prim_dots['vertex_index']

    positions = np.empty((len(prim_dots), 4), dtype=np.float32)
    positions[:, 0] = locs[blender_idxs, 0]
    positions[:, 1] = locs[blender_idxs, 1]
    positions[:, 2] = locs[blender_idxs, 2]
    positions[:, 3] = locs[blender_idxs, 3]

    normals = np.empty((len(prim_dots), 4), dtype=np.float32)
    normals[:, 0] = prim_dots['nx']
    normals[:, 1] = prim_dots['ny']
    normals[:, 2] = prim_dots['nz']
    normals[:, 3] = 1 / 255

    tangents = np.empty((len(prim_dots), 4), dtype=np.float32)
    tangents[:, 0] = prim_dots['tx']
    tangents[:, 1] = prim_dots['ty']
    tangents[:, 2] = prim_dots['tz']
    tangents[:, 3] = 1 / 255

    bitangents = np.empty((len(prim_dots), 4), dtype=np.float32)
    bitangents[:, 0] = prim_dots['bx']
    bitangents[:, 1] = prim_dots['by']
    bitangents[:, 2] = prim_dots['bz']
    bitangents[:, 3] = 1 / 255

    uvs = np.empty((len(mesh.uv_layers), len(prim_dots), 2), dtype=np.float32)
    for tex_coord_i in range(len(mesh.uv_layers)):
        uvs[tex_coord_i, :, 0] = prim_dots['uv%dx' % tex_coord_i]
        uvs[tex_coord_i, :, 1] = prim_dots['uv%dy' % tex_coord_i]

    colors = np.empty((len(prim_dots), 4), dtype=np.float32)
    colors[:, 0] = prim_dots['colorR']
    colors[:, 1] = prim_dots['colorG']
    colors[:, 2] = prim_dots['colorB']
    colors[:, 3] = prim_dots['colorA']

    for i, vertex in enumerate(prim_mesh.vertexBuffer.vertices):
        vertex = format.Vertex()
        vertex.position = positions[i]
        vertex.normal = normals[i]
        vertex.tangent = tangents[i]
        vertex.bitangent = bitangents[i]
        for tex_coord_i in range(len(mesh.uv_layers)):
            vertex.uv[tex_coord_i] = uvs[tex_coord_i, i]
        vertex.color = (colors[i] * 255).astype("uint8").tolist()
        prim_mesh.vertexBuffer.vertices[i] = vertex
    
    prim_mesh.collision.tri_per_chunk = max_tris_per_chunk
    save_prim_hitboxes(mesh, prim_mesh)

    # automatic collision bounding box generation start
    '''
    triangles = []
    for i in range(int(len(prim_mesh.indices) / 3)):
        triangles.append([
            prim_mesh.vertexBuffer.vertices[prim_mesh.indices[i*3]],
            prim_mesh.vertexBuffer.vertices[prim_mesh.indices[i*3+1]],
            prim_mesh.vertexBuffer.vertices[prim_mesh.indices[i*3+2]]
        ])
    bbox = prim_mesh.calc_bb()
    bbox_x = bbox[1][0] - bbox[0][0]
    bbox_y = bbox[1][1] - bbox[0][1]
    bbox_z = bbox[1][2] - bbox[0][2]
    if bbox_x > bbox_y and bbox_x > bbox_z:
        triangles = sorted(triangles, key=cmp_to_key(compare_x_axis))
    elif bbox_y > bbox_z:
        triangles = sorted(triangles, key=cmp_to_key(compare_y_axis))
    else:
        triangles = sorted(triangles, key=cmp_to_key(compare_z_axis))
    coli_bb_max = [-sys.float_info.max] * 3
    coli_bb_min = [sys.float_info.max] * 3
    count = 0
    count2 = 0
    for triangle in reversed(triangles):
        for t in range(3):
            for axis in range(3):
                if triangle[t].position[axis] > coli_bb_max[axis]:
                    coli_bb_max[axis] = triangle[t].position[axis]
                if triangle[t].position[axis] < coli_bb_min[axis]:
                    coli_bb_min[axis] = triangle[t].position[axis]
        count += 1
        if count == max_tris_per_chunk:
            entry = format.BoxColiEntry()
            coli_bb_min[0] = int(((coli_bb_min[0] - bbox[0][0]) * 255) / (bbox_x))
            coli_bb_min[1] = int(((coli_bb_min[1] - bbox[0][1]) * 255) / (bbox_y))
            coli_bb_min[2] = int(((coli_bb_min[2] - bbox[0][2]) * 255) / (bbox_z))
            coli_bb_max[0] = int(((coli_bb_max[0] - bbox[0][0]) * 255) / (bbox_x))
            coli_bb_max[1] = int(((coli_bb_max[1] - bbox[0][1]) * 255) / (bbox_y))
            coli_bb_max[2] = int(((coli_bb_max[2] - bbox[0][2]) * 255) / (bbox_z))
            entry.min = coli_bb_min
            entry.max = coli_bb_max
            prim_mesh.collision.box_entries.append(entry)
            count = 0
            count2 += 1
            coli_bb_max = [-sys.float_info.max] * 3
            coli_bb_min = [sys.float_info.max] * 3
    if count % max_tris_per_chunk != 0:
        entry = format.BoxColiEntry()
        coli_bb_min[0] = int(((coli_bb_min[0] - bbox[0][0]) * 255) / (bbox_x))
        coli_bb_min[1] = int(((coli_bb_min[1] - bbox[0][1]) * 255) / (bbox_y))
        coli_bb_min[2] = int(((coli_bb_min[2] - bbox[0][2]) * 255) / (bbox_z))
        coli_bb_max[0] = int(((coli_bb_max[0] - bbox[0][0]) * 255) / (bbox_x))
        coli_bb_max[1] = int(((coli_bb_max[1] - bbox[0][1]) * 255) / (bbox_y))
        coli_bb_max[2] = int(((coli_bb_max[2] - bbox[0][2]) * 255) / (bbox_z))
        entry.min = coli_bb_min
        entry.max = coli_bb_max
        prim_mesh.collision.box_entries.append(entry)
        count = 0
        count2 += 1
        coli_bb_max = [-sys.float_info.max] * 3
        coli_bb_min = [sys.float_info.max] * 3
    '''
    # automatic collision bounding box generation end

    return prim_mesh


def get_positions(mesh, matrix):
    # read the vertex locations
    locs = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    source = mesh.vertices

    for vert in source:
        vert.co = matrix @ vert.co

    source.foreach_get('co', locs)
    locs = locs.reshape(len(mesh.vertices), 3)
    locs = np.c_[locs, np.ones(len(mesh.vertices), dtype=int)]

    return locs


def get_normals(mesh):
    """Get normal for each loop."""
    normals = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.calc_normals_split()
    mesh.loops.foreach_get('normal', normals)

    normals = normals.reshape(len(mesh.loops), 3)

    for ns in normals:
        is_zero = ~ns.any()
        ns[is_zero, 2] = 1

    return normals


def get_tangents(mesh):
    """Get an array of the tangent for each loop."""
    tangents = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.loops.foreach_get('tangent', tangents)
    tangents = tangents.reshape(len(mesh.loops), 3)
    tangents = np.c_[tangents, np.ones(len(mesh.loops), dtype=int)]

    return tangents


def get_bitangents(mesh):
    """Get an array of the tangent for each loop."""
    bitangents = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.loops.foreach_get('bitangent', bitangents)
    bitangents = bitangents.reshape(len(mesh.loops), 3)
    bitangents = np.c_[bitangents, np.ones(len(mesh.loops), dtype=int)]

    return bitangents


def get_uvs(mesh, uv_i):
    layer = mesh.uv_layers[uv_i]
    uvs = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    layer.data.foreach_get('uv', uvs)
    uvs = uvs.reshape(len(mesh.loops), 2)

    # u,v -> u,1-v
    uvs[:, 1] *= -1
    uvs[:, 1] += 1

    return uvs


def get_colors(mesh, color_i):
    colors = np.empty(len(mesh.loops) * 4, dtype=np.float32)
    layer = mesh.vertex_colors[color_i]
    mesh.color_attributes[layer.name].data.foreach_get('color', colors)
    colors = colors.reshape(len(mesh.loops), 4)
    return colors


def bitArrToInt(arr):
    lod_str = ""
    for bit in arr:
        if bit:
            lod_str = "1" + lod_str
        else:
            lod_str = "0" + lod_str
    return int(lod_str, 2)


def triangulate_object(obj):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)

    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    bm.to_mesh(me)
    bm.free()

def save_prim_hitboxes(bl_mesh, prim_sub_mesh):
    bb_max = [-sys.float_info.max] * 3
    bb_min = [sys.float_info.max] * 3
    for vert in bl_mesh.vertices:
        for axis in range(3):
            if bb_max[axis] < vert.co[axis]:
                bb_max[axis] = vert.co[axis]
            if bb_min[axis] > vert.co[axis]:
                bb_min[axis] = vert.co[axis]
    triangles = np.array(bl_mesh.loop_triangles)
    num_chunks = len(triangles) / prim_sub_mesh.collision.tri_per_chunk
    if len(triangles) % prim_sub_mesh.collision.tri_per_chunk:
        num_chunks += 1
    chunks = np.array_split(triangles, num_chunks)
    for chunk in chunks:
        h_max = [-sys.float_info.max] * 3
        h_min = [sys.float_info.max] * 3
        for triangle in chunk:
            for vert in triangle.vertices:
                vert_pos = bl_mesh.vertices[vert].co
                for axis in range(3):
                    if h_max[axis] < vert_pos[axis]:
                        h_max[axis] = vert_pos[axis]
                    if h_min[axis] > vert_pos[axis]:
                        h_min[axis] = vert_pos[axis]
        bb_x = (bb_max[0] - bb_min[0])
        bb_y = (bb_max[1] - bb_min[1])
        bb_z = (bb_max[2] - bb_min[2])
        h_min[0] = 0 if bb_x == 0 else int(round(((h_min[0] - bb_min[0]) / bb_x) * 255))
        h_min[1] = 0 if bb_y == 0 else int(round(((h_min[1] - bb_min[1]) / bb_y) * 255))
        h_min[2] = 0 if bb_z == 0 else int(round(((h_min[2] - bb_min[2]) / bb_z) * 255))
        h_max[0] = 0 if bb_x == 0 else int(round(((h_max[0] - bb_min[0]) / bb_x) * 255))
        h_max[1] = 0 if bb_y == 0 else int(round(((h_max[1] - bb_min[1]) / bb_y) * 255))
        h_max[2] = 0 if bb_z == 0 else int(round(((h_max[2] - bb_min[2]) / bb_z) * 255))
        entry = format.BoxColiEntry()
        entry.min = h_min
        entry.max = h_max
        prim_sub_mesh.collision.box_entries.append(entry)

def compare_x_axis(a, b):
    max_a = np.max([a[0].position[0], a[1].position[0], a[2].position[0]])
    max_b = np.max([b[0].position[0], b[1].position[0], b[2].position[0]])
    if (max_a > max_b):
        return 1
    elif (max_a < max_b):
        return -1
    else:
        return 0

def compare_y_axis(a, b):
    max_a = np.max([a[0].position[1], a[1].position[1], a[2].position[1]])
    max_b = np.max([b[0].position[1], b[1].position[1], b[2].position[1]])
    if (max_a > max_b):
        return 1
    elif (max_a < max_b):
        return -1
    else:
        return 0

def compare_z_axis(a, b):
    max_a = np.max([a[0].position[2], a[1].position[2], a[2].position[2]])
    max_b = np.max([b[0].position[2], b[1].position[2], b[2].position[2]])
    if (max_a > max_b):
        return 1
    elif (max_a < max_b):
        return -1
    else:
        return 0

def get_vertices_and_indices(blender_obj):
    if len(blender_obj.modifiers) == 0:
        mesh = blender_obj.to_mesh()
    else:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh_owner = blender_obj.evaluated_get(depsgraph)
        mesh = mesh_owner.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

    locs = get_positions(mesh, blender_obj.matrix_world.copy())

    dot_fields = [('vertex_index', np.uint32)]

    dots = np.empty(len(mesh.loops), dtype=np.dtype(dot_fields))

    vidxs = np.empty(len(mesh.loops))
    mesh.loops.foreach_get('vertex_index', vidxs)
    dots['vertex_index'] = vidxs
    del vidxs

    # Calculate triangles and sort them into primitives.
    mesh.calc_loop_triangles()
    loop_indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.uint32)
    mesh.loop_triangles.foreach_get('loops', loop_indices)

    prim_dots = dots[loop_indices]
    prim_dots, indices = np.unique(prim_dots, return_inverse=True)
    indices = indices.tolist()

    blender_idxs = prim_dots['vertex_index']
    vertices = np.empty((len(prim_dots), 3), dtype=np.float32)
    vertices[:, 0] = locs[blender_idxs, 0]
    vertices[:, 1] = locs[blender_idxs, 1]
    vertices[:, 2] = locs[blender_idxs, 2]
    vertices = vertices.tolist()
    vertices = [i for v in vertices for i in v]
    
    return vertices, indices