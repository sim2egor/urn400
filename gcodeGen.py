from gerbil.gerbil import Gerbil
import threading
import time


class GcodeGen(Gerbil):
    ready = False
    completed = 0
    percent = 0
    port = ""
    speed = 0
    _thread_gcode = None
    oldY = 0
    Fs = 500

    def __init__(self, port="", speed=0):
        if len(port) > 0: self.port = port
        if speed > 0: self.speed = speed
        if len(self.port) == 0: return
        if self.speed == 0: return

        Gerbil.__init__(self, self._gcode_callback)
        self.setup_logging()
        self.cnect(self.port, self.speed)

        self.killalarm()
        self.ready = False

        if self.is_connected() == False: return
        if self._thread_gcode == None:
            self._thread_gcode = threading.Thread(target=self._gcode_state)
            self._thread_gcode.start()
            self.logger.debug("{}: Gcode thread started".format(self.name))
        else:
            self.logger.debug("{}: Gcode thread already running...".format(self.name))

    def home(self):
        if self.is_connected == True: return
        print("-------------------HOME CALLED--------------------------")
        #self.stream("$H\n")
        self.homing()
        self.stream("G92 X0.0 Y0.0 Z0.0 \n")
        self.stream("G10 P0 L20 X0 Y0 Z0 \n")
        self.stream("G90 \n")
        self.stream("G21 \n")

        #self.stream("$HX \nG92 X0.0 Y0.0 Z0.0 \nG10 P0 L20 X0 Y0 Z0 \n G90 \n G21 \n")
        self.ready = True
        self.connected = True
        self.oldY = 0
        print("-------------------HOME CALLED END--------------------------")

    ##Cleaning Y, windings count
    def resetX(self):
        if self.is_connected == True: return
        self.stream("G10 P0 L20 X0 \n")

    ##Cleaning Y, windings count
    def windingClean(self):
        if self.is_connected == True: return
        self.stream("$HY \n")
        self.oldY = 0

    ##Setting shifting speed
    def setFs(self, F):
        self.Fs = F

    """
            empty_step = {
            # 'number': self.current_step + 1,
            'rotation_direction': 'CW', #Направление вращения: CW по часовой стрелке /CCW против часовой стрелки
            'direction': 'right', #Направление движения каретки вправо/влево
            'reversible' : 0, #менять направление при нескольких слоях
            'step_number': 0, # Номер шага
            'winding_count': 0, # Количество витков
            'winding_step': 0, # Шаг витка мм
            'rpm': 0, # Частота вращения/ обороты/мин
            'cycle': 'none', # Тип цикла: цикл с остановкой (пауза), цикл с замедлением, цикл без замедления
            'left_reverse_point': 0, # Левая точка реверс (координата)
            'right_reverse_point': 0, # Правая точка реверс (координата)
            'pedal': 0, # Педаль
            'shift': 0, # Сдвиг
            'shift_speed': 100  #Скорость сдвига
        }"""

    ##Send gcode to board for one layer
    def makeBlock(self, step):
        if self.ready == False:
            return -1
        # print(step)

        self.percent = 0
        self.completed = 0

        F = int(step['rpm'])
        # Fs = int(step['shift_speed'])
        Fs = self.Fs

        X_start = float(step['left_reverse_point'])
        X_end = float(step['right_reverse_point'])

        # width = X_end - X_start
        Y = float(step['winding_count'])
        if step['rotation_direction'] == 'CCW': Y *= -1
        Y += self.oldY
        self.oldY = Y

        if step['direction'] == 'left':
            self.stream("G0 X" + str(X_end) + " F" + str(Fs) + " \n G1 X" + str(X_start) + " Y" + str(Y) + " F" + str(
                F) + " \n")
        else:
            self.stream("G0 X" + str(X_start) + " F" + str(Fs) + " \n G1 X" + str(X_end) + " Y" + str(Y) + " F" + str(
                F) + " \n")

    ##Send to board one move action
    def move(self, X, Y):
        if self.ready == False:
            return -1
        if self.cmode == "Idle" or self.cmode[:5] == "Alarm":

            Fs = self.Fs

            if X != 0:
                self.stream("G91 G0 X" + str(X) + " F" + str(Fs) + "\n" + "G90 \n")
            if Y != 0:
                self.stream("G91 G0 Y" + str(Y) + " F" + str(Fs) + "\nG90 \n")
                self.oldY += Y
        else:
            return -2

    def get_percent(self):
        return self.percent

    def get_completed(self):
        return self.completed

    def _gcode_callback(self, eventstring, *data):
        args = []
        for d in data:
            args.append(str(d))

        if "on_progress_percent" in eventstring:
            self.percent = data[0]

        if "on_job_completed" in eventstring:
            self.completed = 1

        if "on_stateupdate" in eventstring:
            pass
            # if self.cmode == "Door:0":
            #    self.resume()
        #else:
        print("gcodeGen: event={} data={}".format(eventstring.ljust(30), ", ".join(args)))
        #     if self.cmode == "Hold:0":
        #         if "H" in self.cpn:
        #             pass
        #         else:
        #             self._iface_write("~")
        # if "on_alarm" in eventstring :
        #    self.softreset()
