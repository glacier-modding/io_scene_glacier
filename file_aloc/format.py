import enum
import os
import bpy
import sys
import ctypes
import platform
import struct

from .. import io_binary


class PhysicsDataType(enum.IntEnum):
    NONE = 0
    CONVEX_MESH = 1
    TRIANGLE_MESH = 2
    CONVEX_MESH_AND_TRIANGLE_MESH = 3
    PRIMITIVE = 4
    CONVEX_MESH_AND_PRIMITIVE = 5
    TRIANGLE_MESH_AND_PRIMITIVE = 6
    KINEMATIC_LINKED = 132
    SHATTER_LINKED = 144
    KINEMATIC_LINKED_2 = 192


class PhysicsCollisionType(enum.IntEnum):
    NONE = 0
    STATIC = 1
    RIGIDBODY = 2
    SHATTER_LINKED = 16
    KINEMATIC_LINKED = 32
    BACKWARD_COMPATIBLE = 2147483647


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
    NONE = 3


class PhysicsCollisionSettings(ctypes.Structure):
    _fields_ = [
        ("data_type", ctypes.c_uint32),
        ("collider_type", ctypes.c_uint32),
    ]


class ConvexMesh:
    def __init__(self):
        self.collision_layer = 0
        self.position = [0.0, 0.0, 0.0]
        self.rotation = [0.0, 0.0, 0.0, 0.0]
        self.vertex_count = 0
        self.vertices = []
        self.has_grb_data = 0
        self.edge_count = 0
        self.polygon_count = 0
        self.polygons_vertex_count = 0


class TriangleMesh:
    def __init__(self):
        self.collision_layer = 0
        self.serial_flags = 0
        self.vertex_count = 0
        self.triangle_count = 0
        self.vertices = []
        self.triangle_data = []


class Shatter:
    def __init__(self):
        self.collision_layer = 0
        self.vertex_count = 0
        self.triangle_count = 0


class PrimitiveBox:
    def __init__(self):
        self.half_extents = [0.0, 0.0, 0.0]
        self.collision_layer = 0
        self.position = [0.0, 0.0, 0.0]
        self.rotation = [0.0, 0.0, 0.0, 0.0]


class PrimitiveCapsule:
    def __init__(self):
        self.radius = 0.0
        self.length = 0.0
        self.collision_layer = 0
        self.position = [0.0, 0.0, 0.0]
        self.rotation = [0.0, 0.0, 0.0, 0.0]


class PrimitiveSphere:
    def __init__(self):
        self.radius = 0.0
        self.collision_layer = 0
        self.position = [0.0, 0.0, 0.0]
        self.rotation = [0.0, 0.0, 0.0, 0.0]


def log(level, msg, filter_field):
    enabled = ["ERROR", "WARNING", "INFO", "DEBUG"]  # Log levels are "DEBUG", "INFO", "WARNING", "ERROR"
    if level in enabled:  # and filter_field == "0031CDA11AFD98A9":
        print("[" + str(level) + "] " + str(filter_field) + ": " + str(msg))


