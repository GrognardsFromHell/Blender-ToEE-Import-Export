import struct
import time
from io import BytesIO
from typing import List

import mathutils
from mathutils import Vector, Quaternion

def write_short(file, data):
    file.write( struct.pack("<h", data))

def write_short_list(file, data):
    file.write( struct.pack("<%dh" % len(data), *data))

def write_float_list(file, data):
    file.write( struct.pack("<%df" % len(data), *data))

def matrix4_to_3x4_array(mat):
    """Concatenate matrix's columns into a single, flat tuple"""
    return tuple(f for v in mat[0:3] for f in v)

class FixedLengthName(object):
    __slots__ = "name", "size"

    def __init__(self, Name="", Size=48):
        if len(Name) == 0:
            self.name = ""
        else:
            self.name = Name
        self.size = Size
        assert len(self.name) <= Size, "FixedLengthName: must be shorter than Size (%d)!" % Size

    def from_raw_data(self, rawdata):
        self.name = rawdata.split(b'\0')[0].decode()

    def get_size(self):
        return self.size

    def write(self, file):
        
        b_name = bytes(self.name.encode() )
        name_len = len(b_name)
        file.write(b_name)
        for p in range(0, self.size - name_len):
            file.write(b'\0')

    def __str__(self):
        return str(self.name)


class SkaBone(object):
    __slots__ = "flags", "parent_id", "name", "scale", "rotation", "translation"
    flags: int
    parent_id: int
    name: FixedLengthName
    scale: mathutils.Vector
    rotation: mathutils.Vector
    translation: mathutils.Vector

    def __init__(self, Name="", Parent_id=0):
        self.flags = 0
        self.parent_id = Parent_id
        self.name = FixedLengthName(Name, 40)

    def from_raw_data(self, rawdata):
        self.flags = struct.unpack('<h', rawdata[0:2])[0]
        self.parent_id = struct.unpack('<h', rawdata[2:4])[0]
        self.name.from_raw_data(rawdata[4:44])
        # print(self.name.name)
        field2c = struct.unpack('<i', rawdata[44:48])[0]
        field30 = struct.unpack('<i', rawdata[48:52])[0]
        if field30 != 0 or field2c != 0:
            print('interesting! field2c = ', field2c)
        scale = struct.unpack('<4f', rawdata[52:52 + 16])
        self.scale = mathutils.Vector(scale[0:3])
        rotation = struct.unpack('<4f', rawdata[52 + 16:52 + 32])
        self.rotation = mathutils.Quaternion([rotation[3], rotation[0], rotation[1], rotation[2]])
        translation = struct.unpack('<4f', rawdata[52 + 32:52 + 48])
        self.translation = mathutils.Vector(translation[0:3])

    def write(self, file):
        write_short(file, self.flags) 
        write_short(file, self.parent_id)
        self.name.write(file)
        self.scale.write(file)
        self.rotation.write(file)
        self.translation.write(file)

    @staticmethod
    def get_size():
        return 100

    def __str__(self):
        return self.name.__str__()


class SkmBone:
    def __init__(self, Name="", Parent_id=0):
        self.flags = 0
        self.parent_id = Parent_id
        self.name = FixedLengthName(Name, 48)
        self.world_inverse = [[0, 0, 0, 0] for i in range(0, 3)]  # 3x4 matrix (3x3 rotation, 3x1 translation)

    @property
    def world_inverse_matrix(self):
        return mathutils.Matrix(self.world_inverse + [[0, 0, 0, 1]])

    def from_raw_data(self, rawdata):
        self.flags = struct.unpack('<h', rawdata[0:2])[0]
        self.parent_id = struct.unpack('<h', rawdata[2:4])[0]
        self.name.from_raw_data(rawdata[4:52])
        tmp = struct.unpack('<12f', rawdata[52:52 + 48])
        self.world_inverse = [tmp[i * 4:(i + 1) * 4] for i in range(0, 3)] 
        # [ [t0...t3],
        #   [t4...t7],
        #   [t8..t11] ]
        return

    def write(self, file):
        write_short(file, self.flags) 
        write_short(file, self.parent_id)
        self.name.write(file)
        write_float_list(file, self.world_inverse)

    @staticmethod
    def get_size():
        return 100

    def __str__(self):
        return self.name.__str__()


