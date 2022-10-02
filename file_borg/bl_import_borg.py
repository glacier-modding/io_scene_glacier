import os
import bpy
import mathutils
import math

from mathutils import Vector, Quaternion, Matrix
import numpy as np

from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       )

from bpy_extras.io_utils import (ImportHelper,
                                 ExportHelper,
                                 unpack_list,
                                 unpack_face_list,
                                 axis_conversion,
                                 )

from . import format
from .. import io_binary

class Bone:

    def __init__(self):
        self.name = None
        self.children = []
        self.parent = None
        self.base_trs = (
            Vector((0, 0, 0)),
            Quaternion((1, 0, 0, 0)),
            Vector((1, 1, 1)),
        )
        # Additional rotations before/after the base TRS.
        # Allows per-bone axis adjustment. See local_rotation.
        self.rotation_after = Quaternion((1, 0, 0, 0))
        self.rotation_before = Quaternion((1, 0, 0, 0))

    def trs(self):
        # (final TRS) = (rotation after) (base TRS) (rotation before)
        t, r, s = self.base_trs
        m = scale_rot_swap_matrix(self.rotation_before)
        return (
            self.rotation_after @ t,
            self.rotation_after @ r @ self.rotation_before,
            m @ s,
        )

def nearby_signed_perm_matrix(rot): #found in gltf_blender addon
    """Returns a signed permutation matrix close to rot.to_matrix().
    (A signed permutation matrix is like a permutation matrix, except
    the non-zero entries can be ±1.)
    """
    m = rot.to_matrix()
    x, y, z = m[0], m[1], m[2]

    # Set the largest entry in the first row to ±1
    a, b, c = abs(x[0]), abs(x[1]), abs(x[2])
    i = 0 if a >= b and a >= c else 1 if b >= c else 2
    x[i] = 1 if x[i] > 0 else -1
    x[(i + 1) % 3] = 0
    x[(i + 2) % 3] = 0

    # Same for second row: only two columns to consider now.
    a, b = abs(y[(i + 1) % 3]), abs(y[(i + 2) % 3])
    j = (i + 1) % 3 if a >= b else (i + 2) % 3
    y[j] = 1 if y[j] > 0 else -1
    y[(j + 1) % 3] = 0
    y[(j + 2) % 3] = 0

    # Same for third row: only one column left
    k = (0 + 1 + 2) - i - j
    z[k] = 1 if z[k] > 0 else -1
    z[(k + 1) % 3] = 0
    z[(k + 2) % 3] = 0

    return m

def scale_rot_swap_matrix(rot): #found in gltf_blender addon
    """Returns a matrix m st. Scale[s] Rot[rot] = Rot[rot] Scale[m s].
    If rot.to_matrix() is a signed permutation matrix, works for any s.
    Otherwise works only if s is a uniform scaling.
    """
    m = nearby_signed_perm_matrix(rot)  # snap to signed perm matrix
    m.transpose()  # invert permutation
    for i in range(3):
        for j in range(3):
            m[i][j] = abs(m[i][j])  # discard sign
    return m

def pick_bone_length(bones, bone_id):
    """Heuristic for bone length."""
    bone = bones[bone_id]

    child_locs = [
        bones[child].editbone_trans
        for child in bone.children
    ]
    child_locs = [loc for loc in child_locs]
    if child_locs:
        return min(loc.length for loc in child_locs)

    return bones[bone.parent].bone_length

def pick_bone_rotation(bones, bone_id, parent_rot):
    bone = bones[bone_id]

    # Try to put our tip at the centroid of our children
    child_locs = [
        bones[child].editbone_trans
        for child in bone.children
    ]
    child_locs = [loc for loc in child_locs]
    if child_locs:
        centroid = sum(child_locs, Vector((0, 0, 0)))
        rot = Vector((0, 1, 0)).rotation_difference(centroid)
        rot = nearby_signed_perm_matrix(rot).to_quaternion()
        return rot

    return parent_rot

def local_rotation(bones, bone_id, rot):
    """Appends a local rotation to bone's world transform:
    (new world transform) = (old world transform) @ (rot)
    without changing the world transform of bone's children.

    For correctness, rot must be a signed permutation of the axes
    """
    bones[bone_id].rotation_before @= rot

    # Append the inverse rotation after children's TRS to cancel it out.
    rot_inv = rot.conjugated()
    for child in bones[bone_id].children:
        bones[child].rotation_after = \
            rot_inv @ bones[child].rotation_after

def rotate_edit_bone(bones, bone_id, rot):
    """Rotate one edit bone without affecting anything else."""
    bones[bone_id].editbone_rot @= rot
    # Cancel out the rotation so children aren't affected.
    rot_inv = rot.conjugated()
    for child_id in bones[bone_id].children:
        child = bones[child_id]
        child.editbone_trans = rot_inv @ child.editbone_trans
        child.editbone_rot = rot_inv @ child.editbone_rot
    # Need to rotate the bone's final TRS by the same amount so skinning
    # isn't affected.
    local_rotation(bones, bone_id, rot)


def prettify_bones(bones):
    """
    Prettify bone lengths/directions.
    """

    def visit(bone_id, parent_rot=None):  # Depth-first walk
        bone = bones[bone_id]
        rot = None

        bone.bone_length = pick_bone_length(bones, bone_id)
        rot = pick_bone_rotation(bones, bone_id, parent_rot)
        if rot is not None:
            rotate_edit_bone(bones, bone_id, rot)
        for child in bone.children:
            visit(child, parent_rot=rot)

    visit(0)

