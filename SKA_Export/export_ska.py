import struct
import os
import bpy
import mathutils    
from bpy_extras import io_utils, node_shader_utils
import time
from bpy_extras.wm_utils.progress_report import (
    ProgressReport,
    ProgressReportSubstep,
)

from .ska import FixedLengthName, SkmFile, SkmBone, SkmMaterial, SkaFile, SkaBone, MdfFile, SkmVertex, SkmFace

progress = None

def matrix4_to_3x4_array(mat):
    """Concatenate matrix's columns into a single, flat tuple"""
    return tuple(f for v in mat[0:3] for f in v)

def vector_to_array(vec):
    result = tuple(f for f in vec)
    return result

def mat_to_mdf_file(mat_wrap, mdf_file_path):
    mdf_file = MdfFile()

    # source_dir = os.path.dirname(bpy.data.filepath)
    # dest_dir   = os.path.dirname(filepath)

    # Currently supporting only mat_wrap.base_color_texture
    mat_wrap_key = 'base_color_texture'
    tex_wrap = getattr(mat_wrap, mat_wrap_key, None)
    if tex_wrap is None:
        return
    image = tex_wrap.image
    if image is None:
        return
    
    mdf_file.texture_filepath = image.filepath
    # path_mode = 'AUTO'
    # filepath = io_utils.path_reference(image.filepath, source_dir, dest_dir,
    #                                                 path_mode, "", copy_set, image.library)
    
    def proc_node_tex(nodetex):
        # TODO handle texture scaling & translation
        tex_offset = nodetex.translation
        tex_scale  = nodetex.scale
        tex_coord  = nodetex.texcoords
        assert tex_offset[0] == 0.0
        assert tex_offset[1] == 0.0
        assert tex_offset[2] == 0.0
        assert tex_scale[0] == 1.0
        assert tex_scale[1] == 1.0
        assert tex_scale[2] == 1.0
        assert tex_coord == 'UV'
        return

    proc_node_tex(mat_wrap.base_color_texture)
    # elif mapto == 'SPECULARITY':
    #     _generic_tex_set(mat_wrap.specular_texture, image, 'UV', tex_offset, tex_scale)
    # elif mapto == 'ALPHA':
    #     _generic_tex_set(mat_wrap.alpha_texture, image, 'UV', tex_offset, tex_scale)
    # elif mapto == 'NORMAL':
    #     _generic_tex_set(mat_wrap.normalmap_texture, image, 'UV', tex_offset, tex_scale)

    with open(mdf_file_path, 'w') as file:
        mdf_file.write(file)

    return
    


def blender_to_skm(mesh, rig, WRITE_MDF):
    skm_data = SkmFile()

    contextMaterial = None
    context_mat_wrap = None
    contextMatrix_rot = None

    contextObName = "ToEE Model"
    rigObName = "ToEE Rig"
    armatureName = "ToEE Model Skeleton"

    TEXTURE_DICT = {}
    MATDICT = {}
    WRAPDICT = {}
    copy_set = set() # set of files to copy (texture images...)
    
        
    def mesh_to_skm_mesh(skm_data):  # myContextMesh_vertls, myContextMesh_facels, myContextMeshMaterials):
        '''
        Creates Mesh Object from vertex/face/material data
        '''
        bmesh = bpy.data.meshes['ToEE Model']

        vertex_count = len(bmesh.vertices)
        face_count   = len(bmesh.polygons)

        print("%d vertices, %d faces" % (vertex_count, face_count))

        # Create vertices
        for vtx in bmesh.vertices:
            skm_vtx = SkmVertex()
            skm_vtx.pos = vtx.co.to_tuple() + (0.0,)
            skm_vtx.normal = vtx.normal.to_tuple() + (0.0,)
            skm_data.vertex_data.append(skm_vtx)
        assert len(skm_data.vertex_data) == vertex_count

        # Create faces (Triangles). Note: face should be triangles only!
        for p in bmesh.polygons:
            loop_start = p.loop_start
            loop_total = p.loop_total
            assert loop_total == 3, "Faces must be triangles!"
            face = bmesh.loops[loop_start+0].vertex_index, bmesh.loops[loop_start+1].vertex_index, bmesh.loops[loop_start+2].vertex_index
            skm_face = SkmFace()
            skm_face.vertex_ids = face
            skm_data.face_data.append(skm_face)
        assert len(skm_data.face_data) == face_count

        
        # Get UV coordinates for each polygon's vertices
        print("Setting UVs")
        uvl = bmesh.uv_layers[0].data[:]
        for fidx, fa in enumerate(skm_data.face_data):
            fa.material_id = bmesh.polygons[fidx].material_index

        for fidx, pl in enumerate(bmesh.polygons):
            face = skm_data.face_data[fidx]
            v1, v2, v3 = face.vertex_ids

            skm_data.vertex_data[v1].uv = uvl[pl.loop_start + 0].uv
            skm_data.vertex_data[v2].uv = uvl[pl.loop_start + 1].uv 
            skm_data.vertex_data[v3].uv = uvl[pl.loop_start + 2].uv
        
    def rig_to_skm_bones(skm_data):
        '''
        Converts rig/armature objects to SKM Bones
        '''
        # Bones
        print("Getting bones")
        obj = bpy.data.objects[contextObName]
        barm = bpy.data.armatures[armatureName]
        rig = bpy.data.objects[rigObName]
        
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')  # set to Edit Mode so bones can be accessed

        bone_ids = {}

        for bone_id, bone in enumerate(barm.edit_bones):
            bone_name = bone.name
            bone_ids[bone_name] = bone_id

            skm_bone = SkmBone(Name = bone_name)

            if bone.parent is None:
                skm_bone.parent_id = -1
            else:
                skm_bone.parent_id = bone_ids[bone.parent.name]

            world = bone.matrix
            wi = world.inverted_safe()
            skm_bone.world_inverse = matrix4_to_3x4_array(wi)

            skm_data.bone_data.append(skm_bone)
        
        # Exit edit mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        
        for vidx, vtx in enumerate(obj.data.vertices):
            for i, vg in enumerate(vtx.groups):
                bone_id = vg.group
                bone_wt = vg.weight
                skm_data.vertex_data[vidx].attachment_bones.append(bone_id)
                skm_data.vertex_data[vidx].attachment_weights.append(bone_wt)
        
        return
    
    def material_to_skm_mat(mat_wrap, mdf_file_path):
        skm_mat = SkmMaterial(mdf_file_path)
        return skm_mat

    ## Create materials
    progress.enter_substeps(3, "Processing data...")
    progress.step("Processing Materials and images...")
    for mm in bpy.data.materials: #skm_data.material_data:  

        material_name = mm.name
        if not material_name.lower().endswith('mdf'):
            print('Skipping material whose name doesn\'t end with .mdf: %r' % material_name)
            continue

        assert mm.use_nodes, "export_ska assumes use_nodes = True!"
        contextMaterial = mm

        mat_wrap = node_shader_utils.PrincipledBSDFWrapper(contextMaterial, is_readonly=False)
        assert mat_wrap.use_nodes == True, "huh? no use_nodes in wrapper?"
        context_mat_wrap = mat_wrap


        
        print("Converting material to SKM format: %s" % material_name)

        skm_mat = material_to_skm_mat(mat_wrap, material_name)
        if WRITE_MDF:
            mat_to_mdf_file(mat_wrap, skm_mat.id)

        MATDICT[material_name] = contextMaterial
        WRAPDICT[contextMaterial] = context_mat_wrap
        
        skm_data.material_data.append(skm_mat)


    # Convert Mesh object
    progress.step("Processing Mesh...")
    mesh_to_skm_mesh(skm_data)

    # Create Rig
    progress.step("Processing Rig...")
    rig_to_skm_bones(skm_data)

    # copy all collected files.
    io_utils.path_reference_copy(copy_set)

    progress.leave_substeps("Finished SKM conversion.")
    return skm_data




