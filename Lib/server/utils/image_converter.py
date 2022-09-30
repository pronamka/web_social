from PIL import Image
from os import remove


def convert_image(name: str) -> None:
    """Convert an image from png or jpg to jpeg
    Saves all files in ../static/avatar_images/"""
    if name.rsplit('.', maxsplit=1)[1] != 'jpeg':  # check if picture already in jpeg format
        path = f'../static/avatar_images/{name}'  # construct path
        image = Image.open(path)  # create an image object
        jpeg = image.convert('RGB')  # convert image into RGB representation
        remove(f'../static/avatar_images/{name}')  # delete the old image
        jpeg.save(f'../static/avatar_images/{name.split(".")[0]}.jpeg')  # save the the representation as jpeg
