import math
import os
import time

import bpy
import mathutils
from mathutils import Vector

from SKA_Export.ska import SkaAnimStream
from .ska import SkmFile, SkaFile

BOUNDS_SKA = []
USE_SHADELESS = True
global scn
scn = None

object_dictionary = {}
object_matrix = {}
# rig_dictionary = {}
global ToEE_data_dir
ToEE_data_dir = ""  # ToEE data dir. Extracted from the filename, assuming it is located inside the data/art folder, and its textures are all present there.


def add_texture_to_material(image, texture, scale, offset, extension, material, mapto):
    '''
    Adds new texture slot to material, and assigns it an image
    '''

    if mapto not in {'COLOR', 'SPECULARITY', 'ALPHA', 'NORMAL'}:
        print(
            "\tError: Cannot map to %r\n\tassuming diffuse color. modify material %r later." %
            (mapto, material.name)
        )
        mapto = "COLOR"

    if image:
        texture.image = image

    mtex = material.texture_slots.add()
    mtex.texture = texture
    mtex.texture_coords = 'UV'
    mtex.use_map_color_diffuse = False

    mtex.scale = (scale[0], scale[1], 1.0)
    mtex.offset = (offset[0], offset[1], 0.0)

    texture.extension = 'REPEAT'
    if extension == 'mirror':
        # 3DS mirror flag can be emulated by these settings (at least so it seems)
        texture.repeat_x = texture.repeat_y = 2
        texture.use_mirror_x = texture.use_mirror_y = True
    elif extension == 'decal':
        # 3DS' decal mode maps best to Blenders CLIP
        texture.extension = 'CLIP'

    if mapto == 'COLOR':
        mtex.use_map_color_diffuse = True
    elif mapto == 'SPECULARITY':
        mtex.use_map_specular = True
    elif mapto == 'ALPHA':
        mtex.use_map_alpha = True
    elif mapto == 'NORMAL':
        mtex.use_map_normal = True


