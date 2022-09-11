import bpy
from ..io_binary import BinaryReader
from .. import BlenderUI
from ..file_mrtr.format import MorphemeRig
from . import MjbaReader
import math
import mathutils


class Animation:
    def __init__(self, object, mjba_path, mrtr_path):
        self.object = object
        self.mjba_path = mjba_path
        self.mrtr_path = mrtr_path

    def import_animation(self, quaternion_to_try):
        with open(self.mjba_path, "rb") as f:
            self.mjba = MjbaReader(BinaryReader(f))
        with open(self.mrtr_path, "rb") as f:
            self.mrtr = MorphemeRig()
            self.mrtr.read(BinaryReader(f))
        if self.mjba.mrtr_bone_map.mrtr_bone_count != len(self.mrtr.hierarchy.bone_parents):
            BlenderUI.MessageBox("The MJBA and MRTR have mismatched bone counts!", icon="ERROR")
            return
        bpy.ops.object.mode_set(mode='POSE')
        if self.object.animation_data == None:
            self.object.animation_data_create()
        elif self.object.animation_data.action != None:
            print(self.object.animation_data.action)
            bpy.data.actions.remove(self.object.animation_data.action)
        bpy.context.scene.render.fps = int(self.mjba.animation.fps)
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = self.mjba.animation.frame_count_1
        bpy.context.scene.frame_current = 1
        self.twist_bone_map = {"l_forearm": "l_foretwist",
                               "l_upperarm": "luparmtwist",
                               "r_forearm": "r_foretwist",
                               "r_upperarm": "ruparmtwist",
                               "l_thigh": "lthightwist1",
                               "r_thigh": "rthightwist1"}
        self.load_bones()
        output = ""
        for frame in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
            bpy.context.scene.frame_set(frame)
            frame_index = frame - 1
            flag_for_auto_quaternion = False
            for pose_bone in self.object.pose.bones:
                if pose_bone.name in self.pose_bone_to_mrtr_bone:
                    bone = self.pose_bone_to_mrtr_bone[pose_bone.name]
                    if bone in self.bones:
                        # print(bone, "in self bones")
                        if self.bones[bone]["dynamic_transforms"] != None:
                            self.object.pose.bones[pose_bone.name].location = (
                            self.bones[bone]["dynamic_transforms"][frame_index][0],
                            self.bones[bone]["dynamic_transforms"][frame_index][1],
                            self.bones[bone]["dynamic_transforms"][frame_index][2])
                            self.object.pose.bones[pose_bone.name].keyframe_insert(data_path="location")
                        # print(bone, "set transform to", self.bones[bone]["dynamic_transforms"][frame_index], "on frame", frame)
                        if self.bones[bone]["static_transform"] != None:
                            self.object.pose.bones[pose_bone.name].location = (self.bones[bone]["static_transform"][0],
                                                                               self.bones[bone]["static_transform"][1],
                                                                               self.bones[bone]["static_transform"][2])
                            self.object.pose.bones[pose_bone.name].keyframe_insert(data_path="location")
                        # print(bone, "set transform to", self.bones[bone]["dynamic_transforms"][frame_index], "on frame", frame)
                        if self.bones[bone]["dynamic_quaternions"] != None:
                            q = mathutils.Quaternion((self.bones[bone]["dynamic_quaternions"][frame_index][3],
                                                      self.bones[bone]["dynamic_quaternions"][frame_index][0],
                                                      self.bones[bone]["dynamic_quaternions"][frame_index][1],
                                                      self.bones[bone]["dynamic_quaternions"][frame_index][2]))
                            # print(q)
                            '''if self.bones[bone]["bind_poses_quaternions"] != None:
                                q = q @ mathutils.Quaternion((self.bones[bone]["bind_poses_quaternions"][3],
                                                            self.bones[bone]["bind_poses_quaternions"][0],
                                                            self.bones[bone]["bind_poses_quaternions"][1],
                                                            self.bones[bone]["bind_poses_quaternions"][2]))'''
                            # q = q @ mathutils.Quaternion((0.0, 0.0, 1.0), -math.radians(45.0))
                            # print(q)
                            # rotation_quaternion = (q.w, q.x, q.y, q.z)
                            quaternion_to_try_index = 0
                            done = False
                            for a in range(8):
                                if not done:
                                    if a == 0:
                                        self.q1 = q.w
                                    elif a == 1:
                                        self.q1 = -q.w
                                    elif a == 2:
                                        self.q1 = q.x
                                    elif a == 3:
                                        self.q1 = -q.x
                                    elif a == 4:
                                        self.q1 = q.y
                                    elif a == 5:
                                        self.q1 = -q.y
                                    elif a == 6:
                                        self.q1 = q.z
                                    elif a == 7:
                                        self.q1 = -q.z
                                    for b in range(8):
                                        if not done:
                                            if b == 0:
                                                self.q2 = q.x
                                            elif b == 1:
                                                self.q2 = -q.x
                                            elif b == 2:
                                                self.q2 = q.y
                                            elif b == 3:
                                                self.q2 = -q.y
                                            elif b == 4:
                                                self.q2 = q.z
                                            elif b == 5:
                                                self.q2 = -q.z
                                            elif b == 6:
                                                self.q2 = q.w
                                            elif b == 7:
                                                self.q2 = -q.w
                                            for c in range(8):
                                                if not done:
                                                    if c == 0:
                                                        self.q3 = q.y
                                                    elif c == 1:
                                                        self.q3 = -q.y
                                                    elif c == 2:
                                                        self.q3 = q.z
                                                    elif c == 3:
                                                        self.q3 = -q.z
                                                    elif c == 4:
                                                        self.q3 = q.w
                                                    elif c == 5:
                                                        self.q3 = -q.w
                                                    elif c == 6:
                                                        self.q3 = q.x
                                                    elif c == 7:
                                                        self.q3 = -q.x
                                                    for d in range(8):
                                                        if not done:
                                                            if d == 0:
                                                                self.q4 = q.z
                                                            elif d == 1:
                                                                self.q4 = -q.z
                                                            elif d == 2:
                                                                self.q4 = q.w
                                                            elif d == 3:
                                                                self.q4 = -q.w
                                                            elif d == 4:
                                                                self.q4 = q.x
                                                            elif d == 5:
                                                                self.q4 = -q.x
                                                            elif d == 6:
                                                                self.q4 = q.y
                                                            elif d == 7:
                                                                self.q4 = -q.y
                                                            if quaternion_to_try == quaternion_to_try_index:
                                                                rotation_quaternion = (
                                                                self.q1, self.q2, self.q3, self.q4)
                                                                if frame_index == 0 and not flag_for_auto_quaternion:
                                                                    if a == 0:
                                                                        output += "q.w"
                                                                    elif a == 1:
                                                                        output += "-q.w"
                                                                    elif a == 2:
                                                                        output += "q.x"
                                                                    elif a == 3:
                                                                        output += "-q.x"
                                                                    elif a == 4:
                                                                        output += "q.y"
                                                                    elif a == 5:
                                                                        output += "-q.y"
                                                                    elif a == 6:
                                                                        output += "q.z"
                                                                    elif a == 7:
                                                                        output += "-q.z"
                                                                    if b == 0:
                                                                        output += ", q.x"
                                                                    elif b == 1:
                                                                        output += ", -q.x"
                                                                    elif b == 2:
                                                                        output += ", q.y"
                                                                    elif b == 3:
                                                                        output += ", -q.y"
                                                                    elif b == 4:
                                                                        output += ", q.z"
                                                                    elif b == 5:
                                                                        output += ", -q.z"
                                                                    elif b == 6:
                                                                        output += ", q.w"
                                                                    elif b == 7:
                                                                        output += ", -q.w"
                                                                    if c == 0:
                                                                        output += ", q.y"
                                                                    elif c == 1:
                                                                        output += ", -q.y"
                                                                    elif c == 2:
                                                                        output += ", q.z"
                                                                    elif c == 3:
                                                                        output += ", -q.z"
                                                                    elif c == 4:
                                                                        output += ", q.w"
                                                                    elif c == 5:
                                                                        output += ", -q.w"
                                                                    elif c == 6:
                                                                        output += ", q.x"
                                                                    elif c == 7:
                                                                        output += ", -q.x"
                                                                    if d == 0:
                                                                        output += " q.z"
                                                                    elif d == 1:
                                                                        output += " -q.z"
                                                                    elif d == 2:
                                                                        output += " q.w"
                                                                    elif d == 3:
                                                                        output += " -q.w"
                                                                    elif d == 4:
                                                                        output += " q.x"
                                                                    elif d == 5:
                                                                        output += " -q.x"
                                                                    elif d == 6:
                                                                        output += " q.y"
                                                                    elif d == 7:
                                                                        output += " -q.y"
                                                                    done = True
                                                                    flag_for_auto_quaternion = True
                                                            quaternion_to_try_index += 1
                            self.object.pose.bones[pose_bone.name].rotation_quaternion = rotation_quaternion
                            self.object.pose.bones[pose_bone.name].keyframe_insert(data_path="rotation_quaternion")
                            # print(bone, "set quaternion to", self.bones[bone]["dynamic_quaternions"][frame_index], "on frame", frame)
                            if self.mrtr_bone_to_pose_bone[bone] in self.twist_bone_map:
                                if self.twist_bone_map[self.mrtr_bone_to_pose_bone[bone]] in self.pose_bones:
                                    self.object.pose.bones[self.twist_bone_map[
                                        self.mrtr_bone_to_pose_bone[bone]]].rotation_quaternion = rotation_quaternion
                                    self.object.pose.bones[
                                        self.twist_bone_map[self.mrtr_bone_to_pose_bone[bone]]].keyframe_insert(
                                        data_path="rotation_quaternion")
                            # print(self.twist_bone_map[self.mrtr_bone_to_pose_bone[bone]], "set quaternion to", self.bones[bone]["dynamic_quaternions"][frame_index], "on frame", frame)
                        if self.bones[bone]["static_quaternion"] != None:
                            q = mathutils.Quaternion((self.bones[bone]["static_quaternion"][3],
                                                      self.bones[bone]["static_quaternion"][0],
                                                      self.bones[bone]["static_quaternion"][1],
                                                      self.bones[bone]["static_quaternion"][2]))
                            # print(q)
                            '''if self.bones[bone]["bind_poses_quaternions"] != None:
                                q = q @ mathutils.Quaternion((self.bones[bone]["bind_poses_quaternions"][3],
                                                            self.bones[bone]["bind_poses_quaternions"][0],
                                                            self.bones[bone]["bind_poses_quaternions"][1],
                                                            self.bones[bone]["bind_poses_quaternions"][2]))'''
                            # q = q @ mathutils.Quaternion((0.0, 0.0, 1.0), -math.radians(45.0))
                            # print(q)
                            # rotation_quaternion = (q.w, q.x, q.y, q.z)
                            quaternion_to_try_index = 0
                            done = False

                            # holy shit, what happened here?
                            for a in range(8):
                                if not done:
                                    if a == 0:
                                        self.q1 = q.w
                                    elif a == 1:
                                        self.q1 = -q.w
                                    elif a == 2:
                                        self.q1 = q.x
                                    elif a == 3:
                                        self.q1 = -q.x
                                    elif a == 4:
                                        self.q1 = q.y
                                    elif a == 5:
                                        self.q1 = -q.y
                                    elif a == 6:
                                        self.q1 = q.z
                                    elif a == 7:
                                        self.q1 = -q.z
                                    for b in range(8):
                                        if not done:
                                            if b == 0:
                                                self.q2 = q.x
                                            elif b == 1:
                                                self.q2 = -q.x
                                            elif b == 2:
                                                self.q2 = q.y
                                            elif b == 3:
                                                self.q2 = -q.y
                                            elif b == 4:
                                                self.q2 = q.z
                                            elif b == 5:
                                                self.q2 = -q.z
                                            elif b == 6:
                                                self.q2 = q.w
                                            elif b == 7:
                                                self.q2 = -q.w
                                            for c in range(8):
                                                if not done:
                                                    if c == 0:
                                                        self.q3 = q.y
                                                    elif c == 1:
                                                        self.q3 = -q.y
                                                    elif c == 2:
                                                        self.q3 = q.z
                                                    elif c == 3:
                                                        self.q3 = -q.z
                                                    elif c == 4:
                                                        self.q3 = q.w
                                                    elif c == 5:
                                                        self.q3 = -q.w
                                                    elif c == 6:
                                                        self.q3 = q.x
                                                    elif c == 7:
                                                        self.q3 = -q.x
                                                    for d in range(8):
                                                        if not done:
                                                            if d == 0:
                                                                self.q4 = q.z
                                                            elif d == 1:
                                                                self.q4 = -q.z
                                                            elif d == 2:
                                                                self.q4 = q.w
                                                            elif d == 3:
                                                                self.q4 = -q.w
                                                            elif d == 4:
                                                                self.q4 = q.x
                                                            elif d == 5:
                                                                self.q4 = -q.x
                                                            elif d == 6:
                                                                self.q4 = q.y
                                                            elif d == 7:
                                                                self.q4 = -q.y
                                                            if quaternion_to_try == quaternion_to_try_index:
                                                                rotation_quaternion = (
                                                                self.q1, self.q2, self.q3, self.q4)
                                                                if frame_index == 0 and not flag_for_auto_quaternion:
                                                                    if a == 0:
                                                                        output += "q.w"
                                                                    elif a == 1:
                                                                        output += "-q.w"
                                                                    elif a == 2:
                                                                        output += "q.x"
                                                                    elif a == 3:
                                                                        output += "-q.x"
                                                                    elif a == 4:
                                                                        output += "q.y"
                                                                    elif a == 5:
                                                                        output += "-q.y"
                                                                    elif a == 6:
                                                                        output += "q.z"
                                                                    elif a == 7:
                                                                        output += "-q.z"
                                                                    if b == 0:
                                                                        output += ", q.x"
                                                                    elif b == 1:
                                                                        output += ", -q.x"
                                                                    elif b == 2:
                                                                        output += ", q.y"
                                                                    elif b == 3:
                                                                        output += ", -q.y"
                                                                    elif b == 4:
                                                                        output += ", q.z"
                                                                    elif b == 5:
                                                                        output += ", -q.z"
                                                                    elif b == 6:
                                                                        output += ", q.w"
                                                                    elif b == 7:
                                                                        output += ", -q.w"
                                                                    if c == 0:
                                                                        output += ", q.y"
                                                                    elif c == 1:
                                                                        output += ", -q.y"
                                                                    elif c == 2:
                                                                        output += ", q.z"
                                                                    elif c == 3:
                                                                        output += ", -q.z"
                                                                    elif c == 4:
                                                                        output += ", q.w"
                                                                    elif c == 5:
                                                                        output += ", -q.w"
                                                                    elif c == 6:
                                                                        output += ", q.x"
                                                                    elif c == 7:
                                                                        output += ", -q.x"
                                                                    if d == 0:
                                                                        output += " q.z"
                                                                    elif d == 1:
                                                                        output += " -q.z"
                                                                    elif d == 2:
                                                                        output += " q.w"
                                                                    elif d == 3:
                                                                        output += " -q.w"
                                                                    elif d == 4:
                                                                        output += " q.x"
                                                                    elif d == 5:
                                                                        output += " -q.x"
                                                                    elif d == 6:
                                                                        output += " q.y"
                                                                    elif d == 7:
                                                                        output += " -q.y"
                                                                    done = True
                                                                    flag_for_auto_quaternion = True
                                                            quaternion_to_try_index += 1
                            self.object.pose.bones[pose_bone.name].rotation_quaternion = rotation_quaternion
                            self.object.pose.bones[pose_bone.name].keyframe_insert(data_path="rotation_quaternion")
                            # print(bone, "set quaternion to", self.bones[bone]["dynamic_quaternions"][frame_index], "on frame", frame)
                            if self.mrtr_bone_to_pose_bone[bone] in self.twist_bone_map:
                                if self.twist_bone_map[self.mrtr_bone_to_pose_bone[bone]] in self.pose_bones:
                                    self.object.pose.bones[self.twist_bone_map[
                                        self.mrtr_bone_to_pose_bone[bone]]].rotation_quaternion = rotation_quaternion
                                    self.object.pose.bones[
                                        self.twist_bone_map[self.mrtr_bone_to_pose_bone[bone]]].keyframe_insert(
                                        data_path="rotation_quaternion")
                            # print(self.twist_bone_map[self.mrtr_bone_to_pose_bone[bone]], "set quaternion to", self.bones[bone]["dynamic_quaternions"][frame_index], "on frame", frame)
        print("Trying quaternion: (", output, ")")
        for pose_bone in self.object.pose.bones:
            # print(pose_bone.name)
            pass

    def apply_animation(self):
        '''bpy.ops.object.mode_set(mode='POSE')
        bpy.context.scene.render.fps = self.mjba.mjba.animation.fps
        bpy.context.scene.frame_end = self.mjba.mjba.animation.frame_count_1
        bone_list = self.mjba.get_used_bone_list()
        print(bone_list)
        #debug_list = [ "Laboratory_Machine_D_Arm_Root", "Arm_Base", "Arm_Rotation_A" ]#"Ground", "Spine", "Spine1", "Spine2", "Neck", "Neck1", "Head" ]
        for bone in bone_list:
            #if bone in debug_list:
            print(bone, "added to self bones")
            self.bones[bone] = Bone.Bone(object, bone)
        for bone1 in object.pose.bones:
            for bone2 in bone_list:
                if bone1.name.lower() == bone2.lower():
                    bone1.name = bone2
                    print(bone1.name, "was changed to", bone2)
        for frame in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end):
            bpy.context.scene.frame_set(frame)
            for bone in object.pose.bones:
                #print(bone.name, "in pose bones")
                if bone.name in self.bones:
                    print(bone.name, "in self bones")
                    self.bones[bone.name].location = self.mjba.get_bone_location(frame, bone.name)
                    if self.bones[bone.name].location != None:
                        object.pose.bones[bone.name].location = self.bones[bone.name].location
                        object.pose.bones[bone.name].keyframe_insert(data_path = "location")
                    print(object.pose.bones[bone.name].location)
                    self.bones[bone.name].rotation_quaternion = self.mjba.get_bone_rotation(frame, bone.name)
                    if self.bones[bone.name].rotation_quaternion != None:
                        object.pose.bones[bone.name].rotation_quaternion = self.bones[bone.name].rotation_quaternion
                        object.pose.bones[bone.name].keyframe_insert(data_path = "rotation_quaternion")
                    print(object.pose.bones[bone.name].rotation_quaternion)'''

    def export_animation(self, object):
        pass
        '''bpy.ops.object.mode_set(mode='POSE')
        self.object = object
        self.bones = {}		
        for fcurve in self.object.animation_data.action.fcurves:
            animation_type = fcurve.data_path[fcurve.data_path.rfind('.') + 1:]
            bone = fcurve.data_path.split('"')[1]
            if bone not in self.bones:
                self.bones[bone] = Bone.Bone(object, bone)
            for keyframe in fcurve.keyframe_points:
                if keyframe.co[0] >= bpy.context.scene.frame_start and keyframe.co[0] <= bpy.context.scene.frame_end:
                    if animation_type == "location":
                        self.bones[bone].set_position_animated()
                    elif animation_type == "rotation_euler":
                        self.bones[bone].set_rotation_animated()
                    elif animation_type == "rotation_quaternion":
                        self.bones[bone].set_rotation_animated()
                    elif animation_type == "scale":
                        self.bones[bone].set_scale_animated()
        for frame in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
            bpy.context.scene.frame_set(frame)
            for bone in object.pose.bones:
                if bone in self.bones:
                    self.bones[bone].set_matrix(frame, bone.matrix)'''

    def clear_object_animation(self):
        bpy.ops.object.mode_set(mode='POSE')
        if self.object.animation_data == None:
            self.object.animation_data_create()
        elif self.object.animation_data.action != None:
            print(self.object.animation_data.action)
            bpy.data.actions.remove(self.object.animation_data.action)
            bpy.context.scene.frame_start = 1
            bpy.context.scene.frame_end = 1
            bpy.context.scene.frame_current = 1

    def load_bones(self):
        bpy.ops.object.mode_set(mode='POSE')
        self.mrtr_bone_to_pose_bone = {}
        self.pose_bone_to_mrtr_bone = {}
        self.pose_bones = []
        for pose_bone in self.object.pose.bones:
            # print(pose_bone.name.encode())
            for mrtr_bone in self.mrtr.bone_name_map.data:
                # print(mrtr_bone)
                if pose_bone.name.lower().encode() == mrtr_bone.lower():
                    self.mrtr_bone_to_pose_bone[mrtr_bone] = pose_bone.name
                    self.pose_bone_to_mrtr_bone[pose_bone.name] = mrtr_bone
            self.pose_bones.append(pose_bone.name)
        self.mrtr_index_to_mjba_index = {}
        for used_bone_index in self.mjba.mrtr_bone_map.used_bone_indices:
            self.mrtr_index_to_mjba_index[used_bone_index] = self.mjba.mrtr_bone_map.mrtr_bone_indices[used_bone_index]
        self.bones = {}
        # print(self.mrtr_index_to_mjba_index)
        # print(self.mrtr_bone_to_pose_bone)
        # print(self.pose_bone_to_mrtr_bone)
        static_quaternion_index = 0
        static_transform_index = 0
        static_bind_poses_index = 0
        for used_bone_index in self.mjba.mrtr_bone_map.used_bone_indices:
            bone = self.mrtr.bone_name_map.data[used_bone_index]
            self.bones[bone] = {}
            self.bones[bone]["static_quaternion"] = None
            self.bones[bone]["dynamic_quaternions"] = None
            self.bones[bone]["static_transform"] = None
            self.bones[bone]["static_scale"] = None
            self.bones[bone]["dynamic_transforms"] = None
            self.bones[bone]["dynamic_scales"] = None
            self.bones[bone]["bind_poses_quaternions"] = None
            self.bones[bone]["bind_poses_transforms"] = None
            self.bones[bone]["index"] = self.mjba.mrtr_bone_map.mrtr_bone_indices[used_bone_index]
            if self.mjba.animation.bones_with_static_quaternions["bones"][self.bones[bone]["index"]]:
                self.bones[bone]["static_quaternion"] = [
                    self.mjba.animation.static_bone_quaternions[static_quaternion_index * 4],
                    self.mjba.animation.static_bone_quaternions[static_quaternion_index * 4 + 1],
                    self.mjba.animation.static_bone_quaternions[static_quaternion_index * 4 + 2],
                    self.mjba.animation.static_bone_quaternions[static_quaternion_index * 4 + 3]]
                static_quaternion_index += 1
            if self.mjba.animation.bones_with_static_transforms["bones"][self.bones[bone]["index"]]:
                self.bones[bone]["static_transform"] = [
                    self.mjba.animation.static_bone_transforms[static_transform_index * 4],
                    self.mjba.animation.static_bone_transforms[static_transform_index * 4 + 1],
                    self.mjba.animation.static_bone_transforms[static_transform_index * 4 + 2]]
                self.bones[bone]["static_sccale"] = self.mjba.animation.static_bone_transforms[
                    static_transform_index * 4 + 3]
                self.bones[bone]["static_transform"][0] *= self.mjba.animation.transform_scale[0]
                self.bones[bone]["static_transform"][1] *= self.mjba.animation.transform_scale[1]
                self.bones[bone]["static_transform"][2] *= self.mjba.animation.transform_scale[2]
                static_transform_index += 1
            if self.mjba.animation.bones_with_static_bind_poses["bones"][self.bones[bone]["index"]]:
                self.bones[bone]["bind_poses_quaternions"] = [
                    self.mjba.animation.bone_bind_poses_quaternions[static_bind_poses_index * 4],
                    self.mjba.animation.bone_bind_poses_quaternions[static_bind_poses_index * 4 + 1],
                    self.mjba.animation.bone_bind_poses_quaternions[static_bind_poses_index * 4 + 2],
                    self.mjba.animation.bone_bind_poses_quaternions[static_bind_poses_index * 4 + 3],
                    self.mjba.animation.bone_bind_poses_quaternions[static_bind_poses_index * 4 + 4],
                    self.mjba.animation.bone_bind_poses_quaternions[static_bind_poses_index * 4 + 5],
                    self.mjba.animation.bone_bind_poses_quaternions[static_bind_poses_index * 4 + 6],
                    self.mjba.animation.bone_bind_poses_quaternions[static_bind_poses_index * 4 + 7]]
                self.bones[bone]["bind_poses_transforms"] = [
                    self.mjba.animation.bone_bind_poses_transforms[static_bind_poses_index * 4],
                    self.mjba.animation.bone_bind_poses_transforms[static_bind_poses_index * 4 + 1],
                    self.mjba.animation.bone_bind_poses_transforms[static_bind_poses_index * 4 + 2],
                    self.mjba.animation.bone_bind_poses_transforms[static_bind_poses_index * 4 + 3],
                    self.mjba.animation.bone_bind_poses_transforms[static_bind_poses_index * 4 + 4],
                    self.mjba.animation.bone_bind_poses_transforms[static_bind_poses_index * 4 + 5],
                    self.mjba.animation.bone_bind_poses_transforms[static_bind_poses_index * 4 + 6],
                    self.mjba.animation.bone_bind_poses_transforms[static_bind_poses_index * 4 + 7]]
                self.bones[bone]["bind_poses_transforms"][0] *= self.mjba.animation.transform_scale[0]
                self.bones[bone]["bind_poses_transforms"][1] *= self.mjba.animation.transform_scale[1]
                self.bones[bone]["bind_poses_transforms"][2] *= self.mjba.animation.transform_scale[2]
                self.bones[bone]["bind_poses_transforms"][4] *= self.mjba.animation.transform_scale[0]
                self.bones[bone]["bind_poses_transforms"][5] *= self.mjba.animation.transform_scale[1]
                self.bones[bone]["bind_poses_transforms"][6] *= self.mjba.animation.transform_scale[2]
                static_bind_poses_index += 1
        dynamic_quaternion_index = 0
        dynamic_transform_index = 0
        for frame in range(self.mjba.animation.frame_count_1):
            for used_bone_index in self.mjba.mrtr_bone_map.used_bone_indices:
                bone = self.mrtr.bone_name_map.data[used_bone_index]
                if self.bones[bone]["static_quaternion"] == None:
                    if self.bones[bone]["dynamic_quaternions"] == None:
                        self.bones[bone]["dynamic_quaternions"] = []
                    self.bones[bone]["dynamic_quaternions"].append(
                        [self.mjba.animation.dynamic_bone_quaternions[dynamic_quaternion_index * 4],
                         self.mjba.animation.dynamic_bone_quaternions[dynamic_quaternion_index * 4 + 1],
                         self.mjba.animation.dynamic_bone_quaternions[dynamic_quaternion_index * 4 + 2],
                         self.mjba.animation.dynamic_bone_quaternions[dynamic_quaternion_index * 4 + 3]])
                    dynamic_quaternion_index += 1
                if self.bones[bone]["static_transform"] == None:
                    if self.bones[bone]["dynamic_transforms"] == None:
                        self.bones[bone]["dynamic_transforms"] = []
                    if self.bones[bone]["dynamic_scales"] == None:
                        self.bones[bone]["dynamic_scales"] = []
                    dynamic_transform = [self.mjba.animation.dynamic_bone_transforms[dynamic_transform_index * 4],
                                         self.mjba.animation.dynamic_bone_transforms[dynamic_transform_index * 4 + 1],
                                         self.mjba.animation.dynamic_bone_transforms[dynamic_transform_index * 4 + 2]]
                    self.bones[bone]["dynamic_scales"].append(
                        self.mjba.animation.dynamic_bone_transforms[dynamic_transform_index * 4 + 3])
                    dynamic_transform[0] *= self.mjba.animation.transform_scale[0]
                    dynamic_transform[1] *= self.mjba.animation.transform_scale[1]
                    dynamic_transform[2] *= self.mjba.animation.transform_scale[2]
                    self.bones[bone]["dynamic_transforms"].append(dynamic_transform)
                    static_transform_index += 1
# print(self.bones)