def read_convex_mesh(br, aloc_name):
    # Start of first convex mesh, offset = 27
    # ---- Fixed header for each Convex Mesh sizeof = 80
    # CollisionLayer, position, rotation: sizeof = 36
    convex_mesh = ConvexMesh()
    convex_mesh.collision_layer = br.readUInt()
    convex_mesh.position = br.readFloatVec(3)
    convex_mesh.rotation = br.readFloatVec(4)
    # "\0\0.?NXS.VCXM\u{13}\0\0\0\0\0\0\0ICE.CLCL\u{8}\0\0\0ICE.CVHL\u{8}\0\0\0" sizeof = 44
    br.readUByteVec(44)
    # For first mesh, current position = 103 = 0x67
    # ---- Variable data for each Convex Mesh Hull
    # sizeof = 16 + 3*vertex_count + 20*polygon_count + polygons_vertex_count + 2*edge_count + 3*vertex_count + (if (has_grb_data) then 8*edge_count else 0)
    # Example: 00C87539307C6091:
    #  vertex_count: 8
    #  has_grb_data: false
    #  edge_count: 12
    #  polygon_count: 6
    #  polygons_vertex_count: 24
    #  sizeof variable data (no grb) = 16 + 24 + 120 + 24 + 24 + 24 + 0 = 232 = 0xE8
    #  sizeof variable data (with grb) = 16 + 24 + 120 + 24 + 24 + 24 + 96 = 328 = 0x148
    #  Total size (no grb) = 103 + 232 = 0x67 + 0xE8 = 335 = 0x14F
    #  Total size (with grb) = 103 + 328 = 0x67 + 0x148 = 431 = 0x1AF
    log("DEBUG", "Starting to read variable convex mesh hull data. Current offset: " + str(br.tell()), aloc_name)
    convex_mesh.vertex_count = br.readUInt()
    log("DEBUG", "Num vertices " + str(convex_mesh.vertex_count), aloc_name)

    grb_flag_and_edge_count = br.readUInt()
    convex_mesh.has_grb_data = 0x8000 & grb_flag_and_edge_count
    log("DEBUG", "Has_grb_data " + str(convex_mesh.has_grb_data), aloc_name)

    convex_mesh.edge_count = 0x7FFF & grb_flag_and_edge_count
    log("DEBUG", "edge_count " + str(convex_mesh.edge_count), aloc_name)
    convex_mesh.polygon_count = br.readUInt()
    log("DEBUG", "polygon_count " + str(convex_mesh.polygon_count), aloc_name)
    convex_mesh.polygons_vertex_count = br.readUInt()
    log("DEBUG", "polygons_vertex_count " + str(convex_mesh.polygons_vertex_count), aloc_name)
    vertices = []
    for _vertex_index in range(convex_mesh.vertex_count):
        vertices.append(br.readFloatVec(3))
    convex_mesh.vertices = vertices
    log("DEBUG", "Finished reading vertices and metadata. Reading convex main hull data", aloc_name)

    # Unused because Blender can build the convex hull
    hull_polygon_data = 0
    for _polygon_index in range(convex_mesh.polygon_count):
        log("DEBUG", "Reading 20 characters of HullPolygonData. Current offset: " + str(br.tell()), aloc_name)
        hull_polygon_data = br.readUByteVec(20)  # HullPolygonData
        log("DEBUG", len(hull_polygon_data), aloc_name)
        # TODO: <------------------ Read past EOF Here on second convex mesh!
        if len(hull_polygon_data) < 20:
            break
    if len(hull_polygon_data) < 20:
        return
    _mHullDataVertexData8 = br.readUByteVec(
        convex_mesh.polygons_vertex_count)  # mHullDataVertexData8 for each polygon's vertices
    log("DEBUG", "mHullDataVertexData8 " + str(_mHullDataVertexData8), aloc_name)
    _mHullDataFacesByEdges8 = br.readUByteVec(convex_mesh.edge_count * 2)  # mHullDataFacesByEdges8
    log("DEBUG", "mHullDataFacesByEdges8 " + str(_mHullDataVertexData8), aloc_name)
    _mHullDataFacesByVertices8 = br.readUByteVec(convex_mesh.vertex_count * 3)  # mHullDataFacesByVertices8
    log("DEBUG", "mHullDataFacesByVertices8 " + str(_mHullDataVertexData8), aloc_name)
    if convex_mesh.has_grb_data == 1:
        log("DEBUG", "has_grb_data true. Reading edges. Current offset: " + str(br.tell()), aloc_name)
        _mEdges = br.readUByteVec(4 * 2 * convex_mesh.edge_count)  # mEdges
    else:
        _ = -1
        log("DEBUG", "has_grb_data false. No edges to read. Current offset: " + str(br.tell()), aloc_name)
    log("DEBUG",
        "Finished reading main convex hull data. Reading remaining convex hull data. Current offset: " + str(br.tell()),
        aloc_name)
    # ---- End of Variable data for each Convex Mesh Hull

    # Remaining convex hull data
    zero = br.readFloat()  # 0
    log("DEBUG", "This should be zero: " + str(zero) + " Current offset: " + str(br.tell()), aloc_name)
    # Local bounds
    bbox_min_x = br.readFloat()  # mHullData.mAABB.getMin(0)
    log("DEBUG", "Bbox min x: " + str(bbox_min_x) + " Current offset: " + str(br.tell()), aloc_name)
    _bbox_min_y = br.readFloat()  # mHullData.mAABB.getMin(1)
    _bbox_min_z = br.readFloat()  # mHullData.mAABB.getMin(2)
    _bbox_max_x = br.readFloat()  # mHullData.mAABB.getMax(0)
    _bbox_max_y = br.readFloat()  # mHullData.mAABB.getMax(1)
    _bbox_max_z = br.readFloat()  # mHullData.mAABB.getMax(2)
    # Mass Info
    mass = br.readFloat()  # mMass
    log("DEBUG", "Mass: " + str(mass) + " Current offset: " + str(br.tell()), aloc_name)
    br.readFloatVec(9)  # mInertia
    br.readFloatVec(3)  # mCenterOfMass.x
    gauss_map_flag = br.readFloat()
    log("DEBUG", "Gauss Flag: " + str(gauss_map_flag), aloc_name)

    if gauss_map_flag == 1.0:
        log("DEBUG", "Gauss Flag is 1.0, reading Gauss Data", aloc_name)
        br.readUByteVec(24)  # ICE.SUPM....ICE.GAUS....
        m_subdiv = br.readInt()  # mSVM->mData.m_subdiv
        log("DEBUG", "m_subdiv: " + str(m_subdiv), aloc_name)

        num_samples = br.readInt()  # mSVM->mData.mNbSamples
        log("DEBUG", "num_samples: " + str(num_samples), aloc_name)
        br.readUByteVec(num_samples * 2)
        br.readUByteVec(4)  # ICE.
        log("DEBUG", "Reading VALE: Current offset: " + str(br.tell()), aloc_name)
        vale = br.readString(4)  # VALE
        log("DEBUG", "Should say VALE: " + str(vale), aloc_name)
        br.readUByteVec(4)  # ....
        num_svm_verts = br.readInt()  # mSVM->mData.mNbVerts
        log("DEBUG", "num_svm_verts: " + str(num_svm_verts), aloc_name)
        num_svm_adj_verts = br.readInt()  # mSVM->mData.mNbAdjVerts
        log("DEBUG", "num_svm_adj_verts: " + str(num_svm_adj_verts), aloc_name)
        svm_max_index = br.readInt()  # maxIndex
        log("DEBUG", "svm_max_index: " + str(svm_max_index), aloc_name)
        if svm_max_index <= 0xff:
            log("DEBUG", "svm_max_index <= 0xff. File offset: " + str(br.tell()), aloc_name)
            br.readUByteVec(num_svm_verts)
        else:
            log("DEBUG", "svm_max_index > 0xff. File offset: " + str(br.tell()), aloc_name)
            br.readUByteVec(num_svm_verts * 2)
        br.readUByteVec(num_svm_adj_verts)
        log("DEBUG", "Finished Gauss Data. File offset: " + str(br.tell()), aloc_name)
    else:
        _ = -1
        log("DEBUG", "Gauss Flag is " + str(gauss_map_flag) + " No Gauss Data. File offset: " + str(br.tell()),
            aloc_name)
    _mRadius = br.readFloat()
    _mExtents_0 = br.readFloat()
    _mExtents_1 = br.readFloat()
    _mExtents_2 = br.readFloat()
    log("DEBUG", "Finished reading Convex mesh. File offset: " + str(br.tell()), aloc_name)
    return convex_mesh


