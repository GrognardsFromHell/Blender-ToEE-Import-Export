import struct
import time

class FixedLengthName(object):
    __slots__ = "name", "size"
    
    def __init__(self, Name = "", Size = 48):
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
    
    def __init__(self, Name = "", Parent_id = 0):
        self.flags = 0
        self.parent_id = Parent_id
        self.name = FixedLengthName(Name, 40)
        
    def from_raw_data(self, rawdata):
        self.flags     = struct.unpack('<h', rawdata[0:2])[0]
        self.parent_id = struct.unpack('<h', rawdata[2:4])[0]
        self.name.from_raw_data(rawdata[4:44])
        #print(self.name.name)
        field2c   = struct.unpack('<i', rawdata[44:48])[0]
        field30   = struct.unpack('<i', rawdata[48:52])[0]
        if field30 != 0 or field2c != 0:
            print('interesting! field2c = ', field2c)
        self.scale       = struct.unpack('<4f', rawdata[52:52+16])
        self.rotation    = struct.unpack('<4f', rawdata[52+16:52+32])
        self.translation = struct.unpack('<4f', rawdata[52+32:52+48])

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

class SkmBone(object):
    __slots__ = "flags", "parent_id", "name", "world_inverse"
    
    def __init__(self, Name = "", Parent_id = 0):
        self.flags = 0
        self.parent_id = Parent_id
        self.name = FixedLengthName(Name, 48)
        self.world_inverse = [ [0,0,0,0] for i in range(0,3)] # 3x4 matrix (3x3 rotation, 3x1 translation)
        
    def from_raw_data(self, rawdata):
        self.flags         = struct.unpack('<h', rawdata[0:2])[0]
        self.parent_id     = struct.unpack('<h', rawdata[2:4])[0]
        self.name.from_raw_data(rawdata[4:52])
        tmp                = struct.unpack('<12f', rawdata[52:52+48])
        self.world_inverse = [ tmp[i*4:(i+1)*4] for i in range(0,3)]

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
    def __init__(self, id = ""):
        self.id = FixedLengthName(id, 128)
    def from_raw_data(self, rawdata):
        self.id.from_raw_data(rawdata)
    @staticmethod
    def get_size():
        return 128

class SkaAnimKeyframeBoneData(object):
    __slots__ = "bone_id", "flags", "frame", "scale_next_frame","scale", "rotation_next_frame", "rotation", "translation_next_frame", "translation"
    def __init__(self):
        self.bone_id = -1
        self.flags = 0
        self.frame = -1
        self.scale_next_frame = -1
        self.rotation_next_frame = -1
        self.translation_next_frame = -1
        self.scale = [1, 1, 1]
        self.rotation = [0,0,0,0] # X,Y,Z, scalar
        self.translation = [0, 0, 0]
    def from_raw_data(self, rawdata):
        self.bone_id     = struct.unpack('<h',rawdata[0:2])[0]
        if  not (self.bone_id < 0):
            self.scale       = struct.unpack('<3h',rawdata[2:8])
            self.rotation    = struct.unpack('<4h',rawdata[8:16])
            self.translation = struct.unpack('<3h',rawdata[16:22])
            self.frame = -1
            self.scale_next_frame = -1
            self.rotation_next_frame = -1
            self.translation_next_frame = -1
            self.flags = 0
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

class SkaAnimKeyframeSet(object):
    __slots__ = "scale_factor", "translation_factor", "bone_start_data", "keyframes"
    def __init(self):
        self.scale_factor = 1.0
        self.translation_factor = 1.0
        self.bone_start_data = []
        self.keyframes = { 0: []} # kf : [SkaAnimKeyframeBoneData]
    
    def from_raw_data(self, rawdata):
        self.scale_factor       = struct.unpack('<f', rawdata[0:4])[0]
        self.translation_factor = struct.unpack('<f', rawdata[4:8])[0]
        self.bone_start_data = []
        self.keyframes = { 0: []} # kf: [SkaAnimKeyframeBoneData]

class SkaAnimStreamHeader(object):
    __slots__ = "frame_count", "variation_id", "frame_rate", "dps", "data_offset"
    def __init__(self):
        self.frame_count  = 0
        self.variation_id = 0
        self.frame_rate   = 1.0
        self.dps          = 30.0
        self.data_offset  = 0
    def from_raw_data(self, rawdata):
        self.frame_count   = struct.unpack('<H', rawdata[0:2])[0]
        self.variation_id  = struct.unpack('<h', rawdata[2:4])[0]
        self.frame_rate    = struct.unpack('<f', rawdata[4:8])[0]
        self.dps           = struct.unpack('<f', rawdata[8:12])[0]
        self.data_offset   = struct.unpack('<i', rawdata[12:16])[0]

    @staticmethod
    def get_size():
        return 2 + 2 + 4 + 4 + 4

