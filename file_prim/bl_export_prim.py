import os
import bpy
import bmesh
import numpy as np
import mathutils as mu
from functools import cmp_to_key
import copy
import sys
import hashlib
import json
import copy

from . import format
from .. import io_binary
from .. import BlenderUI
from ..file_aloc import format as aloc_format
from ..file_mat import materials as mat_materials


def save_prim(
    selected_collection,
    filepath: str,
    hitbox_slider: int,
    force_highres_flag: bool = False,
    export_scene: bool = False,
    export_all_collections: bool = False,
    collection_folders: bool = False,
    export_materials_textures: bool = False,
    export_geomentity: bool = False,
):
    """
    Export the selected collection to a prim
    Writes to the given path.
    Returns "FINISHED" when successful
    """
    export_file = os.fsencode(filepath)
    export_dir_original = export_file[: export_file.rfind(os.sep.encode())]
    bpy.context.scene.render.image_settings.file_format = "TARGA"
    collections = []
    material_jsons = mat_materials.Materials()
    hash_list_entries = {}

    if export_all_collections:
        for collection in bpy.data.scenes[0].collection.children:
            collections.append(collection)
    else:
        collections.append(selected_collection)

    for collection in collections:
        prim = format.RenderPrimitive()
        prim.header.bone_rig_resource_index = (
            collection.prim_collection_properties.bone_rig_resource_index
        )

        prim.header.object_table = []

        materials = {}

        export_dir = export_dir_original
        collection_name = collection.name.replace(".", "_")
        if export_scene:
            if collection_folders:
                export_dir += os.sep.encode() + collection_name.encode()
                if not os.path.exists(export_dir):
                    os.system('mkdir "' + export_dir.decode() + '"')
        mesh_obs = [o for o in collection.all_objects if o.type == "MESH"]
        for ob in mesh_obs:
            if (
                not ob.name.startswith("BoxCollider")
                and not ob.name.startswith("CapsuleCollider")
                and not ob.name.startswith("SphereCollider")
                and not ob.name.startswith("ConvexMeshCollider")
                and not ob.name.startswith("TriangleMeshCollider")
            ):
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

                prim_obj.sub_mesh, material_id = save_prim_sub_mesh(
                    collection_name,
                    ob,
                    hitbox_slider[0],
                    export_dir,
                    material_id,
                    export_materials_textures,
                    materials,
                    material_jsons,
                    hash_list_entries,
                    export_scene,
                )
                if material_id != -1:
                    prim_obj.prim_object.material_id = material_id

                if prim_obj.sub_mesh is None:
                    return {"CANCELLED"}
                # Set subMesh properties
                if len(prim_obj.sub_mesh.vertexBuffer.vertices) > 100000:
                    prim_obj.prim_object.properties.setHighResolution()

                if force_highres_flag:
                    prim_obj.prim_object.properties.setHighResolution()

                if ob.data.prim_properties.use_mesh_color:
                    prim_obj.sub_mesh.prim_object.properties.setColor1()

                prim_obj.sub_mesh.prim_object.variant_id = (
                    ob.data.prim_properties.variant_id
                )
                prim_obj.prim_object.zbias = ob.data.prim_properties.z_bias
                prim_obj.prim_object.zoffset = ob.data.prim_properties.z_offset
                if ob.data.prim_properties.use_mesh_color:
                    prim_obj.sub_mesh.prim_object.color1[0] = round(
                        ob.data.prim_properties.mesh_color[0] * 255
                    )
                    prim_obj.sub_mesh.prim_object.color1[1] = round(
                        ob.data.prim_properties.mesh_color[1] * 255
                    )
                    prim_obj.sub_mesh.prim_object.color1[2] = round(
                        ob.data.prim_properties.mesh_color[2] * 255
                    )
                    prim_obj.sub_mesh.prim_object.color1[3] = round(
                        ob.data.prim_properties.mesh_color[3] * 255
                    )

                prim.header.object_table.append(prim_obj)
                ob.data = mesh_backup

        if export_scene:
            geom_ioi_path = (
                "[assembly:/_pro/environment/geometry/"
                + collection_name
                + "/"
                + collection_name
                + ".prim].pc_entitytype"
            )
            geom_ioi_path, geom_ioi_hash = get_ioi_path_and_hash(geom_ioi_path)
            # print("IOI Hash GEOMENTITY:", geom_ioi_hash)
            # print("IOI Path GEOMENTITY:", geom_ioi_path)
            hash_list_entry_key = geom_ioi_hash + ".TEMP"
            if hash_list_entry_key not in hash_list_entries:
                hash_list_entries[hash_list_entry_key] = geom_ioi_path
            prim_ioi_path = (
                "[assembly:/_pro/environment/materials/"
                + collection_name
                + "/"
                + collection_name
                + ".prim].pc_prim"
            )
            prim_ioi_path, prim_ioi_hash = get_ioi_path_and_hash(prim_ioi_path)
            # print("IOI Hash PRIM:", prim_ioi_hash)
            # print("IOI Path PRIM:", prim_ioi_path)
            hash_list_entry_key = prim_ioi_hash + ".PRIM"
            if hash_list_entry_key not in hash_list_entries:
                hash_list_entries[hash_list_entry_key] = prim_ioi_path
            aloc_ioi_path = (
                "[assembly:/_pro/environment/materials/"
                + collection_name
                + "/"
                + collection_name
                + ".prim].pc_coll"
            )
            aloc_ioi_path, aloc_ioi_hash = get_ioi_path_and_hash(aloc_ioi_path)
            # print("IOI Hash ALOC:", aloc_ioi_hash)
            # print("IOI Path ALOC:", aloc_ioi_path)
            hash_list_entry_key = aloc_ioi_hash + ".ALOC"
            if hash_list_entry_key not in hash_list_entries:
                hash_list_entries[hash_list_entry_key] = aloc_ioi_path

        if export_scene:
            prim_export_path = (
                export_dir + os.sep.encode() + prim_ioi_hash.encode() + b".prim"
            )
        else:
            prim_export_path = os.fsencode(filepath)

        if os.path.exists(prim_export_path):
            os.remove(prim_export_path)
        bre = io_binary.BinaryReader(open(prim_export_path, "wb"))
        prim.write(bre)
        bre.close()

        if export_scene:
            write_prim_meta(prim_export_path + b".meta.json", materials)

            write_aloc = False
            # Only export to ALOC if data and collision types are both not set to NONE
            physics_data_type = int(
                collection.prim_collection_properties.physics_data_type
            )
            physics_collision_type = int(
                collection.prim_collection_properties.physics_collision_type
            )
            if physics_data_type > 0 and physics_collision_type > 0:
                # print(physics_data_type, physics_collision_type)
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
                        export_dir + os.sep.encode() + aloc_ioi_hash.encode() + b".aloc"
                    )

            if not write_aloc:
                aloc_ioi_path = ""

            if export_geomentity:
                geom_export_path = (
                    export_dir
                    + os.sep.encode()
                    + geom_ioi_hash.encode()
                    + b".entity.json"
                )
                write_geomentity(
                    collection,
                    geom_export_path,
                    geom_ioi_hash,
                    prim_ioi_path,
                    aloc_ioi_path,
                )

    if len(hash_list_entries) > 0:
        hash_list_path = export_dir + os.sep.encode() + b"hashlist.txt"
        output = ""
        for entry in hash_list_entries:
            output += entry + "," + hash_list_entries[entry] + "\n"
        with open(hash_list_path, "w", encoding="utf-8") as f:
            f.write(output)

    return {"FINISHED"}