def skm_to_blender(skm_data, importedObjects, IMAGE_SEARCH):
    from bpy_extras.image_utils import load_image

    contextObName = None
    contextMaterial = None
    contextMatrix_rot = None  # Blender.mathutils.Matrix(); contextMatrix.identity()
    # contextMatrix_tx = None # Blender.mathutils.Matrix(); contextMatrix.identity()

    TEXTURE_DICT = {}
    MATDICT = {}

    def read_texture(texture_path, name, mapto):
        new_texture = bpy.data.textures.new(name, type='IMAGE')

        u_scale, v_scale, u_offset, v_offset = 1.0, 1.0, 0.0, 0.0
        mirror = False
        extension = 'wrap'  # 'mirror', 'decal'

        img = TEXTURE_DICT[contextMaterial.name] = load_image(texture_path, ToEE_data_dir)

        # add the map to the material in the right channel
        if img:
            add_texture_to_material(img, new_texture, (u_scale, v_scale),
                                    (u_offset, v_offset), extension, contextMaterial, mapto)

    def mdf_resolve(mdf_filename):
        mdf_fullpath = os.path.join(ToEE_data_dir, mdf_filename)
        if not os.path.exists(mdf_fullpath):
            print("MDF %s not found" % mdf_fullpath)
            return
        mdf_file = open(mdf_fullpath, 'rb')
        mdf_raw = mdf_file.read().decode()
        mdf_file.close()
        texture_files = mdf_raw.split("\"")
        texture_filepath = texture_files[1]  # TODO handling more than one texture (e.g. phase spiders)
        print("Registering texture: %s" % texture_filepath)
        read_texture(texture_filepath, "Diffuse",
                     "COLOR")  # "Specular / SPECULARITY", "Opacity / ALPHA", "Bump / NORMAL"
        return

    def putContextMesh(skm_data):  # myContextMesh_vertls, myContextMesh_facels, myContextMeshMaterials):
        '''
        Creates Mesh Object from vertex/face/material data
        '''
        # Create new mesh
        bmesh = bpy.data.meshes.new(contextObName)

        vertex_count = len(skm_data.vertex_data)
        face_count = len(skm_data.face_data)
        print("------------ FLAT ----------------")
        print("%d vertices, %d faces" % (vertex_count, face_count))

        # Create vertices
        bmesh.vertices.add(vertex_count)
        flattened_vtx_pos = [t for vtx in skm_data.vertex_data for t in vtx.pos[0:3]]
        bmesh.vertices.foreach_set("co", flattened_vtx_pos)

        # Create faces (Triangles) - make face_count Polygons, each loop defined by 3 vertices
        bmesh.polygons.add(face_count)
        bmesh.loops.add(face_count * 3)
        bmesh.polygons.foreach_set("loop_start", range(0, face_count * 3, 3))
        bmesh.polygons.foreach_set("loop_total", (3,) * face_count)
        flattened_face_vtx_map = [t for fa in skm_data.face_data for t in fa.vertex_ids]
        bmesh.loops.foreach_set("vertex_index", flattened_face_vtx_map)

        # Apply Materials
        for mm in skm_data.material_data:
            mat_name = mm.id.name
            bmat = MATDICT.get(mm.id.name)
            if bmat:
                img = TEXTURE_DICT.get(bmat.name)
            else:
                print(" WARNING! Material %s not defined!" % mat_name)
                bmat = MATDICT[mat_name] = bpy.data.materials.new(mat_name)
                img = None
            bmesh.materials.append(bmat)

        # Get UV coordinates for each polygon's vertices
        print("Setting UVs")
        bmesh.uv_textures.new()
        uv_faces = bmesh.uv_textures.active.data[:]
        if uv_faces:
            for fidx, fa in enumerate(skm_data.face_data):
                bmesh.polygons[fidx].material_index = fa.material_id
                bmat = bmesh.materials[fa.material_id]
                img = TEXTURE_DICT.get(bmat.name)
                uv_faces[fidx].image = img
            uvl = bmesh.uv_layers.active.data[:]
            for fidx, pl in enumerate(bmesh.polygons):
                face = skm_data.face_data[fidx]
                v1, v2, v3 = face.vertex_ids

                uvl[pl.loop_start + 0].uv = skm_data.vertex_data[v1].uv
                uvl[pl.loop_start + 1].uv = skm_data.vertex_data[v2].uv
                uvl[pl.loop_start + 2].uv = skm_data.vertex_data[v3].uv

        # Finish up
        bmesh.validate()
        bmesh.update()

        # Create new object from mesh
        ob = bpy.data.objects.new(contextObName, bmesh)
        object_dictionary[contextObName] = ob
        SCN.objects.link(ob)
        importedObjects.append(ob)

        if contextMatrix_rot:
            ob.matrix_local = contextMatrix_rot
            object_matrix[ob] = contextMatrix_rot.copy()

    def putRig(skm_data):
        '''
        Creates rig object for Mesh Object, and parents it (Armature type parenting, so it deforms it via bones)
        '''
        # Bones
        print("Getting bones")
        obj = object_dictionary[contextObName]
        barm = bpy.data.armatures.new(armatureName)
        rig = bpy.data.objects.new(rigObName, barm)
        SCN.objects.link(rig)
        SCN.objects.active = rig
        rig.select = True
        bpy.ops.object.mode_set(mode='EDIT')  # set to Edit Mode so bones can be added
        bone_dump = open(os.path.join(ToEE_data_dir, "bone_dump.txt"), 'w')

        fh = open("D:/bones.txt", "wt")

        vertex_groups = dict()

        for bone_id, bd in enumerate(skm_data.bone_data):
            bone_name = str(bd.name)
            bone = barm.edit_bones.new(bone_name)  # type: bpy.types.EditBone
            bone.select = True

            wi = bd.world_inverse_matrix
            world = wi.inverted_safe()
            if bd.parent_id != -1:
                bone.parent = barm.edit_bones[bd.parent_id]

            bone.head = Vector([0, 0, 0])
            bone.tail = Vector([0, 0, 1])
            bone.matrix = world

            print("****************************************************************************", file=fh)
            print(bone_name, file=fh)
            print("BONE MATRIX:", file=fh)
            print(bone.matrix, file=fh)
            print("WORLD INVERSE:", file=fh)
            print(world, file=fh)
            print("****************************************************************************", file=fh)

            vg = obj.vertex_groups.new(bone_name)  # Create matching vertex groups
            vertex_groups[bone_id] = vg

        fh.close()
        bone_dump.close()
        bpy.ops.object.mode_set(mode='OBJECT')  # do an implicit update
        # parent obj with rig, using Armaturre type parenting so Bones will deform vertices
        obj.parent = rig
        obj.parent_type = 'ARMATURE'

        print("********************************************************")
        print("BONE WEIGHTS")
        print("********************************************************")

        # Set Vertex bone weights
        for vidx, vtx in enumerate(skm_data.vertex_data):
            attachment_count = len(vtx.attachment_bones)
            for i in range(0, attachment_count):
                bone_id = vtx.attachment_bones[i]
                bone_wt = vtx.attachment_weights[i]
                vertex_groups[bone_id].add((vidx,), bone_wt, 'ADD')

        # object_dictionary[rigObName] = obj
        # rig_dictionary[contextObName] = obj
        importedObjects.append(obj)

    contextObName = "ToEE Model"
    rigObName = "ToEE Rig"
    armatureName = "ToEE Model Skeleton"
    ## Create materials
    for mm in skm_data.material_data:
        contextMaterial = bpy.data.materials.new('Material')
        mdf_path = mm.id.name  # path relative to data_dir (that's how ToEE rolls)
        material_name = mdf_path
        contextMaterial.name = material_name  # material_name.rstrip()
        print("Registering material: %s" % material_name)
        MATDICT[material_name] = contextMaterial
        mdf_resolve(mdf_path)
        if USE_SHADELESS:
            contextMaterial.use_shadeless = True

    # Create Mesh object
    putContextMesh(skm_data)

    # Create Rig
    putRig(skm_data)

    return


