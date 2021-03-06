""" Pre-procesing methods for an input image
"""
from __future__ import print_function, absolute_import, division, unicode_literals

import numpy as np
from PIL import Image
import pdb

from spit import zscale as aut_z


def flattened_array(image, pdict, **kwargs):
    """ Process a single image and return an image
    with flips and flattened

    Parameters
    ----------
    image : ndarray
      Typically the RAW frame read from disk

    Returns
    -------
    images : ndarray, dtype=uint8
       2D trimmed, resized, scaled image with flips
    """
    zimage = process_image(image, pdict, **kwargs)
    image, ver_image, hor_image, hor_ver_image = flips(zimage)

    # Flatten
    im_array = []
    im_array.append(image.flatten())
    im_array.append(ver_image.flatten())
    im_array.append(hor_image.flatten())
    im_array.append(hor_ver_image.flatten())

    # Return
    images_array = np.array(im_array)
    return images_array


def process_image(image, preproc_dict, debug=False, min_rows=50):
    """ Process a single image

    Parameters
    ----------
    image : ndarray
      Typically the RAW frame read from disk
    preproc_dict : dict
      Parameters for pre-processing

    Returns
    -------
    zimage : ndarray
       2D trimmed, resized, scaled image
    """
    from spit.utils import congrid
    # Trim
    image = trim_image(image, cutoff_percent=preproc_dict['cutoff_percent'], debug=debug)
    # Check trimming
    if image.shape[0] < min_rows:
        pdb.set_trace()

    # Resize
    rimage = congrid(image.astype(float), (preproc_dict['image_height'],
                                           preproc_dict['image_width']))

    # zscale
    zimage = zscale(rimage)

    # Return
    return zimage


def flips(image):
    """ Flip the input image this way and that

    Parameters
    ----------
    image : ndarray
    flatten : bool, optional

    Returns
    -------
    image : ndarray
       Original image
    ver_image : ndarray
      Flipped TOP_BOTTOM
    hor_image : ndarray
      Flipped LEFT_RIGHT
    hor_ver_image : ndarray
      Flipped both
    """
    pil_image = Image.fromarray(image)

    # Generate flipped images
    #pil_image.transpose(Image.FLIP_TOP_BOTTOM)
    ver_image = np.array(pil_image.transpose(Image.FLIP_TOP_BOTTOM))
    hor_image = np.array(pil_image.transpose(Image.FLIP_LEFT_RIGHT))
    hor_ver_image = np.array(pil_image.transpose(Image.FLIP_LEFT_RIGHT).transpose(
        Image.FLIP_TOP_BOTTOM))

    # Return
    return image, ver_image, hor_image, hor_ver_image


'''
def old_resize_image(image_data, sess):
    # CURRENTLY DEFUNCT
    #   INCLUDED PADDING
    # Convert the image data to an int
    image_data = image_data.astype(int)
    height = image_data.shape[0]
    width = image_data.shape[1]

    # Claculate the aspect ratio
    aspect_ratio = float(width / height)

    # Add a third dimension, this is required by TensorFlow
    image_data = image_data[..., np.newaxis]

    # Define the new sizes keeping the aspect ration
    new_height = int(defs.image_width / aspect_ratio)

    # User tensorflow to resize the image
    new_image = tf.image.resize_images(image_data, [new_height, defs.image_width])
    new_image = new_image.eval(session=sess)
    
    # Remove the third added dimension
    new_image = new_image[:, :, 0]

    # Add padding to make the image 200x600
    height_pad = defs.image_height - new_image.shape[0]
    width_pad = defs.image_width - new_image.shape[1]
    npad = ((0, height_pad), (0, width_pad))
    
    padded_image = np.pad(new_image, pad_width=npad, mode='constant', constant_values=defs.pad_const)
    
    return padded_image
'''


def cutoff_forw(max_vals, med_max, med_perc=0.2, cutoff_percent=1.15):
    cutoff_point = 0
    for idx in range(1, len(max_vals)):
        prev_val = max_vals[idx - 1]
        curr_val = max_vals[idx]

        if (curr_val > (cutoff_percent * prev_val)) or (
            np.abs(curr_val-med_max) < med_perc*med_max):
            cutoff_point = idx
            break

    return cutoff_point