def save_prim_sub_mesh(
    collection_name,
    blender_obj,
    max_tris_per_chunk,
    export_dir,
    material_id,
    export_materials_textures,
    materials,
    material_jsons,
    hash_list_entries,
    export_scene,
):
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
        BlenderUI.MessageBox(
            '"%s" is missing a UV map' % mesh.name, "Exporting error", "ERROR"
        )
        return None

    locs = get_positions(mesh, blender_obj.matrix_world.copy())

    dot_fields = [("vertex_index", np.uint32)]
    dot_fields += [("nx", np.float32), ("ny", np.float32), ("nz", np.float32)]
    dot_fields += [
        ("tx", np.float32),
        ("ty", np.float32),
        ("tz", np.float32),
        ("tw", np.float32),
    ]
    dot_fields += [
        ("bx", np.float32),
        ("by", np.float32),
        ("bz", np.float32),
        ("bw", np.float32),
    ]
    for uv_i in range(len(mesh.uv_layers)):
        dot_fields += [("uv%dx" % uv_i, np.float32), ("uv%dy" % uv_i, np.float32)]
    dot_fields += [
        ("colorR", np.float32),
        ("colorG", np.float32),
        ("colorB", np.float32),
        ("colorA", np.float32),
    ]

    dots = np.empty(len(mesh.loops), dtype=np.dtype(dot_fields))

    vidxs = np.empty(len(mesh.loops))
    mesh.loops.foreach_get("vertex_index", vidxs)
    dots["vertex_index"] = vidxs
    del vidxs

    normals = get_normals(mesh)
    dots["nx"] = normals[:, 0]
    dots["ny"] = normals[:, 1]
    dots["nz"] = normals[:, 2]
    del normals

    tangents = get_tangents(mesh)
    dots["tx"] = tangents[:, 0]
    dots["ty"] = tangents[:, 1]
    dots["tz"] = tangents[:, 2]
    dots["tw"] = tangents[:, 3]
    del tangents

    bitangents = get_bitangents(mesh)
    dots["bx"] = bitangents[:, 0]
    dots["by"] = bitangents[:, 1]
    dots["bz"] = bitangents[:, 2]
    dots["bw"] = bitangents[:, 3]
    del bitangents

    for uv_i in range(len(mesh.uv_layers)):
        uvs = get_uvs(mesh, uv_i)
        dots["uv%dx" % uv_i] = uvs[:, 0]
        dots["uv%dy" % uv_i] = uvs[:, 1]
        del uvs

    if len(mesh.vertex_colors) > 0:
        colors = get_colors(mesh, 0)
        dots["colorR"] = colors[:, 0]
        dots["colorG"] = colors[:, 1]
        dots["colorB"] = colors[:, 2]
        dots["colorA"] = colors[:, 3]
        del colors
    else:
        # TODO: look into converting this to color1
        colors = np.full(len(mesh.loops) * 4, 0xFF, dtype=np.float32)
        colors = colors.reshape(len(mesh.loops), 4)
        dots["colorR"] = colors[:, 0]
        dots["colorG"] = colors[:, 1]
        dots["colorB"] = colors[:, 2]
        dots["colorA"] = colors[:, 3]

    # Calculate triangles and sort them into primitives.
    mesh.calc_loop_triangles()
    loop_indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.uint32)
    mesh.loop_triangles.foreach_get("loops", loop_indices)

    prim_dots = dots[loop_indices]
    prim_dots, prim_mesh.indices = np.unique(prim_dots, return_inverse=True)
    prim_mesh.indices = prim_mesh.indices.tolist()
    prim_mesh.vertexBuffer.vertices = [0] * len(prim_dots)

    blender_idxs = prim_dots["vertex_index"]

    positions = np.empty((len(prim_dots), 4), dtype=np.float32)
    positions[:, 0] = locs[blender_idxs, 0]
    positions[:, 1] = locs[blender_idxs, 1]
    positions[:, 2] = locs[blender_idxs, 2]
    positions[:, 3] = locs[blender_idxs, 3]

    normals = np.empty((len(prim_dots), 4), dtype=np.float32)
    normals[:, 0] = prim_dots["nx"]
    normals[:, 1] = prim_dots["ny"]
    normals[:, 2] = prim_dots["nz"]
    normals[:, 3] = 1 / 255

    tangents = np.empty((len(prim_dots), 4), dtype=np.float32)
    tangents[:, 0] = prim_dots["tx"]
    tangents[:, 1] = prim_dots["ty"]
    tangents[:, 2] = prim_dots["tz"]
    tangents[:, 3] = 1 / 255

    bitangents = np.empty((len(prim_dots), 4), dtype=np.float32)
    bitangents[:, 0] = prim_dots["bx"]
    bitangents[:, 1] = prim_dots["by"]
    bitangents[:, 2] = prim_dots["bz"]
    bitangents[:, 3] = 1 / 255

    uvs = np.empty((len(mesh.uv_layers), len(prim_dots), 2), dtype=np.float32)
    for tex_coord_i in range(len(mesh.uv_layers)):
        uvs[tex_coord_i, :, 0] = prim_dots["uv%dx" % tex_coord_i]
        uvs[tex_coord_i, :, 1] = prim_dots["uv%dy" % tex_coord_i]

    colors = np.empty((len(prim_dots), 4), dtype=np.float32)
    colors[:, 0] = prim_dots["colorR"]
    colors[:, 1] = prim_dots["colorG"]
    colors[:, 2] = prim_dots["colorB"]
    colors[:, 3] = prim_dots["colorA"]

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

    if export_scene:
        if export_materials_textures:
            material_id = -1
            first_material_found = False
            for slot in blender_obj.material_slots:
                if slot.material != None:
                    for n in slot.material.node_tree.nodes:
                        if n.type == "BSDF_PRINCIPLED":
                            if not first_material_found:
                                if slot.material.name in materials:
                                    material_id = materials[slot.material.name]["index"]
                                    first_material_found = True
                                else:
                                    material = {}
                                    material[
                                        "material"
                                    ] = (
                                        slot.material.prim_material_properties.prim_materials
                                    )
                                    material[
                                        "floats"
                                    ] = (
                                        slot.material.prim_material_properties.material_float_values
                                    )
                                    material[
                                        "colors"
                                    ] = (
                                        slot.material.prim_material_properties.material_color_values
                                    )
                                    material[
                                        "ERES"
                                    ] = (
                                        slot.material.prim_material_properties.material_eres_value
                                    )
                                    material[
                                        "instance_flags"
                                    ] = (
                                        slot.material.prim_material_properties.material_instance_flags
                                    )
                                    material[
                                        "class_flags"
                                    ] = (
                                        slot.material.prim_material_properties.material_class_flags
                                    )
                                    if "Base Color" in n.inputs:
                                        for l in n.inputs["Base Color"].links:
                                            if l.from_node.type == "TEX_IMAGE":
                                                # print("Diffuse Image Texture Found:", l.from_node.image.name)
                                                ioi_path = (
                                                    "[assembly:/_pro/environment/textures/"
                                                    + collection_name
                                                    + "/"
                                                    + slot.material.name.replace(
                                                        ".", "_"
                                                    )
                                                    + ".texture?/diffuse.tex](ascolormap)"
                                                )
                                                ioi_path_text = ioi_path + ".pc_tex"
                                                ioi_path_texd = (
                                                    ioi_path + ".pc_mipblock1"
                                                )
                                                (
                                                    ioi_path_text,
                                                    ioi_hash_text,
                                                ) = get_ioi_path_and_hash(ioi_path_text)
                                                (
                                                    ioi_path_texd,
                                                    ioi_hash_texd,
                                                ) = get_ioi_path_and_hash(ioi_path_texd)
                                                material["diffuse"] = ioi_path_text
                                                # print("IOI Hash TEXT:", ioi_hash_text, ",", ioi_path_text)
                                                # print("IOI Hash TEXD:", ioi_hash_texd, ",", ioi_path_texd)
                                                hash_list_entry_key = (
                                                    ioi_hash_text + ".TEXT"
                                                )
                                                if (
                                                    hash_list_entry_key
                                                    not in hash_list_entries
                                                ):
                                                    hash_list_entries[
                                                        hash_list_entry_key
                                                    ] = ioi_path_text
                                                hash_list_entry_key = (
                                                    ioi_hash_texd + ".TEXD"
                                                )
                                                if (
                                                    hash_list_entry_key
                                                    not in hash_list_entries
                                                ):
                                                    hash_list_entries[
                                                        hash_list_entry_key
                                                    ] = ioi_path_texd
                                                texture_filename = (
                                                    ioi_hash_text
                                                    + "~"
                                                    + ioi_hash_texd
                                                    + ".texture.tga"
                                                )
                                                image_texture = bpy.data.images[
                                                    l.from_node.image.name
                                                ]
                                                if image_texture.has_data:
                                                    texture_output_path = (
                                                        export_dir
                                                        + os.sep.encode()
                                                        + texture_filename.encode()
                                                    )
                                                    image_texture.save_render(
                                                        texture_output_path
                                                    )
                                                    text_texd_scale = int(
                                                        image_texture.size[0]
                                                    ) * int(image_texture.size[1])
                                                    write_texture_meta(
                                                        texture_output_path + b".meta",
                                                        text_texd_scale,
                                                        b"\x49",
                                                    )
                                    if "Normal" in n.inputs:
                                        for l in n.inputs["Normal"].links:
                                            if l.from_node.type == "NORMAL_MAP":
                                                if "Color" in l.from_node.inputs:
                                                    for ln in l.from_node.inputs[
                                                        "Color"
                                                    ].links:
                                                        if (
                                                            ln.from_node.type
                                                            == "TEX_IMAGE"
                                                        ):
                                                            # print("Normal Image Texture Found:", ln.from_node.image.name)
                                                            ioi_path = (
                                                                "[assembly:/_pro/environment/textures/"
                                                                + collection_name
                                                                + "/"
                                                                + slot.material.name.replace(
                                                                    ".", "_"
                                                                )
                                                                + ".texture?/normal.tex](asnormalmap)"
                                                            )
                                                            ioi_path_text = (
                                                                ioi_path + ".pc_tex"
                                                            )
                                                            ioi_path_texd = (
                                                                ioi_path
                                                                + ".pc_mipblock1"
                                                            )
                                                            (
                                                                ioi_path_text,
                                                                ioi_hash_text,
                                                            ) = get_ioi_path_and_hash(
                                                                ioi_path_text
                                                            )
                                                            (
                                                                ioi_path_texd,
                                                                ioi_hash_texd,
                                                            ) = get_ioi_path_and_hash(
                                                                ioi_path_texd
                                                            )
                                                            material[
                                                                "normal"
                                                            ] = ioi_path_text
                                                            # print("IOI Hash TEXT:", ioi_hash_text, ",", ioi_path_text)
                                                            # print("IOI Hash TEXD:", ioi_hash_texd, ",", ioi_path_texd)
                                                            hash_list_entry_key = (
                                                                ioi_hash_text + ".TEXT"
                                                            )
                                                            if (
                                                                hash_list_entry_key
                                                                not in hash_list_entries
                                                            ):
                                                                hash_list_entries[
                                                                    hash_list_entry_key
                                                                ] = ioi_path_text
                                                            hash_list_entry_key = (
                                                                ioi_hash_texd + ".TEXD"
                                                            )
                                                            if (
                                                                hash_list_entry_key
                                                                not in hash_list_entries
                                                            ):
                                                                hash_list_entries[
                                                                    hash_list_entry_key
                                                                ] = ioi_path_texd
                                                            texture_filename = (
                                                                ioi_hash_text
                                                                + "~"
                                                                + ioi_hash_texd
                                                                + ".texture.tga"
                                                            )
                                                            image_texture = bpy.data.images[
                                                                ln.from_node.image.name
                                                            ]
                                                            if image_texture.has_data:
                                                                texture_output_path = (
                                                                    export_dir
                                                                    + os.sep.encode()
                                                                    + texture_filename.encode()
                                                                )
                                                                image_texture.save_render(
                                                                    texture_output_path
                                                                )
                                                                text_texd_scale = int(
                                                                    image_texture.size[
                                                                        0
                                                                    ]
                                                                ) * int(
                                                                    image_texture.size[
                                                                        1
                                                                    ]
                                                                )
                                                                write_texture_meta(
                                                                    texture_output_path
                                                                    + b".meta",
                                                                    text_texd_scale,
                                                                    b"\x55",
                                                                )
                                    # specular_node = None
                                    if bpy.app.version >= (4, 0, 0):
                                        specular_node = n.inputs["Specular IOR Level"]
                                    else:
                                        specular_node = n.inputs["Specular"]
                                    if specular_node:
                                        for l in specular_node.links:
                                            if l.from_node.type == "TEX_IMAGE":
                                                # print("Specular Image Texture Found:", l.from_node.image.name)
                                                ioi_path = (
                                                    "[assembly:/_pro/environment/textures/"
                                                    + collection_name
                                                    + "/"
                                                    + slot.material.name.replace(
                                                        ".", "_"
                                                    )
                                                    + ".texture?/specular.tex](ascolormap)"
                                                )
                                                ioi_path_text = ioi_path + ".pc_tex"
                                                ioi_path_texd = (
                                                    ioi_path + ".pc_mipblock1"
                                                )
                                                (
                                                    ioi_path_text,
                                                    ioi_hash_text,
                                                ) = get_ioi_path_and_hash(ioi_path_text)
                                                (
                                                    ioi_path_texd,
                                                    ioi_hash_texd,
                                                ) = get_ioi_path_and_hash(ioi_path_texd)
                                                material["specular"] = ioi_path_text
                                                # print("IOI Hash TEXT:", ioi_hash_text, ",", ioi_path_text)
                                                # print("IOI Hash TEXD:", ioi_hash_texd, ",", ioi_path_texd)
                                                hash_list_entry_key = (
                                                    ioi_hash_text + ".TEXT"
                                                )
                                                if (
                                                    hash_list_entry_key
                                                    not in hash_list_entries
                                                ):
                                                    hash_list_entries[
                                                        hash_list_entry_key
                                                    ] = ioi_path_text
                                                hash_list_entry_key = (
                                                    ioi_hash_texd + ".TEXD"
                                                )
                                                if (
                                                    hash_list_entry_key
                                                    not in hash_list_entries
                                                ):
                                                    hash_list_entries[
                                                        hash_list_entry_key
                                                    ] = ioi_path_texd
                                                texture_filename = (
                                                    ioi_hash_text
                                                    + "~"
                                                    + ioi_hash_texd
                                                    + ".texture.tga"
                                                )
                                                image_texture = bpy.data.images[
                                                    l.from_node.image.name
                                                ]
                                                if image_texture.has_data:
                                                    # print(len(image_texture.pixels))
                                                    # print(image_texture.size[0], image_texture.size[1])
                                                    texture_output_path = (
                                                        export_dir
                                                        + os.sep.encode()
                                                        + texture_filename.encode()
                                                    )
                                                    image_texture.save_render(
                                                        texture_output_path
                                                    )
                                                    text_texd_scale = int(
                                                        image_texture.size[0]
                                                    ) * int(image_texture.size[1])
                                                    write_texture_meta(
                                                        texture_output_path + b".meta",
                                                        text_texd_scale,
                                                        b"\x5A",
                                                    )
                                    first_material_found = True
                                    ioi_path = (
                                        "[assembly:/_pro/environment/materials/"
                                        + collection_name
                                        + "/"
                                        + slot.material.name.replace(".", "_")
                                        + ".mi].pc_mi"
                                    )
                                    ioi_path_entitytype = (
                                        "[assembly:/_pro/environment/materials/"
                                        + collection_name
                                        + "/"
                                        + slot.material.name.replace(".", "_")
                                        + ".mi].pc_entitytype"
                                    )
                                    ioi_path_entityblueprint = (
                                        "[assembly:/_pro/environment/materials/"
                                        + collection_name
                                        + "/"
                                        + slot.material.name.replace(".", "_")
                                        + ".mi].pc_entityblueprint"
                                    )
                                    ioi_path, ioi_hash = get_ioi_path_and_hash(ioi_path)
                                    (
                                        ioi_path_entitytype,
                                        ioi_hash_entitytype,
                                    ) = get_ioi_path_and_hash(ioi_path_entitytype)
                                    (
                                        ioi_path_entityblueprint,
                                        ioi_hash_entityblueprint,
                                    ) = get_ioi_path_and_hash(ioi_path_entityblueprint)
                                    # print("IOI Hash Material:", ioi_hash, ",", ioi_path)
                                    material_json_output_path = (
                                        export_dir
                                        + os.sep.encode()
                                        + ioi_hash.encode()
                                        + b".material.json"
                                    )
                                    material["ioi_path"] = ioi_path
                                    material[
                                        "ioi_path_entitytype"
                                    ] = ioi_path_entitytype
                                    material[
                                        "ioi_path_entityblueprint"
                                    ] = ioi_path_entityblueprint
                                    material["ioi_hash"] = ioi_hash
                                    material[
                                        "ioi_hash_entitytype"
                                    ] = ioi_hash_entitytype
                                    material[
                                        "ioi_hash_entityblueprint"
                                    ] = ioi_hash_entityblueprint
                                    material["name"] = (
                                        slot.material.name.replace(".", "_") + ".mi"
                                    )
                                    material["index"] = len(materials)
                                    # print(material)
                                    hash_list_entry_key = ioi_hash + ".MATI"
                                    if hash_list_entry_key not in hash_list_entries:
                                        hash_list_entries[
                                            hash_list_entry_key
                                        ] = ioi_path
                                    hash_list_entry_key_entitytype = (
                                        ioi_hash_entitytype + ".MATT"
                                    )
                                    if (
                                        hash_list_entry_key_entitytype
                                        not in hash_list_entries
                                    ):
                                        hash_list_entries[
                                            hash_list_entry_key_entitytype
                                        ] = ioi_path_entitytype
                                    hash_list_entry_key_entityblueprint = (
                                        ioi_hash_entityblueprint + ".MATB"
                                    )
                                    if (
                                        hash_list_entry_key_entityblueprint
                                        not in hash_list_entries
                                    ):
                                        hash_list_entries[
                                            hash_list_entry_key_entityblueprint
                                        ] = ioi_path_entityblueprint
                                    write_material_json(
                                        material_json_output_path,
                                        material,
                                        material_jsons,
                                    )
                                    materials[slot.material.name] = material
                                    material_id = materials[slot.material.name]["index"]

    return prim_mesh, material_id


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