def read_triangle_mesh(aloc_name, br):
    # Start of first triangle mesh, offset = 27
    triangle_mesh = TriangleMesh()
    triangle_mesh.collision_layer = br.readUInt()
    br.readUByteVec(16)  # \0\0\0\0NXS.MESH....\u{15}\0\0\0
    # Offset: 47
    br.readUByteVec(4)  # midPhaseId
    log("DEBUG", "Reading serial_flags. Current offset: " + str(br.tell()), aloc_name)

    triangle_mesh.serial_flags = br.readInt()
    # Example Serial Flag: 6 = 00000110: IMSF_FACE_REMAP | IMSF_8BIT_INDICES
    # IMSF_MATERIALS       =    (1 << 0), // ! < if set, the cooked mesh file contains per-triangle material indices
    # IMSF_FACE_REMAP      =    (1 << 1), // ! < if set, the cooked mesh file contains a remap table
    # IMSF_8BIT_INDICES    =    (1 << 2), // ! < if set, the cooked mesh file contains 8bit indices (topology)
    # IMSF_16BIT_INDICES   =    (1 << 3), // ! < if set, the cooked mesh file contains 16bit indices (topology)
    # IMSF_ADJACENCIES     =    (1 << 4), // ! < if set, the cooked mesh file contains adjacency structures
    # IMSF_GRB_DATA        =    (1 << 5)  // ! < if set, the cooked mesh file contains GRB data structures
    log("DEBUG", "Reading Vertex_count: Current offset: " + str(br.tell()), aloc_name)
    triangle_mesh.vertex_count = br.readUInt()
    log("DEBUG", "vertex_count: " + str(triangle_mesh.vertex_count), aloc_name)
    triangle_mesh.triangle_count = br.readUInt()
    log("DEBUG", "triangle_count: " + str(triangle_mesh.triangle_count), aloc_name)
    vertices = []
    for vertex_index in range(triangle_mesh.vertex_count):
        vertex = br.readFloatVec(3)
        log("DEBUG", "vertex " + str(vertex_index) + ": " + str(vertex), aloc_name)
        vertices.append(vertex)
    triangle_mesh.vertices = vertices
    # Check serial flag
    triangle_data = []
    log("DEBUG", "serial Flags: " + str(triangle_mesh.serial_flags), aloc_name)
    is_8bit = (triangle_mesh.serial_flags >> 2) & 1 == 1
    log("DEBUG", "is_8bit: " + str(is_8bit), aloc_name)
    is_16bit = (triangle_mesh.serial_flags >> 3) & 1 == 1
    log("DEBUG", "is_16bit: " + str(is_16bit), aloc_name)
    if is_8bit:
        log("DEBUG", "is_8bit. Reading triangle bytes", aloc_name)
        for triangle_index in range(triangle_mesh.triangle_count * 3):
            triangle_byte = br.readUByte()
            log("DEBUG", "Triangle_byte: " + str(triangle_byte), aloc_name)
            triangle_data.append(triangle_byte)
    elif is_16bit:
        log("DEBUG", "is_16bit. Reading triangle shorts", aloc_name)
        for triangle_index in range(triangle_mesh.triangle_count * 3):
            triangle_short = br.readUShort()
            log("DEBUG", "Triangle_short: " + str(triangle_short), aloc_name)
            triangle_data.append(triangle_short)
    else:
        log("DEBUG", "Not 8 or 16 bit. Reading triangle ints", aloc_name)
        for triangle_index in range(triangle_mesh.triangle_count * 3):
            triangle_int = br.readInt()
            # log("DEBUG", "Triangle_Int: " + str(triangle_int), aloc_name)
            triangle_data.append(triangle_int)
    triangle_mesh.triangle_data = triangle_data
    material_indices = (triangle_mesh.serial_flags >> 0) & 1 == 1
    log("DEBUG", "material_indices: " + str(material_indices), aloc_name)

    if material_indices:
        br.readUByteVec(2 * triangle_mesh.triangle_count)  # material_indices
    face_remap = (triangle_mesh.serial_flags >> 1) & 1 == 1
    log("DEBUG", "face_remap: " + str(face_remap), aloc_name)

    if face_remap:
        max_id = br.readInt()
        log("DEBUG", "max_id: " + str(max_id), aloc_name)
        if max_id <= 0xff:
            face_remap_val = br.readUByteVec(triangle_mesh.triangle_count)
            log("DEBUG", "face_remap_val 8bit: " + str(face_remap_val), aloc_name)

        elif max_id <= 0xffff:
            face_remap_val = br.readUByteVec(triangle_mesh.triangle_count * 2)
            log("DEBUG", "face_remap_val 16bit: " + str(face_remap_val), aloc_name)
        else:
            for triangle_index in range(triangle_mesh.triangle_count):
                face_remap_val = br.readInt()
                log("DEBUG", "face_remap_val int: " + str(face_remap_val), aloc_name)
    adjacencies = (triangle_mesh.serial_flags >> 4) & 1 == 1
    log("DEBUG", "adjacencies: " + str(adjacencies), aloc_name)
    if adjacencies:
        for triangle_index in range(triangle_mesh.triangle_count * 3):
            br.readInt()
    # Write midPhaseStructure. Is it BV4? -> BV4TriangleMeshBuilder::saveMidPhaseStructure
    log("DEBUG", "Reading BV4: Current offset: " + str(br.tell()), aloc_name)
    bv4 = br.readString(3)  # "BV4."
    br.readUByte()
    log("DEBUG", "Should say BV4: " + str(bv4), aloc_name)
    bv4_version = br.readIntBigEndian()  # Bv4 Structure Version. Is always 1, so the midPhaseStructure will be bigEndian
    log("DEBUG", "BV4 version. Should be 1: " + str(bv4_version), aloc_name)
    if bv4_version != 1:
        log("ERROR", "[ERROR] Error reading triangle mesh: Unexpected BV4 version.", aloc_name)
        # raise ValueError("[ERROR] Error reading triangle mesh " + aloc_name + ": Unexpected BV4 version. File offset: " + str(br.tell()))
        return -1
    br.readFloat()  # mData.mBV4Tree.mLocalBounds.mCenter.x
    br.readFloat()  # mData.mBV4Tree.mLocalBounds.mCenter.y
    br.readFloat()  # mData.mBV4Tree.mLocalBounds.mCenter.z
    br.readFloat()  # mData.mBV4Tree.mLocalBounds.mCenter.mExtentsMagnitude
    br.readUByteVec(4)  # mData.mBV4Tree.mInitData
    # #ifdef GU_BV4_QUANTIZED_TREE
    br.readFloat()  # mData.mBV4Tree.mCenterOrMinCoeff.x
    br.readFloat()  # mData.mBV4Tree.mCenterOrMinCoeff.y
    br.readFloat()  # mData.mBV4Tree.mCenterOrMinCoeff.z
    br.readFloat()  # mData.mBV4Tree.mExtentsOrMaxCoeff.x
    br.readFloat()  # mData.mBV4Tree.mExtentsOrMaxCoeff.y
    br.readFloat()  # mData.mBV4Tree.mExtentsOrMaxCoeff.z
    # endif
    log("DEBUG", "Reading mNbNodes: Current offset: " + str(br.tell()), aloc_name)
    m_nb_nodes = br.readIntBigEndian()  # mData.mBV4Tree.mNbNodes
    log("DEBUG", "mNbNodes: " + str(m_nb_nodes), aloc_name)

    for _mNbNodesIndex in range(m_nb_nodes):
        # #ifdef GU_BV4_QUANTIZED_TREE
        br.readUByteVec(12)  # node.mAABB.mData[0].mExtents
        # else
        # br.readFloatVec(6)  # node.mAABB.mCenter.x
        # endif
        br.readUByteVec(4)  # node.mData
    # End midPhaseStructure

    br.readFloat()  # mMeshData.mGeomEpsilon
    bbox_min_x = br.readFloat()  # mMeshData.mAABB.minimum.x
    log("DEBUG", "mMeshData.mAABB.minimum.x: " + str(bbox_min_x), aloc_name)
    br.readFloat()  # mMeshData.mAABB.minimum.y
    br.readFloat()  # mMeshData.mAABB.minimum.z
    br.readFloat()  # mMeshData.mAABB.maximum.x
    br.readFloat()  # mMeshData.mAABB.maximum.y
    bbox_min_z = br.readFloat()  # mMeshData.mAABB.maximum.z
    log("DEBUG", "mMeshData.mAABB.maximum.z: " + str(bbox_min_z), aloc_name)

    # if(mMeshData.mExtraTrigData)
    m_nbv_triangles = br.readInt()  # mMeshData.mNbTriangles
    log("DEBUG", "m_nbv_triangles: " + str(m_nbv_triangles), aloc_name)

    br.readUByteVec(m_nbv_triangles)
    # else
    # br.readUByteVec(4)  # 0
    # endif

    # GRB Write
    has_grb = (triangle_mesh.serial_flags >> 5) & 1 == 1
    log("DEBUG", "has_grb: " + str(has_grb), aloc_name)

    if has_grb:
        for _triangle_index in range(triangle_mesh.triangle_count * 3):
            if is_8bit:
                br.readUByte()
            elif is_16bit:
                br.readUByteVec(2)
            else:
                br.readInt()
        br.readUIntVec(triangle_mesh.triangle_count * 4)  # mMeshData.mGRB_triAdjacencies
        br.readUIntVec(triangle_mesh.triangle_count)  # mMeshData.mGRB_faceRemap
        # Write midPhaseStructure BV3 -> BV32TriangleMeshBuilder::saveMidPhaseStructure
        bv32 = br.readString(4)  # "BV32"
        log("DEBUG", "Reading BV32: " + str(bv32) + " File Offset: " + str(br.tell()), aloc_name)
        br.readUByteVec(4)  # Bv32 Structure Version. If 1, the midPhaseStructure will be bigEndian
        br.readFloat()  # mData.mBV4Tree.mLocalBounds.mCenter.x
        br.readFloat()  # mData.mBV4Tree.mLocalBounds.mCenter.y
        br.readFloat()  # mData.mBV4Tree.mLocalBounds.mCenter.z
        br.readFloat()  # mData.mBV4Tree.mLocalBounds.mCenter.mExtentsMagnitude
        br.readUByteVec(4)  # mData.mBV4Tree.mInitData
        m_nb_packed_nodes = br.readInt()  # mData.mBV4Tree.m_nb_packed_nodes
        log("DEBUG", "m_nb_packed_nodes: " + str(m_nb_packed_nodes), aloc_name)
        m_nb_packed_nodes_be = br.readIntBigEndian()  # mData.mBV4Tree.m_nb_packed_nodes
        log("DEBUG", "m_nb_packed_nodes_be: " + str(m_nb_packed_nodes_be), aloc_name)
        for _mNbNodesIndex in range(m_nb_packed_nodes):
            m_nb_nodes = br.readInt(4)  # node.mNbNodes
            log("DEBUG", "mNbNodes: " + str(m_nb_nodes), aloc_name)
            m_nb_nodes_be = br.readIntBigEndian(4)  # node.mNbNodes
            log("DEBUG", "m_nb_nodes_be: " + str(m_nb_nodes_be), aloc_name)
            br.readUByteVec(4 * m_nb_nodes)  # node.mData
            br.readFloatVec(4 * m_nb_nodes)  # node.mCenter[0].x
            br.readFloatVec(4 * m_nb_nodes)  # node.mExtents[0].x
        # End midPhaseStructure
        # End GRB Write
    return triangle_mesh


