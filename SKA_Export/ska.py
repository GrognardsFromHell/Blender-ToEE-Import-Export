import struct
import time
from io import BytesIO
from typing import List

import mathutils
from mathutils import Vector, Quaternion


class FixedLengthName(object):
    __slots__ = "name", "size"

    def __init__(self, Name="", Size=48):
        if len(Name) == 0:
            self.name = Name
        else:
            self.name = ""
        self.size = Size
        # check if larger than 48 characters?

    def from_raw_data(self, rawdata):
        self.name = rawdata.split(b'\0')[0].decode()

    def get_size(self):
        return self.size

    def write(self, file):
        name_len = len(self.name)
        file.write(self.name)
        for p in range(0, self.size - name_len):
            file.write('\0')

    def __str__(self):
        return str(self.name)


class SkaBone(object):
    __slots__ = "flags", "parent_id", "name", "scale", "rotation", "translation"

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
        self.flags.write(file)
        self.parent_id.write(file)
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

    def write(self, file):
        self.flags.write(file)
        self.parent_id.write(file)
        self.name.write(file)
        self.world_inverse.write(file)

    @staticmethod
    def get_size():
        return 100

    def __str__(self):
        return self.name.__str__()


class SkmMaterial(object):
    __slots__ = ['id']

    def __init__(self, id=""):
        self.id = FixedLengthName(id, 128)

    def from_raw_data(self, rawdata):
        self.id.from_raw_data(rawdata)

    @staticmethod
    def get_size():
        return 128


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

    def from_raw_data(self, rawdata):
        self.pos = struct.unpack('<4f', rawdata[0:0 + 16])
        self.normal = struct.unpack('<4f', rawdata[0 + 16:0 + 32])
        self.uv = struct.unpack('<2f', rawdata[0 + 32:0 + 40])
        attachment_count = struct.unpack('<h', rawdata[42:44])[0]
        if attachment_count > 6:
            print('wtf')
        attachment_count = max(0, min(attachment_count, 6))
        self.attachment_bones = []
        self.attachment_bones = struct.unpack("<%dh" % attachment_count, rawdata[44:44 + attachment_count * 2])
        self.attachment_weights = struct.unpack("<%df" % attachment_count,
                                                rawdata[44 + 12:44 + 12 + attachment_count * 4])

    @staticmethod
    def get_size():
        return 80


class SkmFace(object):
    __slots__ = "material_id", "vertex_ids"

    def from_raw_data(self, rawdata):
        self.material_id = struct.unpack('<h', rawdata[0:2])[0]
        self.vertex_ids = struct.unpack('<3h', rawdata[2:8])

    @staticmethod
    def get_size():
        return 8


class SkmFile(object):
    __slots__ = ["bone_data", "material_data",
                 "vertex_data", "face_data",
                 "_fileraw", "_dataidx"]

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
        DATUM_SIZE = 8
        for i in range(0, count):
            data_start = offset + DATUM_SIZE * i
            newDatum = SkmFace()
            newDatum.from_raw_data(self._fileraw[data_start:data_start + DATUM_SIZE])
            self.face_data.append(newDatum)

    def get_vertex_data(self):
        count = struct.unpack('<i', self._fileraw[16:20])[0]
        offset = struct.unpack('<i', self._fileraw[20:24])[0]
        print(count, 'vertices, offset: ', offset)

        DATUM_SIZE = 80
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

        DATUM_SIZE = 128
        for i in range(0, count):
            data_start = offset + DATUM_SIZE * i
            newDatum = SkmMaterial()
            newDatum.from_raw_data(self._fileraw[data_start:data_start + DATUM_SIZE])
            self.material_data.append(newDatum)

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
        # first write the header

        # bone data
        bone_count = len(self.bone_data)
        bone_data_offset = 24  # always 24
        file.write(struct.pack("<2i", bone_count, bone_data_offset))
        self.write_bones(file)

        # material data
        material_count = len(self.material_data)
        material_data_offset = bone_data_offset + self.get_bone_data_length()
        file.write(struct.pack("<2i", material_count, material_data_offset))

        # *** write data ***

    def get_bone_data_length(self):
        return len(self.bone_data) * 100

    def get_material_data_length(self):
        return len(self.material_data) * 128

    def write_bones(self, file):
        for bd in self.bone_data:
            bd.write(file)

    def add_bone(self, new_bone):
        self.bone_data.append(new_bone)


def main():
    skm_data = SkmFile()
    filepath = r"D:\Blender-ToEE-Import-Export\PC_Human_Male\PC_Human_Male.ska"
    ska_filepath = filepath
    skm_filepath = ska_filepath.split('.ska')[0] + '.skm'

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