class SkmMaterial(object):
    '''
    id - path relative to ToEE data dir
    '''
    __slots__ = ['id']
    id: FixedLengthName

    def __init__(self, id=""):
        self.id = FixedLengthName(id, 128)

    def from_raw_data(self, rawdata):
        self.id.from_raw_data(rawdata)

    def write(self, file):
        self.id.write(file)
    @staticmethod
    def get_size():
        return 128

class MdfFile(object):
    __slots__ = ['texture_filepath']
    texture_filepath: str

    def __init__(self):
        self.texture_filepath = ''
        return

    def from_raw_data(self, rawdata):
        decoded = rawdata.decode()
        texture_files = decoded.split("\"")
        if len(texture_files) < 2:
            raise Exception('No texture set in MDF!')
        if len(texture_files) > 3:
            print('Unhandled MDF 2nd texture!')
            # TODO handling more than one texture (e.g. phase spiders)
        
        self.texture_filepath = texture_files[1]
        return
    def write(self, file):
        file.write("Textured\n")
        file.write("Texture \"")
        file.write(self.texture_filepath)
        file.write("\"\n")
        return
    

class SkaAnimKeyframeBoneData(object):
    __slots__ = "bone_id", "flags", "frame", "scale_next_frame", "scale", "rotation_next_frame", "rotation", "translation_next_frame", "translation"

    def __init__(self):
        self.bone_id = -1
        self.flags = 0
        self.frame = -1
        self.scale_next_frame = -1
        self.rotation_next_frame = -1
        self.translation_next_frame = -1
        self.scale = mathutils.Vector([1, 1, 1])
        self.rotation = mathutils.Quaternion()  # X,Y,Z, scalar
        self.translation = mathutils.Vector([0, 0, 0])

    def has_scale_data(self):
        if self.frame < 0:
            return True
        if self.flags & 8:
            return True
        return False

    def has_rot_data(self):
        if self.frame < 0:
            return True
        if self.flags & 4:
            return True
        return False

    def has_trans_data(self):
        if self.frame < 0:
            return True
        if self.flags & 2:
            return True
        return False

    @staticmethod
    def get_size():
        return 22


class SkaAnimStreamHeader(object):
    __slots__ = "frame_count", "variation_id", "frame_rate", "dps", "data_offset"

    def __init__(self):
        self.frame_count = 0
        self.variation_id = 0
        self.frame_rate = 1.0
        self.dps = 30.0
        self.data_offset = 0

    def from_raw_data(self, rawdata):
        self.frame_count = struct.unpack('<H', rawdata[0:2])[0]
        self.variation_id = struct.unpack('<h', rawdata[2:4])[0]
        self.frame_rate = struct.unpack('<f', rawdata[4:8])[0]
        self.dps = struct.unpack('<f', rawdata[8:12])[0]
        self.data_offset = struct.unpack('<i', rawdata[12:16])[0]

    @staticmethod
    def get_size():
        return 2 + 2 + 4 + 4 + 4


class SkaAnimStreamInstance:
    """
    An animation stream which is an actual physical keyframe stream
    can be instanced multiple times within an animation file.
    I.e., unarmed_unarmed_rturn might just be identical to sword_sword_rturn
    in terms of keyframes, but might for example be played at a different speed.
    """

    def __init__(self, name, frame_rate, dps):
        self.name = name
        self.frame_rate = frame_rate
        self.dps = dps


