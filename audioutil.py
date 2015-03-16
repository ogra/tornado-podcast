import glob
import os.path

class AudioUtil():
    def __init__(self, uploadpath):
        self.uploadpath = uploadpath

    def get_index(self):
        audios_tmp = glob.glob(self.uploadpath + '*.mp3')
        audios = []
        for audio in audios_tmp:
            audios.append(os.path.basename(audio))
        return audios
