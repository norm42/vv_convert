from subprocess import Popen, PIPE
import re
import sys
import os
import logging


# MINLINES is the threshold to determine if avprobe found an error
# larger number of lines indicated avprobe found a good file, less an error
# this is limited measurement as it is posslbe the avprobe could get verbose
# with errors in the future or errors I that have not tested.  
# However, in any case we would not find any valid data parsing the error, so no action would result
# ** Worse case is still safe **
MINLINES = 15 

logger = logging.getLogger(__name__)

# This module gets the video informatin needed to scale and transcode the video file


class VideoProcessToVV():
    
    # allow another projector resolution, default to 800x600
    def __init__(self, projresx=800, projresy=600):
    
        self.videoinfo = {"status":False}  # init to false, will be ok when the dictionary is filled in
        self.PIRES_X = projresx
        self.PIRES_Y = projresy

        
    # This method opens the video file specified by filepath, gets the parameters and determines
    # if the file needs to be converted.  If so, generates the appropriate command for avconv.
    # returns a dictionary that contains "status"=True if successfule at opening and getting info
    # from the file.  However, the file may not need to be processed.  "needtoprocess"=True
    # will indicated if the file needs to be processed to get to the correct resolution/orientation
    
    # If only filepath is specified, then only data on the video file is returned.  No processing.
    # If outpath is specified, and "needtoprocess"=True, then avconv will be called to convert the file.
    #
    def map_video_tovv(self,filepath, outpath=None):
        
        #check to see if file exists
        if not os.path.isfile(filepath):
            self.videoinfo = {"status":False}
            return self.videoinfo

        cmd = "avprobe %s" % filepath
        # only exception here will come if avprobe is not found 
        # as avprobe always seems to print something on
        # stdout/error such that no exception will be raised
        try:
            p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            avresult = p.communicate()
        except:
            logger.exception("avprobe failed for " + filepath)
            self.videoinfo["status"] = False
            return self.videoinfo 
        else:
            # initialize work variables
            rotation, rotcommand, avparameter, createtime = "0", "", "", ""
            encoder, bitrate, framerate = "","",""
            iresx = int(self.PIRES_X)
            iresy = int(self.PIRES_Y)
            resx, resy, dursec = 0.0, 0.0, 0.0
            numlines = 0
            
            # this flag is used to determine if the file needs to be processed
            needtoprocess = False  # assume that everything is in the right format
    
            # Parse the lines from avprobe to gather the information on the 
            # file
            for line in avresult:
                sline = line.split("\n")  # communitate() returns a long string of many lines

                for oneline in sline:     # take one line at a time
 
                    numlines = numlines + 1  #keep track of the number of lines for error checking
                    
                    # The "Video" line has a lot of information about the input file
                    if oneline.rfind("Video") > 0:
                        words = oneline.split(",")
                        bitrate = words[3]              # bitrate as text
                        framerate = words[4]            # framerate as text
                        
                        # Get x,y resolution
                        resxy = re.findall("(\d+x\d+)", oneline)[0]
                        words = resxy.split("x")
                        resx = float(words[0])
                        resy = float(words[1])

				
                        # if the X res is not equal to the PI video resolution
                        # we need to scale.  The X res will be scaled to PIRES_X
                        # the y res will be scaled to the propotion of the x res scale
                        # to maintain apsect ratio
				
				
                        if int(resx) > int(self.PIRES_X):  # source is too wide in x
                            needtoprocess = True
                            vidscale = self.PIRES_X/resx   # do the calc in fp to scale y
                            iresy = int(resy * vidscale)

					
                        # NOTE order is important here as after scaling x, y could still be
                        # too high and we need to scale x vs just set to PIRES_X
                        # or y could be too big, x ok
										
                        if iresy > int(self.PIRES_Y):       # y could be too big 
                            iresy = int(self.PIRES_Y)	    # set y to PIRES_Y - max height
                            vidscale = self.PIRES_Y/resy    # scale for x
                            iresx = int(resx * vidscale)    # xres is now scaled
                            needtoprocess = True
				
                        # at this point both x and y are equal to or less than PIRES values
                        # and needtoprocess is updated to indicate if transcoding is required
                        
                    # get the encoder used				
                    if oneline.rfind("encoder") > 0:
                        words = oneline.split(":")
                        encoder = words[1]
                    
                    # get the creation time as a string
                    if oneline.rfind("creation_time") >0:
                        words = oneline.split(":")
                        createtime = words[1]+":"+words[2]+":"+words[3]
                    
                    # get the duration of the video, convert to seconds
                    if oneline.rfind("Duration") >0:
                        duration = re.findall("Duration: (\d+:\d+:[\d.]+)", oneline)[0]
                        words = duration.split(":")
                        dursec = (float(words[0]) * 3600.0) + (float(words[1]) * 60.0) + (float(words[2]))
 
                        
                    # displaymatrix describes the orientation the video was taken
                    # Entries I found are {none - 0, 180, -90, 90} 
                    # this will set the hflip, vflip, transpose parameters for the transcoder	
                    if oneline.rfind("displaymatrix") >0:
                        words = oneline.split()  # white space
                        frotation = float(words[3])
                        rotation = int(frotation)    # should be able to do this w/o double convert...
                        #print(rotation)

                        if rotation == 180:
                            rotcommand = "-vf vflip,hflip"
                            needtoprocess = True
                        elif rotation == 90:
                            rotcommand = "-vf transpose=2"
                            vidscale = self.PIRES_Y/resx			#rotation - need to swap x,y
                            iresx = int(vidscale * resy)
                            iresy = int(self.PIRES_Y)
                            needtoprocess = True
                        elif rotation == -90:
                            rotcommand = "-vf transpose=1"
                            vidscale = self.PIRES_Y/resx			#rotation - need to swap x,y
                            iresx = int(vidscale * resy)
                            iresy = int(self.PIRES_Y)
                            needtoprocess = True
                        else:
                            rotcommand = " "
				
            # We should have received more than MINLINES lines
            # if not, then there was an error from avprobe
            if numlines < MINLINES:
                logger.exception(avresult)
                self.videoinfo = {"status":False}
                return self.videoinfo
                
            # depending on the encoder, resolution has to have even or divisible by 16
            # in this case (avconv with h264 encoder, even is required)
            iresx = (iresx/2) * 2  
            iresy = (iresy/2) * 2
            
            # This is the file specific parameters for avconv
            avparameter = "-s "+str(iresx)+"x"+str(iresy)+" "+rotcommand        
 
            # return a dictionary with all the information related to the file as well as the
            # avconv parameters required for conversion.
            #
            self.videoinfo = {"inresx":resx, "inresy":resy, "outresx":iresx, "outresy":iresy, 
            "rotation":rotation, "createtime": createtime, "needtoprocess": needtoprocess,
            "encoder": encoder, "rotcommand": rotcommand, "filepath":filepath,  "status":True,
            "duration": dursec, "bitrate":bitrate, "framerate":framerate, "avparameter":avparameter}

            if outpath != None and needtoprocess:
                cmd1 = "avconv -v quiet -i "+filepath+" -c:v h264 -preset medium -tune film "
                cmd2 = self.videoinfo["avparameter"]+" -c:a copy "+outpath+"\n"
                cmdtorun = cmd1 + cmd2
                logger.debug("we would run this "+cmdtorun)
                try:
                    os.system(cmdtorun)
                except:
                    logger.exception(" failed to run: "+cmdtorun)
 
            return self.videoinfo