def get_normals(mesh):
    """Get normal for each loop."""
    normals = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    
    if bpy.app.version < (4, 1, 0):
        mesh.calc_normals_split()
    
    mesh.loops.foreach_get("normal", normals)

    normals = normals.reshape(len(mesh.loops), 3)

    for ns in normals:
        is_zero = ~ns.any()
        ns[is_zero, 2] = 1

    return normals


def get_tangents(mesh):
    """Get an array of the tangent for each loop."""
    tangents = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.loops.foreach_get("tangent", tangents)
    tangents = tangents.reshape(len(mesh.loops), 3)
    tangents = np.c_[tangents, np.ones(len(mesh.loops), dtype=int)]

    return tangents


def get_bitangents(mesh):
    """Get an array of the tangent for each loop."""
    bitangents = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.loops.foreach_get("bitangent", bitangents)
    bitangents = bitangents.reshape(len(mesh.loops), 3)
    bitangents = np.c_[bitangents, np.ones(len(mesh.loops), dtype=int)]

    return bitangents


def get_uvs(mesh, uv_i):
    layer = mesh.uv_layers[uv_i]
    uvs = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    layer.data.foreach_get("uv", uvs)
    uvs = uvs.reshape(len(mesh.loops), 2)

    # u,v -> u,1-v
    uvs[:, 1] *= -1
    uvs[:, 1] += 1

    return uvs


