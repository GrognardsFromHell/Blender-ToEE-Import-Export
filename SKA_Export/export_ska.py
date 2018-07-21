
# <pep8 compliant>

######################################################
# Data Structures
######################################################

import struct

# size defines:
SZ_SHORT = 2
SZ_INT = 4
SZ_FLOAT = 4


class _3ds_ushort(object):
    """Class representing a short (2-byte integer) for a 3ds file.
    *** This looks like an unsigned short H is unsigned from the struct docs - Cam***"""
    __slots__ = ("value", )

    def __init__(self, val=0):
        self.value = val

    def get_size(self):
        return SZ_SHORT

    def write(self, file):
        file.write(struct.pack("<H", self.value))

    def __str__(self):
        return str(self.value)


class _3ds_int(object):
    """Class representing an int (4-byte integer) for a 3ds file."""
    __slots__ = ("value", )

    def __init__(self, val):
        self.value = val

    def get_size(self):
        return SZ_INT

    def write(self, file):
        file.write(struct.pack("<i", self.value))

    def __str__(self):
        return str(self.value)

class _3ds_uint(object):
    """Class representing an unsigned int (4-byte integer) for a 3ds file."""
    __slots__ = ("value", )

    def __init__(self, val):
        self.value = val

    def get_size(self):
        return SZ_INT

    def write(self, file):
        file.write(struct.pack("<I", self.value))

    def __str__(self):
        return str(self.value)


class _3ds_float(object):
    """Class representing a 4-byte IEEE floating point number for a 3ds file."""
    __slots__ = ("value", )

    def __init__(self, val):
        self.value = val

    def get_size(self):
        return SZ_FLOAT

    def write(self, file):
        file.write(struct.pack("<f", self.value))

    def __str__(self):
        return str(self.value)


class _3ds_string(object):
    """Class representing a zero-terminated string for a 3ds file."""
    __slots__ = ("value", )

    def __init__(self, val):
        assert(type(val) == bytes)
        self.value = val

    def get_size(self):
        return (len(self.value) + 1)

    def write(self, file):
        binary_format = "<%ds" % (len(self.value) + 1)
        file.write(struct.pack(binary_format, self.value))

    def __str__(self):
        return self.value


class _3ds_point_3d(object):
    """Class representing a three-dimensional point for a 3ds file."""
    __slots__ = "x", "y", "z"

    def __init__(self, point):
        self.x, self.y, self.z = point

    def get_size(self):
        return 3 * SZ_FLOAT

    def write(self, file):
        file.write(struct.pack('<3f', self.x, self.y, self.z))

    def __str__(self):
        return '(%f, %f, %f)' % (self.x, self.y, self.z)

# Used for writing a track

class _3ds_point_4d(object):
    """Class representing a four-dimensional point for a 3ds file, for instance a quaternion."""
    __slots__ = "x","y","z","w"
    def __init__(self, point=(0.0,0.0,0.0,0.0)):
        self.x, self.y, self.z, self.w = point

    def get_size(self):
        return 4*SZ_FLOAT

    def write(self,file):
        data=struct.pack('<4f', self.x, self.y, self.z, self.w)
        file.write(data)

    def __str__(self):
        return '(%f, %f, %f, %f)' % (self.x, self.y, self.z, self.w)



class _3ds_point_uv(object):
    """Class representing a UV-coordinate for a 3ds file."""
    __slots__ = ("uv", )

    def __init__(self, point):
        self.uv = point

    def get_size(self):
        return 2 * SZ_FLOAT

    def write(self, file):
        data = struct.pack('<2f', self.uv[0], self.uv[1])
        file.write(data)

    def __str__(self):
        return '(%g, %g)' % self.uv



class _3ds_rgb_color(object):
    """Class representing a (24-bit) rgb color for a 3ds file."""
    __slots__ = "r", "g", "b"

    def __init__(self, col):
        self.r, self.g, self.b = col

    def get_size(self):
        return 3

    def write(self, file):
        file.write(struct.pack('<3B', int(255 * self.r), int(255 * self.g), int(255 * self.b)))

    def __str__(self):
        return '{%f, %f, %f}' % (self.r, self.g, self.b)