class SkaAnimStream:
    def __init__(self, name):
        """
        :type data: BytesIO
        :type header: SkaAnimStreamHeader
        """
        self.name = name
        self.instances = []

        self.scale_channels = dict()
        self.rotation_channels = dict()
        self.location_channels = dict()

    def add_instance(self, instance):
        """
        :rtype: SkaAnimStreamInstance
        """
        self.instances.append(instance)

    def read(self, data):
        """
        :type data: BytesIO
        """

        (scale_factor, location_factor) = struct.unpack("<ff", data.read(8))
        rotation_factor = 1 / 32767.0

        scale_channels = dict()
        rotation_channels = dict()
        location_channels = dict()

        # Unpack into stream of shorts
        def next_short():
            return struct.unpack("<h", data.read(2))[0]

        def next_scale():
            (x, y, z) = struct.unpack("<hhh", data.read(3 * 2))
            return Vector([
                x * scale_factor,
                y * scale_factor,
                z * scale_factor
            ])

        def next_rotation():
            (x, y, z, w) = struct.unpack("<hhhh", data.read(4 * 2))
            return Quaternion([
                w * rotation_factor,
                x * rotation_factor,
                y * rotation_factor,
                z * rotation_factor
            ])

        def next_location():
            (x, y, z) = struct.unpack("<hhh", data.read(3 * 2))
            return Vector([
                x * location_factor,
                y * location_factor,
                z * location_factor
            ])

        # Read frame 0 for all affected bones
        bone_idx = next_short()
        while bone_idx >= 0:
            scale_channels[bone_idx] = [(0, next_scale())]
            rotation_channels[bone_idx] = [(0, next_rotation())]
            location_channels[bone_idx] = [(0, next_location())]

            bone_idx = next_short()

        # begin reading actual keyframes        
        hdr = next_short()
        while hdr & 1 == 0:
            frame = hdr >> 1
            if frame == -1:
                break

            hdr = next_short()
            while hdr & 1 == 1:
                bone_idx = hdr >> 4
                channels_used = (hdr >> 1) & 7

                if channels_used & 4:
                    channel_frame = next_short()
                    scale_channels[bone_idx].append((channel_frame, next_scale()))

                if channels_used & 2:
                    channel_frame = next_short()
                    rotation_channels[bone_idx].append((channel_frame, next_rotation()))

                if channels_used & 1:
                    channel_frame = next_short()
                    location_channels[bone_idx].append((channel_frame, next_location()))

                hdr = next_short()

        self.scale_channels = scale_channels
        self.rotation_channels = rotation_channels
        self.location_channels = location_channels

class SkaEvent(object):
    __slots__ = "frame_id", "type", "action"

    def __init__(self, frame_id=0, event_type="", action=""):
        self.frame_id = frame_id
        self.type = FixedLengthName(event_type, 48)
        self.action = FixedLengthName(action, 128)

    @staticmethod
    def from_raw_data(rawdata, count):
        result = []
        max_count = len(rawdata) / SkaEvent.get_size()
        if count < max_count:
            count = max_count
        DATUM_SIZE = SkaEvent.get_size()
        for i in range(0, count):
            new_event = SkaEvent()
            new_event.frame_id = struct.unpack('<h', rawdata[0 + i * DATUM_SIZE:2 + i * DATUM_SIZE])[0]
            new_event.type.from_raw_data(rawdata[2 + i * DATUM_SIZE:2 + 48 + i * DATUM_SIZE])
            new_event.action.from_raw_data(rawdata[50 + i * DATUM_SIZE:50 + 128 + i * DATUM_SIZE])
            result.append(new_event)
        return result

    @staticmethod
    def get_size():
        return 2 + 48 + 128


class SkaAnimHeader(object):
    __slots__ = "name", "drive_type", "loopable", "event_count", "event_offset", "stream_count", "unk", "stream_headers"

    def __init__(self, name=""):
        self.name = FixedLengthName(name, 64)
        self.drive_type = 0
        self.loopable = 0
        self.event_count = 0
        self.event_offset = 0
        self.stream_count = 0
        self.stream_headers = []

    def from_raw_data(self, rawdata):
        self.name.from_raw_data(rawdata[0:64])
        self.drive_type = struct.unpack('<b', rawdata[64:65])[0]
        self.loopable = struct.unpack('<b', rawdata[65:66])[0]
        self.event_count = struct.unpack('<h', rawdata[66:68])[0]
        self.event_offset = struct.unpack('<i', rawdata[68:72])[0]
        self.stream_count = struct.unpack('<h', rawdata[72:74])[0]
        unk = struct.unpack('<h', rawdata[74:76])[0]
        self.stream_headers = []
        for i in range(0, 10):
            new_stream_header = SkaAnimStreamHeader()
            DATUM_SIZE = SkaAnimStreamHeader.get_size()
            offset = 76 + i * DATUM_SIZE
            new_stream_header.from_raw_data(rawdata[offset:offset + DATUM_SIZE])
            if i < self.stream_count:
                self.stream_headers.append(new_stream_header)

    @staticmethod
    def get_size():
        return 64 + 1 + 1 + 2 + 4 + 2 + 2 + 10 * SkaAnimStreamHeader.get_size()