class SkaAnimStream(object):
    __slots__ = "header", "keyframe_set"
    def __init__(self):
        self.header = SkaAnimStreamHeader()
        self.keyframe_set = [] #SkaAnimKeyframeSet
    def from_raw_data(self, rawdata, data_start):
        data_off    = data_start + self.header.data_offset
        frame_count = self.header.frame_count
       
        new_keyframe_set = SkaAnimKeyframeSet()
        new_keyframe_set.from_raw_data(rawdata[data_off:data_off+8])
        
        # read initial bone positions
        BONE_INITIALIZER_DATA_SIZE = SkaAnimKeyframeBoneData.get_size()
        bone_data = SkaAnimKeyframeBoneData()
        data_off += 8
        bone_id = struct.unpack('<h', rawdata[data_off:data_off+2])[0]
        while (bone_id >= 0) and (data_off + BONE_INITIALIZER_DATA_SIZE <= len(rawdata)):
            bone_data.from_raw_data(rawdata[data_off:data_off + BONE_INITIALIZER_DATA_SIZE])
            bone_id = bone_data.bone_id
            new_keyframe_set.bone_start_data.append(bone_data)
            bone_data = SkaAnimKeyframeBoneData()
            if (bone_id < 0):
                break
            data_off += BONE_INITIALIZER_DATA_SIZE
        
        data_off += 2

        # begin reading actual keyframes        
        data_header = struct.unpack('<H', rawdata[data_off:data_off+2])[0]
        cur_frame = data_header >> 1 
        if frame_count <= 2:
            sddg=1   
        while cur_frame <= frame_count:
            bone_data.frame = cur_frame #struct.unpack('<H', rawdata[data_off:data_off+2])[0] / 2
            data_off += 2
            data_header = struct.unpack('<H', rawdata[data_off:data_off+2])[0]
            new_keyframe_set.keyframes[cur_frame] =[]
            while (data_header & 1):
                bone_data.bone_id = data_header >> 4
                bone_data.flags = data_header & 0xF            
                data_off += 2
                
                if (bone_data.flags & 8):
                    bone_data.scale_next_frame = struct.unpack('<H', rawdata[data_off:data_off+2])[0]
                    data_off += 2
                    bone_data.scale = struct.unpack('<3h', rawdata[data_off:data_off+6])
                    data_off+=6
                if (bone_data.flags & 4):
                    bone_data.rotation_next_frame = struct.unpack('<H', rawdata[data_off:data_off+2])[0]
                    data_off += 2
                    bone_data.rotation = struct.unpack('<4h', rawdata[data_off:data_off+8])
                    data_off+=8
                if (bone_data.flags & 2):
                    bone_data.translation_next_frame = struct.unpack('<H', rawdata[data_off:data_off+2])[0]
                    data_off += 2
                    bone_data.translation = struct.unpack('<3h', rawdata[data_off:data_off+6])
                    data_off+=6
                new_keyframe_set.keyframes[cur_frame].append(bone_data)
                bone_data = SkaAnimKeyframeBoneData()
                bone_data.frame = cur_frame
                data_header = struct.unpack('<H', rawdata[data_off:data_off+2])[0]
                bone_data.bone_id = data_header >> 4
                bone_data.flags = data_header & 0xF
            #read data header with null LSB - this is the start of a new keyframe
            cur_frame = (data_header >>1)
                

        self.keyframe_set=new_keyframe_set
        
class SkaEvent(object):
    __slots__ = "frame_id", "type", "action"
    def __init__(self, frame_id=0, event_type = "", action = ""):
        self.frame_id = frame_id
        self.type   = FixedLengthName(event_type,48)
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
            new_event.frame_id = struct.unpack('<h',rawdata[0 + i*DATUM_SIZE:2 + i*DATUM_SIZE])[0]
            new_event.type.from_raw_data(rawdata[2 + i*DATUM_SIZE:2+48 + i*DATUM_SIZE])
            new_event.action.from_raw_data(rawdata[50 + i*DATUM_SIZE:50+128 + i*DATUM_SIZE])
            result.append(new_event)
        return result

    @staticmethod
    def get_size():
        return 2 + 48 + 128

