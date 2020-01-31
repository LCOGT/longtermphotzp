import logging

from longtermphotzp.es_aws_imagefinder import download_from_archive

logging.basicConfig()
def notest_aws_fits_access():


        # public dark
        frameid = 13855729
        fits = download_from_archive(frameid)
        assert fits is not None, f"Download of image {frameid}from lco aws archive"

        # proproatary iamge
        frameid = 13854219
        fits = download_from_archive(frameid)
        assert fits is not None, f"Download of image {frameid}from lco aws archive"