class SkaAnim(object):
    __slots__ = "header", "events", "streams"
    header: SkaAnimHeader
    def __init__(self):
        self.header = SkaAnimHeader()
        self.events = []
        self.streams = []

    def from_raw_data(self, rawdata):
        self.header.from_raw_data(rawdata)

    def get_size(self):
        return self.header.get_size() + 2 + 4


class SkaFile:
    streams = ...  # type: List[SkaAnimStream]
    bone_data: List[SkaBone]
    def __init__(self):
        self.bone_data = []
        self.variation_data = []
        self.animation_data = []
        self.streams = []
        self._fileraw = b""

    def read(self, file):

        time1 = time.clock()

        self._fileraw = file.read()
        self.get_bone_data()
        self.get_variation_data()
        self.read_animation_data()
        print(" done in %.2f sec." % (time.clock() - time1))

    def get_bone_data(self):
        count = struct.unpack('<i', self._fileraw[0:4])[0]
        offset = struct.unpack('<i', self._fileraw[4:8])[0]
        print(count, 'bones, offset: ', offset)

        DATUM_SIZE = SkaBone.get_size()
        for i in range(0, count):
            data_start = offset + DATUM_SIZE * i
            newDatum = SkaBone()
            newDatum.from_raw_data(self._fileraw[data_start:data_start + DATUM_SIZE])
            self.bone_data.append(newDatum)

    def get_variation_data(self):
        count = struct.unpack('<i', self._fileraw[8:12])[0]
        offset = struct.unpack('<i', self._fileraw[12:16])[0]
        # do nothing, because it seems ToEE doesn't have this in practice

    def read_animation_data(self):
        count = struct.unpack('<i', self._fileraw[16:20])[0]
        offset = struct.unpack('<i', self._fileraw[20:24])[0]

        # Streams are reused between animations
        streams_by_start = dict()

        # get data headers first
        HEADER_SIZE = SkaAnimHeader.get_size()
        EVENT_SIZE = SkaEvent.get_size()
        data_start = offset
        for i in range(0, count):

            newDatum = SkaAnim()
            newDatum.header = SkaAnimHeader()
            newDatum.header.from_raw_data(self._fileraw[data_start:data_start + HEADER_SIZE])

            # events
            event_offset = data_start + newDatum.header.event_offset
            event_count = newDatum.header.event_count

            if event_count > 0:
                newDatum.events = SkaEvent.from_raw_data(
                    self._fileraw[event_offset:event_offset + event_count * EVENT_SIZE], event_count)

            newDatum.streams = []
            for stream_header in newDatum.header.stream_headers:

                stream_start = data_start + stream_header.data_offset
                if stream_start not in streams_by_start:
                    stream = SkaAnimStream(newDatum.header.name)
                    io = BytesIO(self._fileraw)
                    io.seek(stream_start)
                    stream.read(io)
                    streams_by_start[stream_start] = stream
                else:
                    stream = streams_by_start[stream_start]

                stream.instances.append(SkaAnimStreamInstance(
                    str(newDatum.header.name),
                    stream_header.frame_rate,
                    stream_header.dps
                ))
                newDatum.streams.append(stream)

            self.animation_data.append(newDatum)

            data_start += HEADER_SIZE

        self.streams = streams_by_start.values()

        return

    def write(self, file):
        # first write the header

        # bone data
        bone_count = len(self.bone_data)
        bone_data_offset = 24  # always 24
        file.write(struct.pack("<2i", bone_count, bone_data_offset))
        self.write_bones(file)

        # #variation data
        variation_count = len(self.variation_data)
        variation_data_offset = bone_data_offset + self.get_bone_data_length()
        file.write(struct.pack("<2i", variation_count, variation_data_offset))
        # shouldn't actually have data here, heh

        # animation data
        animation_count = len(self.animation_data)
        animation_data_offset = variation_data_offset + self.get_variation_data_length()  #
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


