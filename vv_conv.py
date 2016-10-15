import vv_videoproc
import sys, getopt
import logging

logging.basicConfig(format='%(asctime)s %(levelname)s:%(name)s:%(message)s', level=logging.INFO)
logger=logging.getLogger(__name__)

def printhelp():
    print("args:  -i inputfile -o outputfile -v -h")
    print("args:  --ifile  inputfile --ofile outputfile --verbose --help")
    print("       -v verbose - will print input file details")
    print("       If output file is specified, program will convert, only if needed")
    
def main(argv):
    inputfile = ''
    outputfile = None
    haveinput = False
    verbose = False
    
    try:
        opts, args = getopt.getopt(argv,"vhi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        printhelp()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            printhelp()
            sys.exit()
        elif opt in ("-v", "--verbose"):
            verbose = True
        elif opt in ("-i", "--ifile"):
            inputfile = arg
            haveinput = True
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    if inputfile and verbose: logger.info ("Input file is "+inputfile)
    if outputfile and verbose: logger.info ("Output file is "+outputfile)
    
    if haveinput:
        p = vv_videoproc.VideoProcessToVV()
        videoinfo = p.map_video_tovv(inputfile, outputfile)
        if videoinfo["status"]:
            if verbose: print(videoinfo)
            if videoinfo["needtoprocess"]:
                cmd1 = "avconv -v quiet -i "+inputfile+" -c:v h264 -preset medium -tune film "
                if outputfile == None:
                    cmd2 = videoinfo["avparameter"]+" -c:a copy outputfile+\n"
                else:
                    cmd2 = videoinfo["avparameter"]+" -c:a copy"+outputfile+"\n"
                cmdtorun = cmd1 + cmd2
                if verbose: print(cmdtorun)
            else:
                if verbose: print("No action for "+inputfile+"\n")
    else: 
        logger.info("No input file specified")
        sys.exit()
        
if __name__ == "__main__":
    main(sys.argv[1:])