class SkaAnimHeader(object):
    __slots__ = "name", "drive_type", "loopable", "event_count", "event_offset", "stream_count", "unk", "stream_headers"
    def __init__(self, name = ""):
        self.name = FixedLengthName(name, 64)
        self.drive_type   = 0
        self.loopable     = 0
        self.event_count  = 0
        self.event_offset = 0
        self.stream_count = 0
        self.stream_headers = []
    
    def from_raw_data(self, rawdata):
        self.name.from_raw_data(rawdata[0:64])
        self.drive_type   = struct.unpack('<b', rawdata[64:65])[0]
        self.loopable     = struct.unpack('<b', rawdata[65:66])[0]
        self.event_count  = struct.unpack('<h', rawdata[66:68])[0]
        self.event_offset = struct.unpack('<i', rawdata[68:72])[0]
        self.stream_count = struct.unpack('<h', rawdata[72:74])[0]
        unk = struct.unpack('<h', rawdata[74:76])[0]
        self.stream_headers = []
        for i in range(0, 10):
            new_stream_header = SkaAnimStreamHeader()
            DATUM_SIZE = SkaAnimStreamHeader.get_size()
            offset = 76 + i * DATUM_SIZE
            new_stream_header.from_raw_data(rawdata[offset:offset+DATUM_SIZE ])
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

class SkaFile(object):
    __slots__ = "bone_data", "variation_data", "animation_data", "_fileraw"
    
    def __init__(self):
        self.bone_data = []
        self.variation_data = []
        self.animation_data = []
        self._fileraw = []
    
    def read(self, file):
        
        time1 = time.clock()

        self._fileraw = file.read()
        self.get_bone_data()
        self.get_variation_data()
        self.get_animation_data()
        print(" done in %.2f sec." % (time.clock() - time1))
    

    def get_bone_data(self):
        count = struct.unpack('<i', self._fileraw[0:4])[0]
        offset = struct.unpack('<i', self._fileraw[4:8])[0]
        print(count , 'bones, offset: ', offset)

        DATUM_SIZE = SkaBone.get_size()
        for i in range(0, count):
            
            data_start = offset + DATUM_SIZE * i
            newDatum = SkaBone()
            newDatum.from_raw_data(self._fileraw[data_start:data_start+DATUM_SIZE])
            self.bone_data.append(newDatum)
    
    def get_variation_data(self):
        count = struct.unpack('<i', self._fileraw[8:12])[0]
        offset = struct.unpack('<i', self._fileraw[12:16])[0]
        print(count , 'variations, offset: ', offset)
        # do nothing, because it seems ToEE doesn't have this in practice

    def get_animation_data(self):
        count = struct.unpack('<i', self._fileraw[16:20])[0]
        offset = struct.unpack('<i', self._fileraw[20:24])[0]
        print(count , 'animation data, offset: ', offset)

        # get data headers first
        HEADER_SIZE = SkaAnimHeader.get_size()
        EVENT_SIZE = SkaEvent.get_size()
        data_start = offset
        for i in range(0, count):
            
            newDatum = SkaAnim()
            newDatum.header = SkaAnimHeader()
            newDatum.header.from_raw_data(self._fileraw[data_start:data_start+ HEADER_SIZE])

            # events
            event_offset = data_start + newDatum.header.event_offset
            event_count = newDatum.header.event_count
            
            if event_count > 0:
                newDatum.events = SkaEvent.from_raw_data(self._fileraw[event_offset:event_offset+event_count*EVENT_SIZE], event_count)

            stream_count = newDatum.header.stream_count
            if stream_count > 1:
                dummy=1
            for j in range(0, stream_count):
                new_stream = SkaAnimStream()
                new_stream.header = newDatum.header.stream_headers[j]
                new_stream.from_raw_data(self._fileraw, data_start)
                newDatum.streams.append(new_stream)

            self.animation_data.append(newDatum)

            
            data_start += HEADER_SIZE
        return
            

    def write(self, file):
        # first write the header
        
        # bone data
        bone_count = len(self.bone_data)
        bone_data_offset = 24 # always 24
        file.write(struct.pack("<2i", bone_count, bone_data_offset))
        self.write_bones(file)
        
        # #variation data
        variation_count = len(self.variation_data)
        variation_data_offset = bone_data_offset + self.get_bone_data_length()
        file.write(struct.pack("<2i", variation_count, variation_data_offset))
        # shouldn't actually have data here, heh
        
        # animation data
        animation_count = len(self.animation_data)
        animation_data_offset = variation_data_offset + self.get_variation_data_length() #
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
        self.pos         = struct.unpack('<4f', rawdata[0:0+16])
        self.normal      = struct.unpack('<4f', rawdata[0+16:0+32])
        self.uv          = struct.unpack('<2f', rawdata[0+32:0+40])
        attachment_count = struct.unpack('<h',  rawdata[42:44])[0]
        if attachment_count > 6:
            print('wtf')
        attachment_count = max(0, min(attachment_count, 6))
        self.attachment_bones = []
        self.attachment_bones   = struct.unpack("<%dh" % attachment_count,  rawdata[44   :44+attachment_count*2])
        self.attachment_weights = struct.unpack("<%df" % attachment_count,  rawdata[44+12:44+12+attachment_count*4])
        
    @staticmethod
    def get_size():
        return 80

