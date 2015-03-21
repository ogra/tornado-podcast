import glob
import os.path

class ImageUtil():
    def __init__(self, thumbnailpath):
        self.thumbnailpath = thumbnailpath

    def get_index(self, subdir_name):
        images_tmp = []
        for ext in ['*.gif', '*.jpg', '*.jpeg', '*.png']:
            images_tmp += glob.glob(self.thumbnailpath + subdir_name + '/' + ext)
        images = []
        for image in images_tmp:
            images.append(os.path.basename(image))
        return images
