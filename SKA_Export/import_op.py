
# if "bpy" in locals():
#     import importlib
#     if "import_ska" in locals():
#         importlib.reload(import_ska)

import bpy
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper,
        axis_conversion,
        )

@orientation_helper(axis_forward='Y', axis_up='Z')
class ImportSKA(bpy.types.Operator, ImportHelper):
    """Import from ToEE's shit Skeletal Animation file formats (.ska, .skm)"""
    bl_idname = "import.ska_file"
    bl_label = 'Import SKA Data'
    bl_options = {'REGISTER','UNDO'}

    filename_ext = ".ska"
    filter_glob: StringProperty(
            default="*.ska",
            options={'HIDDEN'},
            )

    constrain_size: FloatProperty(
            name="Size Constraint",
            description="Scale the model by 10 until it reaches the "
                        "size constraint (0 to disable)",
            min=0.0, max=1000.0,
            soft_min=0.0, soft_max=1000.0,
            default=0.0,
            )
    use_image_search: BoolProperty(
            name="Image Search",
            description="Search subdirectories for any associated images "
                        "(Warning, may be slow)",
            default=True,
            )
    use_apply_transform: BoolProperty(
            name="Apply Transform",
            description="Workaround for object transformations "
                        "importing incorrectly",
            default=True,
            )
    use_inherit_rot: BoolProperty(
            name="Use Inherit Rotation",
            description="Set Inherit Rotation on bone children ",
            default=True,
            )
    use_local_location: BoolProperty(
            name="Use Local Location",
            description="Set Local Location on bone children ",
            default=True,
            )
    apply_animations: BoolProperty(
            name="Apply Animations",
            description="Ignores all keyframes (only uses the stuff in SKA bone)",
            default=True,
            )
    def execute(self, context):
        from . import import_ska

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix
        result = import_ska.blender_load_ska(self, context, **keywords)
        print("Done.")
        return result
    def draw(self, context):
        pass


@orientation_helper(axis_forward='Y', axis_up='Z')
class ImportSKM(bpy.types.Operator, ImportHelper):
    """Import from ToEE's Skeletal Animation Mesh file format (.skm)"""
    bl_idname = "import.skm_file"
    bl_label = 'Import SKM Data'
    bl_options = {'REGISTER','UNDO'}

    filename_ext = ".skm"
    filter_glob: StringProperty(
            default="*.skm",
            options={'HIDDEN'},
            )

    use_image_search: BoolProperty(
            name="Image Search",
            description="Search subdirectories for any associated images "
                        "(Warning, may be slow)",
            default=True,
            )
    def execute(self, context):
        from . import import_ska

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))

        global_matrix = axis_conversion(from_forward=self.axis_forward,
                                        from_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix
        result = import_ska.blender_load_skm(self, context, **keywords)
        print("Done.")
        return result
    def draw(self, context):
        pass


class SKA_PT_import_include(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Include"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_SCENE_OT_ska"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, 'use_image_search')

class SKA_PT_import_options(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Options"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_OT_ska_file"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "apply_animations")
        layout.prop(operator, "axis_forward")
        layout.prop(operator, "axis_up")


def menu_func_import_ska(self, context):
    self.layout.operator(ImportSKA.bl_idname, text="ToEE animation (.SKA + .SKM)")

def menu_func_import_skm(self, context):
    self.layout.operator(ImportSKM.bl_idname, text="ToEE mesh (.SKM)")

def register():
#     print('Registering GITHUB/SKA_Import/import_op.py')
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_ska)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_skm)

def unregister():
#     print('Unregistering GITHUB/SKA_Import/import_op.py!')
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_ska)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_skm)