def cutoff_back(max_vals, med_max, cutoff_percent=1.15, med_perc=0.2):
    """ Trim image from the top"""
    max_vals.reverse()
    cutoff_point = 0
    for idx in range(1, len(max_vals)):
        prev_val = max_vals[idx - 1]
        curr_val = max_vals[idx]

        if (curr_val > (cutoff_percent * prev_val)) or (
            np.abs(curr_val-med_max) < med_perc*med_max):
            cutoff_point = idx
            break

    return cutoff_point


def trim_image(image, ret_all=False, debug=False, **kwargs):
    """ Trim down the image to the flux only region
    Handles overscan and vignetted regions
    """
    import scipy
    from astropy.stats import sigma_clip

    # Rotate
    shape = image.shape
    if shape[0] > shape[1]:  # Vertical image?
        image = scipy.ndimage.interpolation.rotate(image, angle=90.0)
        shape = image.shape

    # Clip and find maximum
    filtered_data = sigma_clip(image, sigma=3, axis=0)
    max_vals = np.max(filtered_data, axis=1)

    # Calculate median (ignoring 0 values)
    med_max = np.median(max_vals[max_vals > 0.])

    # Identify top and bottom
    cutoff_f = cutoff_forw(max_vals, med_max, **kwargs)
    cutoff_b = cutoff_back(max_vals, med_max, **kwargs)
    #
    first = cutoff_f
    second = shape[0] - cutoff_b

    # Trim and return
    if ret_all:
        return image[first:second, :], (max_vals, cutoff_f, cutoff_b)
    else:
        return image[first:second, :]


def cutoff_forw(max_vals, med_max, cutoff_percent=1.10, med_perc=0.2):
    """ Trim image from the bottom
    max_vals : list
      Maximum value of "filtered" sigma_clipped data
    """
    cutoff_point = 0
    for idx in range(1,len(max_vals)):
        prev_val = max_vals[idx-1]
        curr_val = max_vals[idx]

        if (curr_val > (cutoff_percent * prev_val)) or (
                    np.abs(curr_val-med_max) < med_perc*med_max):
            cutoff_point = idx
            break

    return cutoff_point


def cutoff_back(max_vals, med_max, cutoff_percent=1.10, med_perc=0.2):
    """ Trim image from the top
    max_vals : list
      Maximum value of "filtered" sigma_clipped data
    """
    max_vals = max_vals[::-1]
    cutoff_point = 0
    for idx in range(1,len(max_vals)):
        prev_val = max_vals[idx-1]
        curr_val = max_vals[idx]

        if (curr_val > (cutoff_percent * prev_val)) or (
            np.abs(curr_val-med_max) < med_perc*med_max):
            cutoff_point = idx
            break

    return cutoff_point


def zscale(image, chk=False, contrast=0.25, only_range=False):
    """ Take an input image of any range and return a uint8 image
    scaled by the ZSCALE algorithm

    Parameters
    ----------
    image : ndarray of any type
    contrast : float, optional
      Passed to zscale algorithm

    Returns
    -------
    zimage : ndarray of unit8
      Ready to be saved as a PNG
    if only_range is True, return z1,z2

    """
    # Find scale range
    z1,z2 = aut_z.zscale(image, contrast=contrast)
    if only_range:
        return z1, z2
    # Max, min
    cut_data = np.minimum(image, z2)
    cut_data = np.maximum(cut_data, z1)
    if chk:
        print(np.min(cut_data), np.max(cut_data))
    # Rescale to 0 to 255
    zimage = 255 * (cut_data - z1) / (z2 - z1)
    zimage = zimage.astype(np.uint8)
    if chk:
        print(np.min(zimage), np.max(zimage))
    # Return
    return zimage


def original_preproc_dict():
    ########################################################################
    # Various constants for the size of the images.
    # Use these constants in your own program.
    preproc_dict = {}

    # Width and height of each image.
    # The height of an image
    preproc_dict['image_height'] = 210

    # The width of an image
    preproc_dict['image_width'] = 650

    # Length of an image when flattened to a 1-dim array.
    preproc_dict['img_size_flat'] = preproc_dict['image_height'] * preproc_dict['image_width']

    # Tuple with height and width of images used to reshape arrays.
    preproc_dict['img_shape'] = (preproc_dict['image_height'],
                                 preproc_dict['image_width'])

    # Number of channels in each image, 3 channels: Red, Green, Blue.
    preproc_dict['num_channels'] = 1

    # The padding value for the padded image
    preproc_dict['pad_const'] = 0

    # The overscan cutoff percent difference. If the running average is different
    # from the previous running average by this much, then detect an overscan region
    preproc_dict['cutoff_percent'] = 1.10

    # Return
    return preproc_dict