class SkmVertex(object):
    __slots__ = "pos", "normal", "uv", "attachment_bones", "attachment_weights"
    pos: List[float]
    normal: List[float]
    uv: List[float]
    attachment_bones: List[int]
    attachment_weights: List[float]

    def __init__(self):
        self.pos = []
        self.normal = []
        self.uv = []
        self.attachment_bones = []
        self.attachment_weights = []

    @property
    def attachment_count(self):
        return len(self.attachment_bones)

    def from_raw_data(self, rawdata):
        self.pos = struct.unpack('<4f', rawdata[0:0 + 16])
        self.normal = struct.unpack('<4f', rawdata[0 + 16:0 + 32])
        self.uv = struct.unpack('<2f', rawdata[0 + 32:0 + 40])
        dummy = struct.unpack('<h', rawdata[40:42])[0]
        # if dummy != 0:
            # print('sheeit')
        attachment_count = struct.unpack('<h', rawdata[42:44])[0]
        if attachment_count > 6:
            raise Exception("SkmVertex: Unexcepted number of attachments read!")
        attachment_count = max(0, min(attachment_count, 6))
        self.attachment_bones = []
        self.attachment_bones = struct.unpack("<%dh" % attachment_count, rawdata[44:44 + attachment_count * 2])
        self.attachment_weights = struct.unpack("<%df" % attachment_count,
                                                rawdata[44 + 12:44 + 12 + attachment_count * 4])

    def write(self, file):
        write_float_list(file, self.pos)
        write_float_list(file, self.normal)
        write_float_list(file, self.uv)
        
        file.write( struct.pack('<h', 0) )
        file.write( struct.pack('<h', self.attachment_count) )

        write_short_list( file, self.attachment_bones + [0 for _ in range(self.attachment_count, 6)] )
        write_float_list( file, self.attachment_weights + [0.0 for _ in range(self.attachment_count, 6)] )
        return

    @staticmethod
    def get_size():
        return 80


class SkmFace(object):
    __slots__ = "material_id", "vertex_ids"
    material_id: int
    vertex_ids: List[int]
    def from_raw_data(self, rawdata):
        self.material_id = struct.unpack('<h', rawdata[0:2])[0]
        self.vertex_ids = struct.unpack('<3h', rawdata[2:8])

    def write(self, file):
        write_short(file, self.material_id)
        write_short_list(file, self.vertex_ids)
        return
    
    @staticmethod
    def get_size():
        return 8


