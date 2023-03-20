from gerbil.gerbil import Gerbil
import logging
def my_callback(eventstring, *data):
    args = []
    for d in data:
        args.append(str(d))
    print("MY CALLBACK: event={} data={}".format(eventstring.ljust(30), ", ".join(args)))
    # Now, do something interesting with these callbacks

grbl = Gerbil(my_callback)
grbl.cnect("/dev/ttyACM0", 115200) # or /dev/ttyACM0
grbl.poll_start()
grbl.gcode_parser_state_requested = True
grbl.stream('?')
if grbl.cmode == "Alarm":
    grbl.killalarm()
    grbl.stream('?')
print(grbl.cmode)
if grbl.cmode == "Alarm":
    grbl.killalarm()
    grbl.send_immediately('$J=X100F300')
grbl.stream('?')
grbl.softreset()
grbl.killalarm()
grbl.disconnect()
pass