class _3ds_face(object):
    """Class representing a face for a 3ds file."""
    __slots__ = ("vindex", )

    def __init__(self, vindex):
        self.vindex = vindex

    def get_size(self):
        return 4 * SZ_SHORT

    # no need to validate every face vert. the oversized array will
    # catch this problem

    def write(self, file):
        # The last zero is only used by 3d studio
        file.write(struct.pack("<4H", self.vindex[0], self.vindex[1], self.vindex[2], 0))

    def __str__(self):
        return "[%d %d %d]" % (self.vindex[0], self.vindex[1], self.vindex[2])


class _3ds_array(object):
    """Class representing an array of variables for a 3ds file.

    Consists of a _3ds_ushort to indicate the number of items, followed by the items themselves.
    """
    __slots__ = "values", "size"

    def __init__(self):
        self.values = []
        self.size = SZ_SHORT

    # add an item:
    def add(self, item):
        self.values.append(item)
        self.size += item.get_size()

    def get_size(self):
        return self.size

    def validate(self):
        return len(self.values) <= 65535

    def write(self, file):
        _3ds_ushort(len(self.values)).write(file)
        for value in self.values:
            value.write(file)

    # To not overwhelm the output in a dump, a _3ds_array only
    # outputs the number of items, not all of the actual items.
    def __str__(self):
        return '(%d items)' % len(self.values)


class _3ds_named_variable(object):
    """Convenience class for named variables."""

    __slots__ = "value", "name"

    def __init__(self, name, val=None):
        self.name = name
        self.value = val

    def get_size(self):
        if self.value is None:
            return 0
        else:
            return self.value.get_size()

    def write(self, file):
        if self.value is not None:
            self.value.write(file)

    def dump(self, indent):
        if self.value is not None:
            print(indent * " ",
                  self.name if self.name else "[unnamed]",
                  " = ",
                  self.value)


                  
class SkaBoneName(object):
    __slots__ = "name"
    
    def __init__(self, Name = ""):
        self.name = Name
        # check if larger than 48 characters?
        
    def write(self, file):
        name_len = len(self.name)
        file.write(self.name)
        for p in range(0, 48 - name_len):
            file.write('\0')
    
    def __str__(self):
        return str(self.name)

class SkaBone(object):
    __slots__ = "flags", "parent_id", "name", "scale", "rotation", "translation"
    
    def __init__(self, Name = "", Parent_id = 0):
        self.flags = _3ds_ushort(0)
        self.parent_id = _3ds_ushort(Parent_id)
        self.name = SkaBoneName(Name)
        
    
    def write(self, file):
        self.flags.write(file)
        self.parent_id.write(file)
        self.name.write(file)
        self.scale.write(file)
        self.rotation.write(file)
        self.translation.write(file)
        
    def get_size(self):
        return 100
        
    def __str__(self):
        return self.name.__str__()
                  
class SkaFile(object):
    __slots__ = "bone_data", "variation_data", "animation_data"
    
    def __init__(self):
        self.bone_data = []
        self.variation_data = []
        self.animation_data = []
        
    def write(self, file):
        # first write the header
        
        # bone data
        bone_count = len(self.bone_data)
        bone_data_offset = 24 # always 24
        file.write(struct.pack("<2i", bone_count, bone_data_offset))
        self.write_bones(file)
        
        # #variation data
        variation_count = len(self.variation_data)
        variation_data_offset = bone_data_offset + get_bone_data_length()
        file.write(struct.pack("<2i", variation_count, variation_data_offset))
        # shouldn't actually have data here, heh
        
        # animation data
        animation_count = len(self.animation_data)
        animation_data_offset = variation_data_offset + get_variation_data_length() #
        file.write(struct.pack("<2i", animation_count, animation_data_offset))
        
        
        # *** write data ***
    
    def get_bone_data_length(self):
        return len(self.bone_data) * 100
        
    def get_variation_data_length(self):
        return len(self.variation_data) * 0
    
    def write_bones(self, file):
        for bd in self.bone_data:
            bd.write(file)
    
    def add_bone(self, new_bone):
        self.bone_data.append(new_bone)
    