def get_colors(mesh, color_i):
    colors = np.empty(len(mesh.loops) * 4, dtype=np.float32)
    layer = mesh.vertex_colors[color_i]
    mesh.color_attributes[layer.name].data.foreach_get("color", colors)
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


def save_prim_hitboxes(mesh, prim_mesh):
    bb_min = np.array([sys.float_info.max] * 3)
    bb_max = np.array([-sys.float_info.max] * 3)
    for f in range(len(mesh.loop_triangles)):
        for v in range(3):
            #print(f"Triangle loop {f}: Vertex {v}: Index {mesh.loop_triangles[f].vertices[v]}")
            bb_min = np.min([bb_min, mesh.vertices[mesh.loop_triangles[f].vertices[v]].co], axis=0)
            bb_max = np.max([bb_max, mesh.vertices[mesh.loop_triangles[f].vertices[v]].co], axis=0)
    bb_diff = bb_max - bb_min
    num_chunks = int(len(mesh.loop_triangles) / prim_mesh.collision.tri_per_chunk)
    if len(mesh.loop_triangles) % prim_mesh.collision.tri_per_chunk:
        num_chunks += 1
    for n in range(num_chunks):
        #print(f"chunk: {n}")
        #print(f"faces: {n*prim_mesh.collision.tri_per_chunk} to {(n+1)*prim_mesh.collision.tri_per_chunk}")
        coli_bb_min = np.array([sys.float_info.max] * 3)
        coli_bb_max = np.array([-sys.float_info.max] * 3)
        for f in range(n*prim_mesh.collision.tri_per_chunk,(n+1)*prim_mesh.collision.tri_per_chunk):
            if f == len(mesh.loop_triangles):
                break
            for v in range(3):
                coli_bb_min = np.min([coli_bb_min, mesh.vertices[mesh.loop_triangles[f].vertices[v]].co], axis=0)
                coli_bb_max = np.max([coli_bb_max, mesh.vertices[mesh.loop_triangles[f].vertices[v]].co], axis=0)
        entry = format.BoxColiEntry()
        coli_min = (coli_bb_min - bb_min) * 255
        coli_max = (coli_bb_max - bb_min) * 255
        coli_min = [(coli_min[i] / bb_diff[i]) if bb_diff[i] != 0 else 0 for i in range(3)]
        coli_max = [(coli_max[i] / bb_diff[i]) if bb_diff[i] != 0 else 0 for i in range(3)]
        for i in range(3):
            entry.min[i] = int(round(coli_min[i]))
            entry.max[i] = int(round(coli_max[i]))
        prim_mesh.collision.box_entries.append(entry)
        #print(f"coli entry min: {entry.min}")
        #print(f"coli entry max: {entry.max}")


