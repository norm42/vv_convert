# Video Village (VV) Video file conversion.  
This software takes in video files and converts them to the right resolution and orientation required for the projectors.  Projector resolution is 800x600, H.264 mp4 format.

The file vv_videoproc.py does the conversion.  It uses avprobe to get the information about the source file.  Key parameters of the source file are resolution and orientation.  Conversion incorporates the orientation of the camera and rotates/flips the image to be correctly displayed on the VV projectors.  

Resolution is converted to 800x600 maintaining aspect ratio.  In some cases one or both of the resulting dimensions are less than 800x600 to account for aspect ratio.  In particular, for rotation x and y are swapped.

Conversion, scaling, rotation. Flip are done with avconv.  Currently the software codec is used.  The hardware coded does not support the rotation/flipping transformations required and also requires a higher bit rate to maintain the same quality level. However, the hardware version is about 2x faster than software, only working for one orientation. (0 degrees)