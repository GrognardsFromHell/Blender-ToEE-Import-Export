
# if "bpy" in locals():
#     import importlib
#     if "export_ska" in locals():
#         importlib.reload(export_ska)

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
class SkaExport(bpy.types.Operator, ExportHelper):
    """Export animation to ToEE's SKA (Skeletal Animation) format"""
    bl_idname = "export.ska_file"
    bl_label = "Export SKA Data"

    filename_ext = ".ska"
    filter_glob: StringProperty(
            default="*.ska",
            options={'HIDDEN'},
            )
            
    use_selection: BoolProperty(
            name="Selection Only",
            description="Export selected objects only",
            default=False,
            )
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
    
        from . import export_ska
        
        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            "check_existing",
                                            ))
        global_matrix = axis_conversion(to_forward=self.axis_forward,
                                        to_up=self.axis_up,
                                        ).to_4x4()
        keywords["global_matrix"] = global_matrix

        return export_ska.save(self, context, **keywords)
        
        #file = open(self.filepath, 'w')
        #file.write("Hello World " + context.object.name)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def menu_func_export(self, context):
    self.layout.operator(SkaExport.bl_idname, text="ToEE animation (.SKA)")


def register():
    # print('Registering GITHUB/SKA_Import/export_op.py')
    # Register and add to the file selector
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)



def unregister():
    # print('Unregistering GITHUB/SKA_Import/export_op.py!')
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)