def compare_x_axis(a, b):
    max_a = np.max([a[0].position[0], a[1].position[0], a[2].position[0]])
    max_b = np.max([b[0].position[0], b[1].position[0], b[2].position[0]])
    if max_a > max_b:
        return 1
    elif max_a < max_b:
        return -1
    else:
        return 0


def compare_y_axis(a, b):
    max_a = np.max([a[0].position[1], a[1].position[1], a[2].position[1]])
    max_b = np.max([b[0].position[1], b[1].position[1], b[2].position[1]])
    if max_a > max_b:
        return 1
    elif max_a < max_b:
        return -1
    else:
        return 0


def compare_z_axis(a, b):
    max_a = np.max([a[0].position[2], a[1].position[2], a[2].position[2]])
    max_b = np.max([b[0].position[2], b[1].position[2], b[2].position[2]])
    if max_a > max_b:
        return 1
    elif max_a < max_b:
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


def write_texture_meta(output_path, texture_size, format):
    meta_data = b"\x00\x00\x00\x00\x48\x00\x00\x00"
    meta_data += format
    meta_data += b"\x00\x01"
    scaling = b"\x00\x00\x00\x00\x00"
    if texture_size == 32768 or texture_size == 65536:
        scaling = b"\x01\x01\x00\x00\x00"
    elif texture_size == 131072 or texture_size == 262144:
        scaling = b"\x02\x02\x00\x00\x00"
    elif texture_size == 524288 or texture_size == 1048576:
        scaling = b"\x03\x03\x00\x00\x00"
    elif texture_size == 2097152 or texture_size == 4194304:
        scaling = b"\x04\x04\x00\x00\x00"
    elif texture_size == 8388608 or texture_size == 16777216:
        scaling = b"\x05\x05\x00\x00\x00"
    meta_data += scaling
    with open(output_path, "wb") as f:
        f.write(meta_data)