class RestBoneState:
    def __init__(self, loc, rot, sca):
        self.loc = loc
        self.rot = rot
        self.sca = sca

    def get_rel_rot(self, rot):
        return self.rot.inverted() * rot

    def get_rel_loc(self, loc):
        return loc - self.loc

    def apply_to_posebone(self, posebone, loc=None, rot=None, sca=None):
        if rot is not None:
            posebone.rotation_quaternion = self.get_rel_rot(rot)
        if loc is not None:
            posebone.location = self.get_rel_loc(loc)


def ska_to_blender(ska_data, skm_data, importedObjects, USE_INHERIT_ROTATION, USE_LOCAL_LOCATION,
                   APPLY_ANIMATIONS):
    print("Importing animations")
    contextObName = "ToEE Model"
    ob = object_dictionary[contextObName]
    rig = ob.parent
    barm = rig.data
    scn = bpy.context.scene

    def dump_bones():
        bone_dump = open(os.path.join(ToEE_data_dir, 'bone_dump_ska.txt'), 'w')
        for ska_bone_id, bd in enumerate(ska_data.bone_data):
            bone_dump.write(
                "\n\n*******  %d %s  ********** " % (ska_bone_id, str(bd.name)) + " Parent: (%d)" % (bd.parent_id))
            bone_dump.write("\n")
            bone_dump.write("Scale vec: " + str(bd.scale))
            bone_dump.write("\n")
            bone_dump.write("Rotation vec: " + str(bd.rotation))
            bone_dump.write("\n")
            bone_dump.write("Translation vec: " + str(bd.translation))
            bone_dump.write("\n")
        bone_dump.close()

    def get_ska_to_skm_bone_map():
        ska_to_skm_bone_mapping = {}  # in some ToEE models not all SKA bones are present in SKM (clothshit? buggy exporter?)
        for ska_idx, ska_bd in enumerate(ska_data.bone_data):
            found = False
            for skm_idx, skm_bd in enumerate(skm_data.bone_data):
                if str(ska_bd.name) == str(skm_bd.name):
                    ska_to_skm_bone_mapping[ska_idx] = skm_idx
                    found = True
                    break
            if not found:
                ska_to_skm_bone_mapping[ska_idx] = -1
                print("Could not find mapping of SKA bone id %d!" % ska_idx)
        return ska_to_skm_bone_mapping

    dump_bones()
    ska_to_skm_bone_mapping = get_ska_to_skm_bone_map()

    # State (loc, rot, sca) for each of the bones in rest position, relative to parent
    bone_rest_state = dict()
    for ska_bone_id, skm_bone_id in ska_to_skm_bone_mapping.items():
        skm_bone = skm_data.bone_data[skm_bone_id]
        rest_world = skm_bone.world_inverse_matrix.inverted()
        if skm_bone.parent_id != -1:
            rest_world = skm_data.bone_data[skm_bone.parent_id].world_inverse_matrix * rest_world
        rest_loc, rest_rot, rest_sca = rest_world.decompose()
        bone_rest_state[ska_bone_id] = RestBoneState(rest_loc, rest_rot, rest_sca)

    anim_count = len(ska_data.animation_data)
    # anim_count = 1  # DEBUG
    rig.animation_data_create()
    bpy.ops.object.mode_set(mode='POSE')

    for ska_idx, ska_bd in enumerate(ska_data.bone_data):
        skm_bone_id = ska_to_skm_bone_mapping[ska_idx]
        if skm_bone_id == -1:
            continue  # Skip bone not present in SKM

        posebone = rig.pose.bones[skm_bone_id]

        rest_state = bone_rest_state[ska_idx]

        # posebone.scale = ska_bd.scale
        rest_state.apply_to_posebone(posebone, loc=ska_bd.translation, rot=ska_bd.rotation)

    for i in range(0, anim_count):
        ad = ska_data.animation_data[i]
        anim_header = ad.header
        action_name = str(anim_header.name)
        action = bpy.data.actions.new(action_name)
        action.use_fake_user = True
        #rig.animation_data.action = action
        stream_count = anim_header.stream_count
        if stream_count <= 0:
            continue
        stream_count = 1  # TODO more than one stream (never happens as far as I've seen?)

        if not APPLY_ANIMATIONS:
            continue

        # Group FCurves by the bone they affect
        curve_groups = dict()

        def get_curve_group(bone_idx):
            if bone_idx in curve_groups:
                return curve_groups[bone_idx].name
            bone_name = str(skm_data.bone_data[bone_idx].name)
            group = action.groups.new(bone_name)
            curve_groups[bone_idx] = group
            return group.name

        for j in range(0, stream_count):
            stream = ad.streams[j]  # type: SkaAnimStream

            for bone_idx, keyframes in stream.scale_channels.items():
                pass

            for bone_idx, keyframes in stream.rotation_channels.items():
                skm_bone_idx = ska_to_skm_bone_mapping[bone_idx]
                rest_pose = bone_rest_state[skm_bone_idx]

                posebone = rig.pose.bones[skm_bone_idx]
                prop = posebone.path_from_id("rotation_quaternion")
                group = get_curve_group(skm_bone_idx)
                curve_w = action.fcurves.new(prop, index=0, action_group=group)
                curve_x = action.fcurves.new(prop, index=1, action_group=group)
                curve_y = action.fcurves.new(prop, index=2, action_group=group)
                curve_z = action.fcurves.new(prop, index=3, action_group=group)
                for frame, rotation in keyframes:
                    # Transform rotation to be relative to rest pose
                    rotation = rest_pose.get_rel_rot(rotation)

                    kf = curve_w.keyframe_points.insert(1 + frame, rotation.w, {'FAST'})
                    kf.interpolation = 'LINEAR'
                    kf = curve_x.keyframe_points.insert(1 + frame, rotation.x, {'FAST'})
                    kf.interpolation = 'LINEAR'
                    kf = curve_y.keyframe_points.insert(1 + frame, rotation.y, {'FAST'})
                    kf.interpolation = 'LINEAR'
                    kf = curve_z.keyframe_points.insert(1 + frame, rotation.z, {'FAST'})
                    kf.interpolation = 'LINEAR'

                curve_w.update()
                curve_x.update()
                curve_y.update()
                curve_z.update()

            for bone_idx, keyframes in stream.location_channels.items():
                skm_bone_idx = ska_to_skm_bone_mapping[bone_idx]
                rest_pose = bone_rest_state[skm_bone_idx]

                posebone = rig.pose.bones[skm_bone_idx]
                prop = posebone.path_from_id("location")
                group = get_curve_group(skm_bone_idx)
                curve_x = action.fcurves.new(prop, index=0, action_group=group)
                curve_y = action.fcurves.new(prop, index=1, action_group=group)
                curve_z = action.fcurves.new(prop, index=2, action_group=group)
                for frame, location in keyframes:
                    # Transform location to be relative to rest pose
                    location = rest_pose.get_rel_loc(location)

                    kf = curve_x.keyframe_points.insert(1 + frame, location.x, {'FAST'})
                    kf.interpolation = 'LINEAR'
                    kf = curve_y.keyframe_points.insert(1 + frame, location.y, {'FAST'})
                    kf.interpolation = 'LINEAR'
                    kf = curve_z.keyframe_points.insert(1 + frame, location.z, {'FAST'})
                    kf.interpolation = 'LINEAR'

                curve_x.update()
                curve_y.update()
                curve_z.update()


