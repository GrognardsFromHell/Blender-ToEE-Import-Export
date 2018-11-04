if "bpy" in locals():
    import importlib
    if "export_ska" in locals():
        importlib.reload(export_ska)
    if "import_ska" in locals():
        importlib.reload(import_ska)

import bpy

from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        StringProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper_factory,
        axis_conversion,
        )


bl_info = {
    "name": "SKA Importer/Exporter",
    "author": "Cattletech",
    "blender": (2, 78, 0),
    "location": "File > Import-Export",
    "description": "Export SKA format: animations",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
                "Scripts/Import-Export/Autodesk_3DS",
    "support": 'UNOFFICIAL',
    "category": "Import-Export"}
    
IO3DSOrientationHelper = orientation_helper_factory("IO3DSOrientationHelper", axis_forward='Y', axis_up='Z')

class ImportSKA(bpy.types.Operator, ImportHelper, IO3DSOrientationHelper):
    """Import from ToEE's Skeletal Animation file formats (.ska, .skm)"""
    bl_idname = "import.ska_file"
    bl_label = 'Import SKA Data'
    bl_options = {'UNDO'}

    filename_ext = ".ska"
    filter_glob = StringProperty(default="*.ska", options={'HIDDEN'})

    constrain_size = FloatProperty(
            name="Size Constraint",
            description="Scale the model by 10 until it reaches the "
                        "size constraint (0 to disable)",
            min=0.0, max=1000.0,
            soft_min=0.0, soft_max=1000.0,
            default=0.0,
            )
    use_image_search = BoolProperty(
            name="Image Search",
            description="Search subdirectories for any associated images "
                        "(Warning, may be slow)",
            default=True,
            )
    use_apply_transform = BoolProperty(
            name="Apply Transform",
            description="Workaround for object transformations "
                        "importing incorrectly",
            default=True,
            )
    use_inherit_rot = BoolProperty(
            name="Use Inherit Rotation",
            description="Set Inherit Rotation on bone children ",
            default=True,
            )
    use_local_location = BoolProperty(
            name="Use Local Location",
            description="Set Local Location on bone children ",
            default=True,
            )
    apply_animations = BoolProperty(
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
        result = import_ska.load(self, context, **keywords)
        print("Done.")
        return result

class SkaExport(bpy.types.Operator, ExportHelper, IO3DSOrientationHelper):
    """Export animation to ToEE's SKA (Skeletal Animation) format"""
    bl_idname = "export.ska_file"
    bl_label = "Export SKA Data"

    filename_ext = ".ska"
    filter_glob = StringProperty(
            default="*.ska",
            options={'HIDDEN'},
            )
            
    use_selection = BoolProperty(
            name="Selection Only",
            description="Export selected objects only",
            default=False,
            )
    
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")

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


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(SkaExport.bl_idname, text="ToEE animation (.SKA)")

def menu_func_import(self, context):
    self.layout.operator(ImportSKA.bl_idname, text="ToEE animation (.SKA)")

# Register and add to the file selector
bpy.utils.register_class(SkaExport)
bpy.utils.register_class(ImportSKA)

try:
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
finally:
    print("ha")
try:
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
finally:
    print("ha")

bpy.types.INFO_MT_file_export.append(menu_func_export)
bpy.types.INFO_MT_file_import.append(menu_func_import)


# test call
#bpy.ops.export.some_data('INVOKE_DEFAULT')