class SkmFace(object):
    __slots__ = "material_id", "vertex_ids"
    def from_raw_data(self, rawdata):
        self.material_id = struct.unpack('<h',  rawdata[0:2])[0]
        self.vertex_ids  = struct.unpack('<3h',  rawdata[2:8])
    @staticmethod
    def get_size():
        return 8

class SkmFile(object):
    __slots__ = ["bone_data", "material_data", 
                "vertex_data", "face_data", 
                "_fileraw", "_dataidx"]
    
    def __init__(self):
        self.bone_data     = []
        self.material_data = []
        self.vertex_data   = []
        self.face_data     = []

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
        print(count , 'faces, offset: ', offset)
        DATUM_SIZE = 8
        for i in range(0, count):
            
            data_start = offset + DATUM_SIZE * i
            newDatum = SkmFace()
            newDatum.from_raw_data(self._fileraw[data_start:data_start+DATUM_SIZE])
            self.face_data.append(newDatum)

    def get_vertex_data(self):
        count = struct.unpack('<i', self._fileraw[16:20])[0]
        offset = struct.unpack('<i', self._fileraw[20:24])[0]
        print(count , 'vertices, offset: ', offset)

        DATUM_SIZE = 80
        for i in range(0, count):
            
            data_start = offset + DATUM_SIZE * i
            newDatum = SkmVertex()
            newDatum.from_raw_data(self._fileraw[data_start:data_start+DATUM_SIZE])
            self.vertex_data.append(newDatum)

    def get_material_data(self):
        self.material_data = []
        count = struct.unpack('<i', self._fileraw[8:12])[0]
        offset = struct.unpack('<i', self._fileraw[12:16])[0]
        print(count , 'materials, offset: ', offset)

        DATUM_SIZE = 128
        for i in range(0, count):
            
            data_start = offset + DATUM_SIZE * i
            newDatum = SkmMaterial()
            newDatum.from_raw_data(self._fileraw[data_start:data_start+DATUM_SIZE])
            self.material_data.append(newDatum)
        

    def get_bone_data(self):
        bone_count = struct.unpack('<i', self._fileraw[0:4])[0]
        bone_offset = struct.unpack('<i', self._fileraw[4:8])[0]
        print(bone_count , 'bones, offset: ', bone_offset)

        DATUM_SIZE = SkmBone.get_size()
        for i in range(0, bone_count):
            
            bone_start = bone_offset + DATUM_SIZE * i
            newbone = SkmBone()
            newbone.from_raw_data(self._fileraw[bone_start:bone_start+DATUM_SIZE])
            self.bone_data.append(newbone)
        


    def write(self, file):
        # first write the header
        
        # bone data
        bone_count = len(self.bone_data)
        bone_data_offset = 24 # always 24
        file.write(struct.pack("<2i", bone_count, bone_data_offset))
        self.write_bones(file)
        
        # material data
        material_count        = len(self.material_data)
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
    filepath = 'D:/GOG Games/ToEECo8/data/art/meshes/Monsters/Giants/Hill_Giants/Hill_Giant_2/Zomb_giant_2.SKA'
    ska_filepath = filepath
    skm_filepath = ska_filepath.split('.SKA')[0] + '.SKM'

    # read SKM file
    file = open(skm_filepath, 'rb')
    print('Opened file: ', skm_filepath)
    skm_data.read(file)
    file.close()

    #read SKA file
    ska_data = SkaFile()
    file = open(ska_filepath, 'rb')
    print('Opened file: ', ska_filepath)
    ska_data.read(file)
    file.close()
    
    return

if __name__ == '__main__':
    main()
