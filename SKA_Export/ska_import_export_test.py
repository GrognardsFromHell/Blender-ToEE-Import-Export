
import os
from ska import SkmFile, SkaFile


def main():
    
    skm_data = SkmFile()
    # filepath = 'D:/GOG Games/ToEECo8/data/art/meshes/Monsters/Giants/Hill_Giants/Hill_Giant_2/Zomb_giant_2.SKA'
    filepath = r'D:\GOG Games\Vanilla Files\art\meshes\Monsters\Icelizard\icelizard.SKA'
    ska_filepath = filepath
    skm_filepath = os.path.splitext(ska_filepath)[0] + '.SKM'

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

    # modify ICE LIZARD Z
    print("Modifying Ice Lizard")
    def softmax_z(z_raw, z0 = 350, z_linear_range = 100):
        z_scale = z_raw * stream.location_factor
        from math import atan
        z_scale_new = ( atan( (z_scale-z0) /z_linear_range) + atan( z / z_linear_range ) )
        z_scale_new = (z_linear_range/2)*z_scale_new
        z_new = int(z_scale_new / stream.location_factor)
        return z_new

    for stream in ska_data.streams:
        if 2 in stream.initial_state.bone_data:
            if stream.initial_state.bone_data[2].translation:
                t = stream.initial_state.bone_data[2].translation
                z_raw = t[2]
                z_new = softmax_z(z_raw)
                stream.initial_state.bone_data[2].translation = (t[0], t[1], z_new)
        for frame in stream.raw_frames:
            if 2 in frame.bone_data:
                if frame.bone_data[2].translation:
                    z_raw = frame.bone_data[2].translation[2]
                    z_new = softmax_z(z_raw)
                    frame.bone_data[2].translation = (frame.bone_data[2].translation[0], frame.bone_data[2].translation[1], z_new)
                

    #with open('outskm.skm', 'wb') as skm_out_file:
    #    skm_data.write(skm_out_file)

    with open('outska.ska', 'wb') as ska_out_file:
        ska_data.write(ska_out_file)
    file.close()

    return


if __name__ == '__main__':
    main()