def write_material_json(output_path, material, material_jsons):
    material_jsons_copy = copy.deepcopy(material_jsons)
    for t in material_jsons_copy.materials[material["material"]]["Material"][
        "Instance"
    ][0]["Binder"][0]["Texture"]:
        if "FriendlyName" in t:
            del t["FriendlyName"]
    for f in material_jsons_copy.materials[material["material"]]["Material"][
        "Instance"
    ][0]["Binder"][0]["Float Value"]:
        if "FriendlyName" in f:
            del f["FriendlyName"]
    for c in material_jsons_copy.materials[material["material"]]["Material"][
        "Instance"
    ][0]["Binder"][0]["Color"]:
        if "FriendlyName" in c:
            del c["FriendlyName"]
    # print("Writing material json for " + material["name"])
    for m in material_jsons_copy.materials:
        if m == material["material"]:
            material_json = material_jsons_copy.materials[m]
            material_json["MATI"] = material["ioi_path"]
            material_json["MATT"] = material["ioi_path_entitytype"]
            material_json["MATB"] = material["ioi_path_entityblueprint"]
            material_json["ERES"] = material["ERES"]
            material_json["Material"]["Instance"][0]["Name"] = material["name"]
            if "Texture" in material_json["Material"]["Instance"][0]["Binder"][0]:
                for t in material_json["Material"]["Instance"][0]["Binder"][0][
                    "Texture"
                ]:
                    if t["Texture Id"] == "diffuse":
                        if "diffuse" in material:
                            t["Texture Id"] = material["diffuse"]
                            print("Diffuse: " + material["diffuse"])
                        else:
                            t["Texture Id"] = ""
                    if t["Texture Id"] == "normal":
                        if "normal" in material:
                            t["Texture Id"] = material["normal"]
                        else:
                            t["Texture Id"] = ""
                    if t["Texture Id"] == "specular":
                        if "specular" in material:
                            t["Texture Id"] = material["specular"]
                        else:
                            t["Texture Id"] = ""
            for f in material["floats"]:
                if (
                    "Float Value"
                    in material_json["Material"]["Instance"][0]["Binder"][0]
                ):
                    for fv in material_json["Material"]["Instance"][0]["Binder"][0][
                        "Float Value"
                    ]:
                        if f.name == fv["Name"]:
                            fv["Value"] = f.value
            for c in material["colors"]:
                if "Color" in material_json["Material"]["Instance"][0]["Binder"][0]:
                    for cv in material_json["Material"]["Instance"][0]["Binder"][0][
                        "Color"
                    ]:
                        if c.name == cv["Name"]:
                            cv["Value"] = [c.value.r, c.value.g, c.value.b]

            # Flags section
            for flag in material["class_flags"]:
                material_json["Flags"]["Class"][flag["name"]] = (
                    True if flag["value"] == 1 else False
                )

            for flag in material["instance_flags"]:
                material_json["Flags"]["Instance"][flag["name"]] = (
                    True if flag["value"] == 1 else False
                )

            # Overrides section
            for texture_key, texture_id in material_json["Overrides"][
                "Texture"
            ].items():
                if texture_id in ["diffuse", "specular", "normal"]:
                    if texture_id in material:
                        material_json["Overrides"]["Texture"][texture_key] = material[
                            texture_id
                        ]
                    else:
                        material_json["Overrides"]["Texture"][texture_key] = ""
            for float_key in material_json["Overrides"]:
                if float_key in material["floats"]:
                    material_json["Overrides"][float_key] = material["floats"][
                        float_key
                    ].value
            for color_key, color_values in material_json["Overrides"]["Color"].items():
                if color_key in material["colors"]:
                    material_json["Overrides"]["Color"][color_key] = [
                        material["colors"][color_key].value.r,
                        material["colors"][color_key].value.g,
                        material["colors"][color_key].value.b,
                    ]

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(material_json, f, ensure_ascii=False, indent=4)