#the chunk class
class _3ds_chunk(object):
    """Class representing a chunk in a 3ds file.

    Chunks contain zero or more variables, followed by zero or more subchunks.
    """
    __slots__ = "ID", "size", "variables", "subchunks"

    def __init__(self, chunk_id=0):
        self.ID = _3ds_ushort(chunk_id)
        self.size = _3ds_uint(0)
        self.variables = []
        self.subchunks = []

    def add_variable(self, name, var):
        """Add a named variable.

        The name is mostly for debugging purposes."""
        self.variables.append(_3ds_named_variable(name, var))

    def add_subchunk(self, chunk):
        """Add a subchunk."""
        self.subchunks.append(chunk)

    def get_size(self):
        """Calculate the size of the chunk and return it.

        The sizes of the variables and subchunks are used to determine this chunk\'s size."""
        tmpsize = self.ID.get_size() + self.size.get_size()
        for variable in self.variables:
            tmpsize += variable.get_size()
        for subchunk in self.subchunks:
            tmpsize += subchunk.get_size()
        self.size.value = tmpsize
        return self.size.value

    def validate(self):
        for var in self.variables:
            func = getattr(var.value, "validate", None)
            if (func is not None) and not func():
                return False

        for chunk in self.subchunks:
            func = getattr(chunk, "validate", None)
            if (func is not None) and not func():
                return False

        return True

    def write(self, file):
        """Write the chunk to a file.

        Uses the write function of the variables and the subchunks to do the actual work."""
        #write header
        self.ID.write(file)
        self.size.write(file)
        for variable in self.variables:
            variable.write(file)
        for subchunk in self.subchunks:
            subchunk.write(file)

    def dump(self, indent=0):
        """Write the chunk to a file.

        Dump is used for debugging purposes, to dump the contents of a chunk to the standard output.
        Uses the dump function of the named variables and the subchunks to do the actual work."""
        print(indent * " ",
              "ID=%r" % hex(self.ID.value),
              "size=%r" % self.get_size())
        for variable in self.variables:
            variable.dump(indent + 1)
        for subchunk in self.subchunks:
            subchunk.dump(indent + 1)


        
def make_kfdata(start=0, stop=0, curtime=0):
    """Make the basic keyframe data chunk"""
    kfhdr.add_variable("animlen", _3ds_uint(stop-start))

    kfseg.add_variable("start", _3ds_uint(start))
    kfseg.add_variable("stop", _3ds_uint(stop))

    kfcurtime.add_variable("curtime", _3ds_uint(curtime))

    return kfdata

def make_track_chunk(obj):
    """Make a chunk for track data.

    Depending on the ID, this will construct a position, rotation or scale track."""
    track_chunk.add_variable("track_flags", _3ds_ushort())
    track_chunk.add_variable("nkeys", _3ds_uint(1))
    # Next section should be repeated for every keyframe, but for now, animation is not actually supported.
    track_chunk.add_variable("tcb_frame", _3ds_uint(0))
    track_chunk.add_variable("tcb_flags", _3ds_ushort())
    
    
    obj.type
    
    translation = obj.getLocation() # 3 vector
    q           = obj.getEuler().to_quaternion()  # XXX, todo!
    rotation    = _3ds_point_4d((q.angle, q.axis[0], q.axis[1], q.axis[2]))
    scale       = obj.getSize() # 3 vector scale
    
    
    
    
    if obj.type=='Empty':
        asdf = 1
    else:
        # meshes have their transformations applied before
        # exporting, so write identity transforms here:
        translation = _3ds_point_3d((0.0,0.0,0.0))
        rotation    = _3ds_point_4d((0.0, 1.0, 0.0, 0.0))
        scale       = _3ds_point_3d((1.0, 1.0, 1.0))

    return track_chunk