def get_ToEE_data_dir(filepath):
    '''
    Gets the ToEE data dir, assuming filepath is of the form
    <ToEE data dir>\\art\\etc
    '''
    import re
    data_dir = os.path.abspath(filepath)
    data_dir = os.path.dirname(data_dir)
    data_dir = data_dir.replace("\\", "/")
    data_dir = re.split("/art", data_dir, flags=re.IGNORECASE)[0]
    return data_dir


def get_skm_filepath(ska_filepath):
    import re
    skm_filepath = re.split(".ska", ska_filepath, flags=re.IGNORECASE)[0] + '.SKM'
    return skm_filepath


def load_ska(filepath, context, IMPORT_CONSTRAIN_BOUNDS=10.0,
             IMAGE_SEARCH=True,
             APPLY_MATRIX=True,
             USE_INHERIT_ROTATION=True,
             USE_LOCAL_LOCATION=True,
             APPLY_ANIMATIONS=False,
             global_matrix=None):
    global SCN, ToEE_data_dir

    # XXX
    # 	if BPyMessages.Error_NoFile(filepath):
    # 		return
    time1 = time.clock()  # for timing the import duration

    print("importing SKA: %r..." % (filepath), end="")
    # filepath = 'D:/GOG Games/ToEECo8/data/art/meshes/Monsters/Giants/Hill_Giants/Hill_Giant_2/Zomb_giant_2.SKA'
    ska_filepath = filepath
    skm_filepath = get_skm_filepath(ska_filepath)

    if bpy.ops.object.select_all.poll():
        bpy.ops.object.select_all(action='DESELECT')

    ToEE_data_dir = get_ToEE_data_dir(filepath)
    print("Data dir: %s", ToEE_data_dir)

    # Read data into intermediate SkmFile and SkaFile objects
    skm_data = SkmFile()
    ska_data = SkaFile()

    # SKM file
    with open(skm_filepath, 'rb') as file:
        print('Opened file: ', skm_filepath)
        skm_data.read(file)

    # SKA file
    with open(ska_filepath, 'rb') as file:
        print('Opened file: ', ska_filepath)
        ska_data.read(file)

    if IMPORT_CONSTRAIN_BOUNDS:
        BOUNDS_SKA[:] = [1 << 30, 1 << 30, 1 << 30, -1 << 30, -1 << 30, -1 << 30]
    else:
        del BOUNDS_SKA[:]

    # fixme, make unglobal, clear in case
    object_dictionary.clear()
    object_matrix.clear()

    scn = context.scene
    # 	scn = bpy.data.scenes.active
    SCN = scn
    # SCN_OBJECTS = scn.objects
    # SCN_OBJECTS.selected = [] # de select all

    importedObjects = []  # Fill this list with objects
    skm_to_blender(skm_data, importedObjects, IMAGE_SEARCH)
    ska_to_blender(ska_data, skm_data, importedObjects, USE_INHERIT_ROTATION, USE_LOCAL_LOCATION,
                   APPLY_ANIMATIONS)
    # fixme, make unglobal
    object_dictionary.clear()
    object_matrix.clear()

    if APPLY_MATRIX:
        for ob in importedObjects:
            if ob.type == 'MESH':
                me = ob.data
                me.transform(ob.matrix_local.inverted())

    # print(importedObjects)
    if global_matrix:
        for ob in importedObjects:
            if ob.parent is None:
                ob.matrix_world = ob.matrix_world * global_matrix

    for ob in importedObjects:
        ob.select = True

    # Done DUMMYVERT
    """
    if IMPORT_AS_INSTANCE:
        name = filepath.split('\\')[-1].split('/')[-1]
        # Create a group for this import.
        group_scn = Scene.New(name)
        for ob in importedObjects:
            group_scn.link(ob) # dont worry about the layers

        grp = Blender.Group.New(name)
        grp.objects = importedObjects

        grp_ob = Object.New('Empty', name)
        grp_ob.enableDupGroup = True
        grp_ob.DupGroup = grp
        scn.link(grp_ob)
        grp_ob.Layers = Layers
        grp_ob.sel = 1
    else:
        # Select all imported objects.
        for ob in importedObjects:
            scn.link(ob)
            ob.Layers = Layers
            ob.sel = 1
    """

    context.scene.update()

    axis_min = [1000000000] * 3
    axis_max = [-1000000000] * 3
    global_clamp_size = IMPORT_CONSTRAIN_BOUNDS
    if global_clamp_size != 0.0:
        # Get all object bounds
        for ob in importedObjects:
            for v in ob.bound_box:
                for axis, value in enumerate(v):
                    if axis_min[axis] > value:
                        axis_min[axis] = value
                    if axis_max[axis] < value:
                        axis_max[axis] = value

        # Scale objects
        max_axis = max(axis_max[0] - axis_min[0],
                       axis_max[1] - axis_min[1],
                       axis_max[2] - axis_min[2])
        scale = 1.0

        while global_clamp_size < max_axis * scale:
            scale = scale / 10.0

        scale_mat = mathutils.Matrix.Scale(scale, 4)

        for obj in importedObjects:
            if obj.parent is None:
                obj.matrix_world = scale_mat * obj.matrix_world

    # Select all new objects.
    print(" done in %.4f sec." % (time.clock() - time1))


def load(operator, context, filepath="",
         constrain_size=0.0,
         use_image_search=True,
         use_apply_transform=True,
         use_inherit_rot=True,
         use_local_location=True,
         apply_animations=True,
         global_matrix=None,
         ):
    load_ska(filepath, context, IMPORT_CONSTRAIN_BOUNDS=constrain_size,
             IMAGE_SEARCH=use_image_search,
             APPLY_MATRIX=use_apply_transform,
             USE_INHERIT_ROTATION=use_inherit_rot,
             USE_LOCAL_LOCATION=use_local_location,
             APPLY_ANIMATIONS=apply_animations,
             global_matrix=global_matrix,
             )

    return {'FINISHED'}