def get_ioi_path_and_hash(ioi_path):
    ioi_path = ioi_path.lower()
    ioi_hash = "00" + hashlib.md5(ioi_path.encode("utf-8")).hexdigest().upper()[2:16]
    return ioi_path, ioi_hash


def write_geomentity(
    collection, geom_export_path, geom_ioi_hash, prim_ioi_path, aloc_ioi_path
):
    geomentity_json = {
        "tempHash": geom_ioi_hash,
        "tbluHash": "EDIT!!!",
        "rootEntity": "2ed3aa8cc1e0b74f",
        "entities": {
            "2ed3aa8cc1e0b74f": {
                "parent": None,
                "name": "GeomEntity01",
                "factory": "EDIT!!!",
                "blueprint": "EDIT!!!",
                "properties": {
                    "m_mTransform": {
                        "type": "SMatrix43",
                        "value": {
                            "rotation": {"x": 0, "y": 0, "z": 0},
                            "position": {"x": 0, "y": 0, "z": 0},
                        },
                    },
                    "m_ResourceID": {
                        "type": "ZRuntimeResourceID",
                        "value": {"resource": prim_ioi_path, "flag": "5F"},
                    },
                },
            }
        },
        "propertyOverrides": [],
        "overrideDeletes": [],
        "pinConnectionOverrides": [],
        "pinConnectionOverrideDeletes": [],
        "externalScenes": [],
        "subType": "template",
        "quickEntityVersion": 3.1,
        "extraFactoryDependencies": [],
        "extraBlueprintDependencies": [],
        "comments": [],
    }
    if aloc_ioi_path != "":
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_CollisionResourceID"
        ] = {
            "type": "ZRuntimeResourceID",
            "value": {"resource": aloc_ioi_path, "flag": "5F"},
        }
    if int(collection.prim_collection_properties.physics_collision_type) == int(
        aloc_format.PhysicsCollisionType.NONE
    ):
        geomentity_json["tbluHash"] = "008130A85A690BE8"
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"][
            "factory"
        ] = "[modules:/zgeomentity.class].pc_entitytype"
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"][
            "blueprint"
        ] = "[modules:/zgeomentity.class].pc_entityblueprint"
    elif int(collection.prim_collection_properties.physics_collision_type) == int(
        aloc_format.PhysicsCollisionType.STATIC
    ):
        geomentity_json["tbluHash"] = "002E141E1B1C6EFE"
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"][
            "factory"
        ] = "[assembly:/templates/aspectdummy.aspect]([modules:/zgeomentity.class].entitytype,[modules:/zstaticphysicsaspect.class].entitytype,[modules:/zcollisionresourceshapeaspect.class].entitytype).pc_entitytype"
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"][
            "blueprint"
        ] = "[assembly:/templates/aspectdummy.aspect]([modules:/zgeomentity.class].entitytype,[modules:/zstaticphysicsaspect.class].entitytype,[modules:/zcollisionresourceshapeaspect.class].entitytype).pc_entityblueprint"
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_bRemovePhysics"
        ] = {
            "type": "bool",
            "value": collection.prim_collection_properties.m_bRemovePhysics,
        }
    elif int(collection.prim_collection_properties.physics_collision_type) == int(
        aloc_format.PhysicsCollisionType.RIGIDBODY
    ):
        geomentity_json["tbluHash"] = "00C7E348A80A6E6E"
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"][
            "factory"
        ] = "[assembly:/templates/aspectdummy.aspect]([modules:/zgeomentity.class].entitytype,[modules:/zdynamicphysicsaspect.class].entitytype,[modules:/zcollisionresourceshapeaspect.class].entitytype).pc_entitytype"
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"][
            "blueprint"
        ] = "[assembly:/templates/aspectdummy.aspect]([modules:/zgeomentity.class].entitytype,[modules:/zdynamicphysicsaspect.class].entitytype,[modules:/zcollisionresourceshapeaspect.class].entitytype).pc_entityblueprint"
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_bRemovePhysics"
        ] = {
            "type": "bool",
            "value": collection.prim_collection_properties.m_bRemovePhysics,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_bKinematic"
        ] = {
            "type": "bool",
            "value": collection.prim_collection_properties.m_bKinematic,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_bStartSleeping"
        ] = {
            "type": "bool",
            "value": collection.prim_collection_properties.m_bStartSleeping,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_bIgnoreCharacters"
        ] = {
            "type": "bool",
            "value": collection.prim_collection_properties.m_bIgnoreCharacters,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_bEnableCollision"
        ] = {
            "type": "bool",
            "value": collection.prim_collection_properties.m_bEnableCollision,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_bAllowKinematicKinematicContactNotification"
        ] = {
            "type": "bool",
            "value": collection.prim_collection_properties.m_bAllowKinematicKinematicContactNotification,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"]["m_fMass"] = {
            "type": "float32",
            "value": collection.prim_collection_properties.m_fMass,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"]["m_fFriction"] = {
            "type": "float32",
            "value": collection.prim_collection_properties.m_fFriction,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_fRestitution"
        ] = {
            "type": "float32",
            "value": collection.prim_collection_properties.m_fRestitution,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_fLinearDampening"
        ] = {
            "type": "float32",
            "value": collection.prim_collection_properties.m_fLinearDampening,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_fAngularDampening"
        ] = {
            "type": "float32",
            "value": collection.prim_collection_properties.m_fAngularDampening,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_fSleepEnergyThreshold"
        ] = {
            "type": "float32",
            "value": collection.prim_collection_properties.m_fSleepEnergyThreshold,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"]["m_ePriority"] = {
            "type": "ECollisionPriority",
            "value": collection.prim_collection_properties.m_ePriority,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"]["m_eCCD"] = {
            "type": "ECCDUsage",
            "value": collection.prim_collection_properties.m_eCCD,
        }
        geomentity_json["entities"]["2ed3aa8cc1e0b74f"]["properties"][
            "m_eCenterOfMass"
        ] = {
            "type": "ECOMUsage",
            "value": collection.prim_collection_properties.m_eCenterOfMass,
        }
    with open(geom_export_path, "w", encoding="utf-8") as f:
        json.dump(geomentity_json, f, ensure_ascii=False, indent=4)


def write_prim_meta(output_path, materials):
    meta_json = {
        "hash_value": "000D4DE6CA5229F8",
        "hash_offset": 8693330,
        "hash_size": 2147486887,
        "hash_resource_type": "PRIM",
        "hash_reference_table_size": 13,
        "hash_reference_table_dummy": 0,
        "hash_size_final": 6560,
        "hash_size_in_memory": 4294967295,
        "hash_size_in_video_memory": 4294967295,
        "hash_reference_data": [],
    }
    for i in range(len(materials)):
        for m in materials:
            if i == materials[m]["index"]:
                meta_json["hash_reference_data"].append(
                    {"hash": materials[m]["ioi_path"], "flag": "5F"}
                )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, ensure_ascii=False, indent=4)