def make_kf_obj_node(obj, name_to_id):
    """Make a node chunk for a Blender object.

    Takes the Blender object as a parameter. Object id's are taken from the dictionary name_to_id.
    Blender Empty objects are converted to dummy nodes."""

    name = obj.name
    # main object node chunk:
    kf_obj_node = _3ds_chunk(KFDATA_OBJECT_NODE_TAG)
    # chunk for the object id:
    obj_id_chunk = _3ds_chunk(OBJECT_NODE_ID)
    # object id is from the name_to_id dictionary:
    obj_id_chunk.add_variable("node_id", _3ds_ushort(name_to_id[name]))

    # object node header:
    obj_node_header_chunk = _3ds_chunk(OBJECT_NODE_HDR)
    # object name:
    if obj.type == 'Empty':
        # Empties are called "$$$DUMMY" and use the OBJECT_INSTANCE_NAME chunk
        # for their name (see below):
        obj_node_header_chunk.add_variable("name", _3ds_string("$$$DUMMY"))
    else:
        # Add the name:
        obj_node_header_chunk.add_variable("name", _3ds_string(sane_name(name)))
    # Add Flag variables (not sure what they do):
    obj_node_header_chunk.add_variable("flags1", _3ds_ushort(0))
    obj_node_header_chunk.add_variable("flags2", _3ds_ushort(0))

    # Check parent-child relationships:
    parent = obj.parent
    if (parent is None) or (parent.name not in name_to_id):
        # If no parent, or the parents name is not in the name_to_id dictionary,
        # parent id becomes -1:
        obj_node_header_chunk.add_variable("parent", _3ds_ushort(-1))
    else:
        # Get the parent's id from the name_to_id dictionary:
        obj_node_header_chunk.add_variable("parent", _3ds_ushort(name_to_id[parent.name]))

    # Add pivot chunk:
    obj_pivot_chunk = _3ds_chunk(OBJECT_PIVOT)
    obj_pivot_chunk.add_variable("pivot", _3ds_point_3d(obj.getLocation()))
    kf_obj_node.add_subchunk(obj_pivot_chunk)

    # add subchunks for object id and node header:
    kf_obj_node.add_subchunk(obj_id_chunk)
    kf_obj_node.add_subchunk(obj_node_header_chunk)

    # Empty objects need to have an extra chunk for the instance name:
    if obj.type == 'Empty':
        obj_instance_name_chunk = _3ds_chunk(OBJECT_INSTANCE_NAME)
        obj_instance_name_chunk.add_variable("name", _3ds_string(sane_name(name)))
        kf_obj_node.add_subchunk(obj_instance_name_chunk)

    # Add track chunks for position, rotation and scale:
    kf_obj_node.add_subchunk(make_track_chunk(POS_TRACK_TAG, obj))
    kf_obj_node.add_subchunk(make_track_chunk(ROT_TRACK_TAG, obj))
    kf_obj_node.add_subchunk(make_track_chunk(SCL_TRACK_TAG, obj))

    return kf_obj_node


def save(operator, context, filepath="", use_selection=True, global_matrix=None,):
    import bpy
    import mathutils
    
    import time
    from bpy_extras.io_utils import create_derived_objects, free_derived_objects
    
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

    if use_selection:
        objects = (ob for ob in scene.objects if ob.is_visible(scene) and ob.select)
    else:
        objects = (ob for ob in scene.objects if ob.is_visible(scene))

    for ob in objects:
        # get derived objects
        print("object: " + str(ob))
        free, derived = create_derived_objects(scene, ob)
        
        if derived is None:
            continue

        print( "derived obj: " + str(derived) + "\n")
        
        for ob_derived, mat in derived:
            if ob.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
                continue

            try:
                data = ob_derived.to_mesh(scene, True, 'PREVIEW')
            except:
                data = None

            if data:
                matrix = global_matrix * mat
                data.transform(matrix)
                # todo
        if free:
            free_derived_objects(ob)

    # Open the file for writing:
    file = open(filepath, 'wb')

    # Recursively write the chunks to file:
    # primary.write(file)

    # Close the file:
    file.close()

    # Debugging only: report the exporting time:
    # Blender.Window.WaitCursor(0)
    print("SKA export time: %.2f" % (time.clock() - time1))
    
    return {'FINISHED'}