def _write(context, filepath, 
    EXPORT_ANIMATION = False,
    WRITE_MDF = False,
    global_matrix = None):
    global progress
    from bpy_extras.io_utils import create_derived_objects, free_derived_objects
    

    with ProgressReport(context.window_manager) as progress:
        
        base_name, ext = os.path.splitext(filepath)
        context_name = [base_name, '', '', ext] # Base name, scene name, frame number, extension

        depsgraph = context.evaluated_depsgraph_get()
        scene = context.scene

        # Exit edit mode before exporting, so current object states are exported properly.
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        orig_frame = scene.frame_current

        # Export an animation?
        if EXPORT_ANIMATION:
            scene_frames = range(scene.frame_start, scene.frame_end + 1)  # Up to and including the end frame.
        else:
            scene_frames = [orig_frame]  # Dont export an animation.
        
        mesh = bpy.context.scene.objects['ToEE Model']
        rig = bpy.context.scene.objects['ToEE Rig']
        skm_data = blender_to_skm(mesh, rig, WRITE_MDF)
        
        
        skm_filepath = os.path.splitext(filepath)[0] + '.skm'
        with open(skm_filepath, 'wb') as skm_file:
            skm_data.write(skm_file)
    
    
    """Save the Blender scene animation to a ToEE format SKA file.\
    This contains bones and keyframe animations.
    """
    print("\n*** Exporting SKA ***")
    # Time the export
    time1 = time.clock()
    # Blender.Window.WaitCursor(1)
    
    if global_matrix is None:
        global_matrix = mathutils.Matrix()

    scene = context.scene

    objects = (ob for ob in scene.objects if ob.visible_get())

    # for ob in objects:
    #     # get derived objects
    #     print("object: " + str(ob))
    #     free, derived = create_derived_objects(scene, ob)
        
    #     if derived is None:
    #         continue

    #     print( "derived obj: " + str(derived) + "\n")
        
    #     for ob_derived, mat in derived:
    #         if ob.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
    #             continue

    #         try:
    #             data = ob_derived.to_mesh(scene, True, 'PREVIEW')
    #         except:
    #             data = None

    #         if data:
    #             matrix = global_matrix * mat
    #             data.transform(matrix)
    #             # todo
    #     if free:
    #         free_derived_objects(ob)

    # # Open the file for writing:
    # file = open(filepath, 'wb')

    # # Recursively write the chunks to file:
    # # primary.write(file)

    # # Close the file:
    # file.close()

    # Debugging only: report the exporting time:
    # Blender.Window.WaitCursor(0)
    print("SKA export time: %.2f" % (time.clock() - time1))
    return

def save(operator, context, filepath="", use_selection=True, global_matrix=None,):
    _write(context, filepath)
    return {'FINISHED'}