class SkmFile(object):
    __slots__ = ["bone_data", "material_data",
                 "vertex_data", "face_data",
                 "_fileraw", "_dataidx"]
    bone_data: List[SkmBone]
    material_data: List[SkmMaterial]
    vertex_data: List[SkmVertex]
    face_data: List[SkmFace]
    
    def __init__(self):
        self.bone_data = []
        self.material_data = []
        self.vertex_data = []
        self.face_data = []

    def read(self, file):
        self._fileraw = file.read()
        self.get_bone_data()
        self.get_material_data()
        self.get_vertex_data()
        self.get_face_data()

    # methods for converting raw binary to basic model data
    def get_face_data(self):
        count = struct.unpack('<i', self._fileraw[24:28])[0]
        offset = struct.unpack('<i', self._fileraw[28:32])[0]
        print(count, 'faces, offset: ', offset)
        DATUM_SIZE = SkmFace.get_size()
        for i in range(0, count):
            data_start = offset + DATUM_SIZE * i
            newDatum = SkmFace()
            newDatum.from_raw_data(self._fileraw[data_start:data_start + DATUM_SIZE])
            self.face_data.append(newDatum)

    def get_vertex_data(self):
        count = struct.unpack('<i', self._fileraw[16:20])[0]
        offset = struct.unpack('<i', self._fileraw[20:24])[0]
        print(count, 'vertices, offset: ', offset)

        DATUM_SIZE = SkmVertex.get_size()
        for i in range(0, count):
            data_start = offset + DATUM_SIZE * i
            newDatum = SkmVertex()
            newDatum.from_raw_data(self._fileraw[data_start:data_start + DATUM_SIZE])
            self.vertex_data.append(newDatum)

    def get_material_data(self):
        self.material_data = []
        count = struct.unpack('<i', self._fileraw[8:12])[0]
        offset = struct.unpack('<i', self._fileraw[12:16])[0]
        print(count, 'materials, offset: ', offset)

        DATUM_SIZE = SkmMaterial.get_size()
        for i in range(0, count):
            data_start = offset + DATUM_SIZE * i
            newDatum = SkmMaterial()
            newDatum.from_raw_data(self._fileraw[data_start:data_start + DATUM_SIZE])
            self.material_data.append(newDatum)
    
    def write_bones(self, file):
        for bd in self.bone_data:
            bd.write(file)
        return

    def write_materials(self, file):
        for skm_mat in self.material_data:
            skm_mat.write(file)
        return
    
    def write_vertices(self,file):
        for vertex in self.vertex_data:
            vertex.write(file)
        return
    
    def write_faces(self, file):
        for face in self.face_data:
            face.write(file)
        return

    def get_bone_data(self):
        bone_count = struct.unpack('<i', self._fileraw[0:4])[0]
        bone_offset = struct.unpack('<i', self._fileraw[4:8])[0]
        print(bone_count, 'bones, offset: ', bone_offset)

        DATUM_SIZE = SkmBone.get_size()
        for i in range(0, bone_count):
            bone_start = bone_offset + DATUM_SIZE * i
            newbone = SkmBone()
            newbone.from_raw_data(self._fileraw[bone_start:bone_start + DATUM_SIZE])
            self.bone_data.append(newbone)

    def write(self, file):
        BONE_DATA_OFFSET = 40  # always 24
        
        # first write the header

        # bone header data
        bone_count = len(self.bone_data)
        file.write(struct.pack("<2i", bone_count, BONE_DATA_OFFSET)) # 0:8
        bone_data_size = self.get_bone_data_length()
        
        # material header data
        material_count = len(self.material_data)
        material_data_offset = BONE_DATA_OFFSET + bone_data_size
        file.write(struct.pack("<2i", material_count, material_data_offset)) # 8:16
        material_data_size = self.get_material_data_length()

        # vertex header data
        vertex_count = len(self.vertex_data)
        vertex_data_offset = material_data_offset + material_data_size
        file.write(struct.pack("<2i", vertex_count, vertex_data_offset)) # 16:24
        vertex_data_size = self.get_vertex_data_length()
        
        # face header data
        face_count = len(self.face_data)
        face_data_offset = vertex_data_offset + vertex_data_size
        file.write(struct.pack("<2i", face_count, face_data_offset)) # 24:32
        face_data_size = self.get_face_data_length()

        # write some more dummy stuff I guess
        file.write(struct.pack("<2i", 0, 0)) # 32:40

        # *** write data ***
        self.write_bones(file)
        self.write_materials(file)
        self.write_vertices(file)
        self.write_faces(file)

    def get_bone_data_length(self):
        return len(self.bone_data) * SkmBone.get_size()

    def get_material_data_length(self):
        return len(self.material_data) * SkmMaterial.get_size()

    def get_vertex_data_length(self):
        return len(self.vertex_data) * SkmVertex.get_size()

    def get_face_data_length(self):
        return len(self.face_data) * SkmFace.get_size()    


    def add_bone(self, new_bone):
        self.bone_data.append(new_bone)


def main():
    skm_data = SkmFile()
    filepath = 'D:/GOG Games/ToEECo8/data/art/meshes/Monsters/Giants/Hill_Giants/Hill_Giant_2/Zomb_giant_2.SKA'
    ska_filepath = filepath
    skm_filepath = ska_filepath.split('.SKA')[0] + '.SKM'

    # read SKM file
    file = open(skm_filepath, 'rb')
    print('Opened file: ', skm_filepath)
    skm_data.read(file)
    file.close()

    # read SKA file
    ska_data = SkaFile()
    file = open(ska_filepath, 'rb')
    print('Opened file: ', ska_filepath)
    ska_data.read(file)

    print(str(len(ska_data.streams)) + " Streams")
    print(str(len(ska_data.animation_data)) + " Anims")

    file.close()

    return


if __name__ == '__main__':
    main()