class Physics:
    def __init__(self):
        self.data_type = PhysicsDataType.NONE
        self.collision_type = PhysicsCollisionType.NONE
        self.convex_meshes = []
        self.convex_mesh_count = 0
        self.triangle_meshes = []
        self.triangle_mesh_count = 0
        self.primitive_count = []
        self.primitive_boxes = []
        self.primitive_boxes_count = 0
        self.primitive_capsules = []
        self.primitive_capsules_count = 0
        self.primitive_spheres = []
        self.primitive_spheres_count = 0
        self.shatters = []
        self.shatter_count = 0
        if not os.environ["PATH"].startswith(
                os.path.abspath(os.path.dirname(__file__))
        ):
            os.environ["PATH"] = (
                    os.path.abspath(os.path.dirname(__file__))
                    + os.pathsep
                    + os.environ["PATH"]
            )
        if platform.system() == "Linux":
            self.lib = ctypes.CDLL(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "libalocgen.so")),
                winmode=0,
            )
        elif platform.system() == "Windows":
            self.lib = ctypes.CDLL(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "alocgen.dll")),
                winmode=0,
            )
        else:
            print(f"\n\n\n\nError: {platform.system()} is unsupported\n\n\n\n")
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

    def read_primitive_mesh(self, br, primitive_count, aloc_name):
        for primitive_index in range(primitive_count):  # size of box = 52
            primitive_type = br.readString(3).decode("utf-8")
            log("DEBUG", "Loading primitive " + str(primitive_index + 1) + " / " + str(
                primitive_count) + " with type: " + primitive_type, aloc_name)
            br.readUByteVec(1)
            if primitive_type == "BOX":
                log("DEBUG", "Loading Primitive Box", aloc_name)
                primitive_box = PrimitiveBox()
                # 31
                primitive_box.half_extents = br.readFloatVec(3)
                # 43
                primitive_box.collision_layer = br.readUInt64()
                # 51
                primitive_box.position = br.readFloatVec(3)
                # 63
                primitive_box.rotation = br.readFloatVec(4)
                # 79
                log("DEBUG",
                    "Primitive Box: Pos: " + str(primitive_box.position[0]) + str(primitive_box.position[1]) + str(
                        primitive_box.position[2]), aloc_name)
                log("DEBUG", "Primitive Box: half_extents: " + str(primitive_box.half_extents[0]) + str(
                    primitive_box.half_extents[1]) + str(primitive_box.half_extents[2]), aloc_name)
                log("DEBUG",
                    "Primitive Box: rotation: " + str(primitive_box.rotation[0]) + str(primitive_box.rotation[1]) + str(
                        primitive_box.rotation[2]) + str(primitive_box.rotation[3]), aloc_name)
                log("DEBUG", "Primitive Box: collision_layer: " + str(primitive_box.collision_layer), aloc_name)
                self.primitive_boxes_count += 1
                self.primitive_boxes.append(primitive_box)

            elif primitive_type == "CAP":
                primitive_capsule = PrimitiveCapsule()
                primitive_capsule.radius = br.readFloat()
                primitive_capsule.length = br.readFloat()
                primitive_capsule.collision_layer = br.readUInt64()
                primitive_capsule.position = br.readFloatVec(3)
                primitive_capsule.rotation = br.readFloatVec(4)
                self.primitive_capsules_count += 1
                self.primitive_capsules.append(primitive_capsule)
            elif primitive_type == "SPH":
                primitive_sphere = PrimitiveSphere()
                primitive_sphere.radius = br.readFloat()
                primitive_sphere.collision_layer = br.readUInt64()
                primitive_sphere.position = br.readFloatVec(3)
                primitive_sphere.rotation = br.readFloatVec(4)
                self.primitive_spheres_count += 1
                self.primitive_spheres.append(primitive_sphere)

    def read(self, filepath):
        aloc_name = bpy.path.display_name_from_filepath(filepath)

        log("INFO", "Loading aloc file " + aloc_name, aloc_name)

        fp = os.fsencode(filepath)
        file = open(fp, "rb")
        br = io_binary.BinaryReader(file)
        # Header + MeshType Header: sizeof = 23
        self.data_type = br.readUInt()
        self.collision_type = br.readUInt()
        br.readUByteVec(11)  # "ID\0\0\0\u{5}PhysX"
        mesh_type = br.readString(3).decode("utf-8")  # Mesh Type ("CVX", "TRI", "ICP", "BCP")
        log("DEBUG", "Data type: " + str(PhysicsDataType(self.data_type)), aloc_name)
        log("DEBUG", "Current Mesh type: " + mesh_type, aloc_name)
        try:
            br.readUByte()  # .
        except struct.error as err:
            log("ERROR", "Error reading ALOC " + aloc_name + ". Error message: " + str(err), aloc_name)
            br.close()
            return -1
        # End of header. Current offset = 23

        if self.data_type == PhysicsDataType.CONVEX_MESH_AND_TRIANGLE_MESH:
            self.convex_mesh_count = br.readUInt()
            for convex_mesh_index in range(self.convex_mesh_count):
                log("DEBUG", "Loading Convex mesh " + str(convex_mesh_index + 1) + " of " + str(self.convex_mesh_count),
                    aloc_name)
                self.convex_meshes.append(read_convex_mesh(br, aloc_name))
            mesh_type = br.readString(3).decode("utf-8")  # Mesh Type ("TRI")
            br.readUByte()  # .
            log("DEBUG", "Current Mesh type: " + mesh_type, aloc_name)
            self.triangle_mesh_count = br.readUInt()
            for triangle_mesh_index in range(self.triangle_mesh_count):
                log("DEBUG",
                    "Loading Triangle mesh " + str(triangle_mesh_index + 1) + " of " + str(self.triangle_mesh_count),
                    aloc_name)
                mesh = read_triangle_mesh(aloc_name, br)
                if mesh != -1:
                    self.triangle_meshes.append(mesh)
                else:
                    log("ERROR", "Can't continue loading current ALOC " + aloc_name + ". Returning loaded meshes.",
                        aloc_name)
                    self.triangle_mesh_count = triangle_mesh_index
                    br.close()
                    return 0
            br.close()
            return 0
        elif self.data_type == PhysicsDataType.CONVEX_MESH_AND_PRIMITIVE:
            log("DEBUG", "Loading Convex Mesh and Primitives for ALOC: " + aloc_name, aloc_name)
            self.convex_mesh_count = br.readUInt()
            for convex_mesh_index in range(self.convex_mesh_count):
                log("DEBUG", "Loading Convex mesh " + str(convex_mesh_index + 1) + " of " + str(self.convex_mesh_count),
                    aloc_name)
                self.convex_meshes.append(read_convex_mesh(br, aloc_name))
            br.readString(3).decode("utf-8")  # Mesh Type ("ICP")
            br.readUByte()  # .
            log("DEBUG", "Done loading convex meshes. Reading primitive meshes. File offset: " + str(br.tell()),
                aloc_name)
            self.primitive_count = br.readUInt()
            log("DEBUG", "Loading Primitive mesh", aloc_name)
            self.read_primitive_mesh(br, self.primitive_count, aloc_name)
            br.close()
            return 0
        elif self.data_type == PhysicsDataType.TRIANGLE_MESH_AND_PRIMITIVE:
            self.triangle_mesh_count = br.readUInt()
            for triangle_mesh_index in range(self.triangle_mesh_count):
                log("DEBUG",
                    "Loading Triangle mesh " + str(triangle_mesh_index + 1) + " of " + str(self.triangle_mesh_count),
                    aloc_name)
                self.triangle_meshes.append(read_triangle_mesh(aloc_name, br))
            br.readString(3).decode("utf-8")  # Mesh Type ("ICP")
            br.readUByte()  # .
            self.primitive_count = br.readUInt()
            log("DEBUG", "Loading Primitive mesh", aloc_name)
            self.read_primitive_mesh(br, self.primitive_count, aloc_name)
            br.close()
            return 0
        elif self.data_type == PhysicsDataType.SHATTER_LINKED:
            self.shatter_count = br.readUInt()
            br.close()
            return 0
        elif mesh_type == "CVX":
            if self.data_type != PhysicsDataType.CONVEX_MESH:
                _ = -1
                log("WARNING", "data_type " + str(PhysicsDataType(
                    self.data_type)) + " does not match magic string " + mesh_type + " for " + aloc_name, aloc_name)
            self.convex_mesh_count = br.readUInt()
            for convex_mesh_index in range(self.convex_mesh_count):
                log("DEBUG", "Loading Convex mesh " + str(convex_mesh_index + 1) + " of " + str(self.convex_mesh_count),
                    aloc_name)
                self.convex_meshes.append(read_convex_mesh(br, aloc_name))
            br.close()
            return 0
        elif mesh_type == "TRI":
            if self.data_type != PhysicsDataType.TRIANGLE_MESH:
                _ = -1
                log("WARNING", "data_type " + str(PhysicsDataType(
                    self.data_type)) + " does not match magic string " + mesh_type + " for " + aloc_name, aloc_name)
            self.triangle_mesh_count = br.readUInt()
            for triangle_mesh_index in range(self.triangle_mesh_count):
                log("DEBUG",
                    "Loading Triangle mesh " + str(triangle_mesh_index + 1) + " of " + str(self.triangle_mesh_count),
                    aloc_name)
                mesh = read_triangle_mesh(aloc_name, br)
                if mesh != -1:
                    self.triangle_meshes.append(mesh)
                else:
                    log("ERROR", "Can't continue loading current ALOC: " + aloc_name + ". Returning loaded meshes.",
                        aloc_name)
                    self.triangle_mesh_count = triangle_mesh_index
                    return 0
            br.close()
            return 0
        elif mesh_type == "ICP":
            if self.data_type != PhysicsDataType.PRIMITIVE:
                _ = -1
                log("WARNING", "data_type " + str(PhysicsDataType(
                    self.data_type)) + " does not match magic string " + mesh_type + " for " + aloc_name, aloc_name)
            log("DEBUG", "Found primitive", aloc_name)
            primitive_count = br.readUInt()
            # 27
            self.read_primitive_mesh(br, primitive_count, aloc_name)
            self.primitive_count = self.primitive_capsules_count + self.primitive_boxes_count + self.primitive_spheres_count
            br.close()
            return 0
        br.close()
        return -1

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
