from gerbil.gerbil import Gerbil

grbl = Gerbil()

def cnc_callback(eventstring, *data):
    args = []
    for d in data:
        args.append(str(d))
    print("MY CALLBACK: event={} data={}".format(eventstring.ljust(30), ", ".join(args)))
    if "on_alarm" in eventstring :
        grbl.killalarm()

def connect_cnc(port, speed):
    grbl.__init__(cnc_callback)
    grbl.setup_logging()
    grbl.cnect(port, speed)
    grbl.poll_start()
    grbl.stream("M4 S500 \n ")