def calc_bone_matrices(bones):
    """
    Calculate the transformations from bone space to arma space in the bind
    pose and in the edit bone pose.
    """

    def visit(bone_id):  # Depth-first walk
        bone = bones[bone_id]

        parent_bind_mat = Matrix.Identity(4)
        parent_editbone_mat = Matrix.Identity(4)

        if bone.parent >= 0:
            parent_bind_mat = bones[bone.parent].bind_arma_mat
            parent_editbone_mat = bones[bone.parent].editbone_arma_mat

        t, r = bone.bind_trans, bone.bind_rot
        local_to_parent = Matrix.Translation(t) @ Quaternion(r).to_matrix().to_4x4()
        bone.bind_arma_mat = parent_bind_mat @ local_to_parent

        t, r = bone.editbone_trans, bone.editbone_rot
        local_to_parent = Matrix.Translation(t) @ Quaternion(r).to_matrix().to_4x4()
        bone.editbone_arma_mat = parent_editbone_mat @ local_to_parent

        for child in bone.children:
            visit(child)

    visit(0)

def compute_bones(borg):
    bones = {}
    init_bones(borg, bones)
    prettify_bones(bones)
    calc_bone_matrices(bones)
    return bones

def get_bone_trs(svq):
    t = Vector([svq.position[0], -svq.position[2], svq.position[1]])
    r = Quaternion([svq.rotation[3], -svq.rotation[0], svq.rotation[2], -svq.rotation[1]])
    s = Vector([1, 1, 1])
    return t, r, s

def init_bones(borg, bones):
    for i, bone in enumerate(borg.bone_definitions):
        bl_bone = Bone()
        bones[i] = bl_bone
        bl_bone.name = bone.name
        bl_bone.base_trs = get_bone_trs(borg.bind_poses[i])
        bl_bone.bind_trans = Vector(bl_bone.base_trs[0])
        bl_bone.bind_rot = Quaternion(bl_bone.base_trs[1])
        bl_bone.editbone_trans = Vector(bl_bone.bind_trans)
        bl_bone.editbone_rot = Quaternion(bl_bone.bind_rot)
        bl_bone.parent = bone.prev_bone_nr
        if i == 0:  # if root
            rot = mathutils.Euler((0.0, 0.0, 0.0), 'XYZ')
            rot.rotate_axis('X', math.radians(-90.0))
            bl_bone.base_trs[1].rotate(rot)

    for i, bone in enumerate(borg.bone_definitions):
        if len(borg.bone_definitions) >= bone.prev_bone_nr >= 0:
            bones[bone.prev_bone_nr].children.append(i)


def load_borg(operator, context, filepath):
    fp = os.fsencode(filepath)
    file = open(fp, "rb")
    br = io_binary.BinaryReader(file)
    rig = []

    borg_name = bpy.path.display_name_from_filepath(filepath)

    amt = bpy.data.armatures.new(borg_name)
    borg = format.BoneRig()
    borg.read(br)

    bones = compute_bones(borg)

    #for constr in borg.bone_constraints.bone_constraints:
    #    print(borg.bone_definitions[constr.bone_index].name)
    #    print(print(', '.join("%s: %s" % item for item in vars(constr).items())))
    #    print()

    blender_arma = bpy.data.objects.new('temp_obj', amt)
    bpy.context.collection.objects.link(blender_arma)
    armature = blender_arma.data

    bone_ids = []
    def visit(id):  # Depth-first walk

        bone_ids.append(id)
        for child in bones[id].children:
            visit(child)

    visit(0)

    # Switch into edit mode to create all edit bones

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = blender_arma
    bpy.ops.object.mode_set(mode="EDIT")

    for id in bone_ids:
        bone = bones[id]
        editbone = armature.edit_bones.new(bytes.decode(bone.name, "utf-8"))
        bone.bl_bone_name = editbone.name
        editbone.use_connect = False  # TODO?

        # Give the position of the bone in armature space
        arma_mat = bone.editbone_arma_mat
        editbone.head = arma_mat @ Vector((0, 0, 0))
        editbone.tail = arma_mat @ Vector((0, 1, 0))
        editbone.length = bone.bone_length
        editbone.align_roll(arma_mat @ Vector((0, 0, 1)) - editbone.head)

        # Set all bone parents
    for id in bone_ids:
        bone = bones[id]

        if bone.parent >= 0:
            parent_bone = bones[bone.parent]

            editbone = armature.edit_bones[bone.bl_bone_name]
            parent_editbone = armature.edit_bones[parent_bone.bl_bone_name]
            editbone.parent = parent_editbone

    # Switch back to object mode and do pose bones
    bpy.ops.object.mode_set(mode="OBJECT")

    for id in bone_ids:
        bone = bones[id]
        pose_bone = blender_arma.pose.bones[bone.bl_bone_name]

        # BoneTRS = EditBone * PoseBone
        t, r, s = bone.trs()
        et, er = bone.editbone_trans, bone.editbone_rot
        pose_bone.location = er.conjugated() @ (t - et)
        pose_bone.rotation_mode = 'QUATERNION'
        pose_bone.rotation_quaternion = er.conjugated() @ r
        pose_bone.scale = s

    amt = blender_arma.data
    bpy.data.objects.remove(blender_arma)
    return amt
