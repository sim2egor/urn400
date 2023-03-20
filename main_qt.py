# /usr/bin/python3
from datetime import datetime
import base64
import subprocess
from gc import callbacks
import os
from signal import signal
import sys
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2 import QtUiTools
import queue
from gcodeGen import GcodeGen
from threading import Timer
import math
import time
import random
import json

ENABLE_CONTROLS = True

if ENABLE_CONTROLS is True:
    import RPi.GPIO as GPIO

# 3 states: IDLE, START, STOP
STATE = 0

move_step_x = 0.05
move_step_y = 0.05
move_feed_x = 300
move_feed_y = 100
move_delay = 0.05

cnc_port = '/dev/ttyACM0'
cnc_speed = 115200
filename = "_current.json"
gcode = GcodeGen(cnc_port, cnc_speed)
# 2.5
# 0.626
reducer_value = 1
bRed = 26
bLeft = 20
#bLeft = 13
bRight = 21
bUp = 12
bDown = 16
bPedal = 19

pedal_percent = 0

pedal_mode = "none"
pedal_state = {
    "wind": "Намотка",
    "move": "Поворот",
    "none": "Не исп."
}


def proc_send_immediately(s):
    while gcode.cmode == "Alarm":
        gcode.killalarm()
    gcode.send_immediately(s)


def button_callback(pin):
    print("BUTTON CALLBACK, PIN " + str(pin))
    time.sleep(0.2)
    if pin == bRed:
        gcode.resume()
    elif pin == bLeft:
        while GPIO.input(bLeft):
            print('bleft {}'.format(gcode.cmode))
            string1 = "$J=G21G91X" + str(-1 * move_step_x) + "F" + str(move_feed_x) + "\n"
            proc_send_immediately(string1)
            time.sleep(move_delay)
    elif pin == bRight:
        while GPIO.input(bRight):
            string1 = "$J=G21G91X" + str(move_step_x) + "F" + str(move_feed_x) + "\n"
            proc_send_immediately(string1)
            time.sleep(move_delay)
            print(GPIO.input(bRight))
    elif pin == bUp:
        while GPIO.input(bUp):
            string1 = "$J=G21G91Y" + str(-1 * move_step_y) + "F" + str(move_feed_y) + "\n"
            proc_send_immediately(string1)
            time.sleep(move_delay)

    elif pin == bDown:
        while GPIO.input(bDown):
            string1 = "$J=G21G91Y" + str(move_step_y) + "F" + str(move_feed_y) + "\n"
            proc_send_immediately(string1)
            time.sleep(move_delay)


def pedal_up_callback__(pin):
    time.sleep(.05)
    state = GPIO.input(pin)
    if state == 1:
        if gcode.cmode == "Idle":
            if pedal_mode == "wind":
                gcode.resume()
            if pedal_mode == "move":
                if current_program.current_step["rotation_direction"] == "CW":
                    while GPIO.input(pin):
                        string1 = "$J=G21G91X" + str(move_step_x) + "F" + str(move_feed_x) + "\n"
                        proc_send_immediately(string1)
                        time.sleep(move_delay)
                        print("MOVE SENT CW")
                elif current_program.current_step["rotation_direction"] == "CCW":
                    while GPIO.input(pin):
                        string1 = "$J=G21G91X" + str(-1 * move_step_x) + "F" + str(move_feed_x) + "\n"
                        proc_send_immediately(string1)
                        time.sleep(move_delay)
                        print("MOVE SENT CCW")
            pass
        elif gcode.cmode == "Alarm":
            pass
        elif gcode.cmode == "Run":
            if pedal_mode == "wind":
                gcode.hold()
            elif pedal_mode == "move":
                pass
    else:
        if gcode.cmode == "Idle":

            pass
        elif str(gcode.cmode).startswith("Hold"):

            pass
        elif gcode.cmode == "Alarm":
            pass


#    print(gcode.cmode, "state=", state)


remaining_step = None

# PROPERTIES
property_bounds = {
    'rotation_direction': {
        'list': ['CW', 'CCW']
    },
    'direction': {
        'list': ['right', 'left']
    },
    'step_number': {
        'range': [0, 10000]
    },
    'winding_count': {
        'range': [0, 10000]
    },
    'winding_step': {
        'range': [0, 10000]
    },
    'rpm': {
        'range': [0, 4000]
    },
    'cycle': {
        'list': [0, 1, 2, 3]
    },
    'left_reverse_point': {
        'range': [0, 150]
    },
    'right_reverse_point': {
        'range': [0, 150]
    },
    'pedal': {
        'range': [0, 6000]
    },
    'shift': {
        'range': [-150, 150]
    },
    'shift_speed': {
        'range': [0, 100]
    }
}


def is_property_valid(property_name, property_value):
    try:
        bound_type = list(property_bounds.get(property_name).keys())[0]
        bound_values = list(property_bounds[property_name].values())[0]
        if bound_type == 'list':
            if property_value in bound_values:
                return True
            else:
                return False
        if bound_type == 'range':
            if bound_values[0] <= property_value <= bound_values[1]:
                return True
            else:
                return False
    except Exception as exp:
        print(exp)

    return False


class PROPERTIES:

    def __init__(self):
        self.properties = []

    def load_properties(self):
        with open('properties.json', 'r') as read_file:
            properties = json.load(read_file)
        print(properties)

    def save_properties(self):
        with open('properties.json', 'w') as write_file:
            json.dump(self.properties, write_file)
        return 0

    def set_property(self, property_name, value):
        self.properties[property_name] = value
        return 0

    def get_property(self, property_name):
        prop = self.properties.get(property_name)
        if prop:
            return prop
        else:
            return False


# PROGRAM
class PROGRAM(PROPERTIES):

    def __init__(self):
        self.current_program = []
        self.current_property = ''
        self.file_name = ''
        self.current_step_number = 0
        self.current_step = None
        self.q = queue.Queue()

    def step_count(self):
        return len(self.current_program)

    def copy_step(self, source_step_number, destination_step_number):
        if source_step_number in range(self.step_count()) and destination_step_number in range(self.step_count()):
            self.current_program[destination_step_number] = dict(self.current_program[source_step_number])

    def get_step_by_id(self, step_number):
        try:
            if 0 <= step_number < len(self.current_program):
                self.current_step_number = step_number
                self.current_step = self.current_program[step_number]
                return self.current_program[step_number]
            else:
                print('No further steps found, adding one')
                self.add_step()
                self.current_step_number = step_number
                self.current_step = self.current_program[step_number]
                return self.current_program[step_number]

        except Exception as exp:
            print(exp)

    def del_step(self, step_number):
        del self.current_program[step_number]

    def add_step(self):
        empty_step = {
            # 'number': self.current_step + 1,
            'rotation_direction': 'CW',  # Направление вращения: CW по часовой стрелке /CCW против часовой стрелки
            'direction': 'right',  # Направление движения каретки вправо/влево
            'step_number': 0,  # Номер шага
            'winding_count': 0,  # Количество витков
            'winding_step': 0,  # Шаг витка мм
            'rpm': 0,  # Частота вращения/ обороты/мин
            'cycle': 'none',  # Тип цикла: цикл с остановкой (пауза), цикл с замедлением, цикл без замедления
            'left_reverse_point': 0,  # Левая точка реверс (координата)
            'right_reverse_point': 0,  # Правая точка реверс (координата)
            'pedal': 0,  # Педаль
            'shift': 0,  # Сдвиг
            'shift_speed': 100,  # Скорость сдвига
            'layer_stop': 0,
            'hints': [],
            'trapezoid_winding': {
                "left":
                    {
                        "type": "not_used", "offset": "0"
                    },
                "right":
                    {
                        "type": "not_used", "offset": "0"
                    },
            }
        }
        self.current_program.append(empty_step)
        self.save_program('_current.json')

    def new_program(self, file_name):
        try:
            with open(file_name, 'w') as write_file:
                self.current_program = []
                self.add_step()
                json.dump(self.current_program, write_file)
                return 0
        except Exception as exp:
            print(exp)
            return 1

    def save_program(self, filename):
        print(filename)
        try:
            with open(filename, 'w') as write_file:
                json.dump(self.current_program, write_file)
                return 0
        except Exception as exp:
            print(exp)
            return 1

    def open_program(self, filename):
        try:
            with open(filename, 'r') as read_file:
                self.current_program = json.load(read_file)
                self.current_step = self.get_step_by_id(0)
                self.current_step_number = 0
                self.file_name = filename
                # ui.update_ui()
                return True
        except Exception as exp:
            print(exp)
            return False

    def make_queue(self):
        # self.q.mutex.acquire()
        # self.q.queue.clear()

        step = dict(self.current_step)
        step.update({"winding_count": float(step["winding_count"]) / float(reducer_value)})
        step.update({"winding_step": float(step["winding_step"]) * float(reducer_value)})
        # step.update({"winding_step": float(step["winding_count"]) * float(reducer_value)})
        block_count = math.ceil(float(step["winding_count"]) * float(step["winding_step"]) / abs(
            float(step["left_reverse_point"]) - float(step["right_reverse_point"])))
        # print("block_count: " + str(block_count))
        direction = step["direction"]
        winding_count_remaining = float(step["winding_count"])
        # print(winding_count_remaining)
        winding_count_per_layer = abs(float(step["left_reverse_point"]) - float(step["right_reverse_point"])) / float(
            step["winding_step"])
        # print(winding_count_per_layer)

        layer_number = 0
        while winding_count_remaining > 0:
            layer_number += 1
            while (self.q.full == True):
                time.sleep(0.2)

            # builder.get_object("lblLayer").set_text(str(layer_number))
            step.update({"id": str(layer_number)})

            if winding_count_remaining >= winding_count_per_layer:
                step.update({"winding_count": winding_count_per_layer})
                # print("winding_count", winding_count_per_layer)
                winding_count_remaining = winding_count_remaining - winding_count_per_layer
                # remaining_step.update({"winding_count": winding_count_remaining})

            else:
                step.update({"winding_count": winding_count_remaining})
                if direction == "right":
                    step.update({"right_reverse_point":
                                     float(step["left_reverse_point"]) +
                                     float(winding_count_remaining) *
                                     float(step["winding_step"])})
                elif direction == "left":
                    step.update({"left_reverse_point":
                                     float(step["right_reverse_point"]) -
                                     float(winding_count_remaining) *
                                     float(step["winding_step"])})

                # print("winding_count_remaining", winding_count_remaining)
                winding_count_remaining = 0
                # remaining_step = None

            step.update({"direction": direction})
            # print(step)
            self.q.put(dict(step), block=True, timeout=1)

            if direction == "right":
                direction = "left"
            elif direction == "left":
                direction = "right"

        # print(self.q.qsize())
        # print(list(self.q.queue))


current_program = PROGRAM()


# WINDING BLOCKS
def create_blocks(self, step):
    global remaining_step
    step = dict(remaining_step)
    step.update({"winding_count": float(step["winding_count"]) / float(reducer_value)})
    step.update({"winding_step": float(step["winding_step"]) * float(reducer_value)})
    step.update({"rpm": float(step["rpm"]) / float(reducer_value)})

    block_count = math.ceil((float(step["winding_count"]) * float(step["winding_step"])) / abs(
        float(step["left_reverse_point"]) - float(step["right_reverse_point"])) / float(reducer_value))
    direction = step["direction"]
    winding_count_remaining = float(step["winding_count"])
    winding_count_per_layer = abs(float(step["left_reverse_point"]) - float(step["right_reverse_point"])) / float(
        step["winding_step"])
    print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    print(step)

    for layer_number in (1, block_count + 1):
        # builder.get_object("lblLayer").set_text(str(layer_number))
        if winding_count_remaining <= 0:
            return
        if winding_count_remaining >= winding_count_per_layer:
            step.update({"winding_count": winding_count_per_layer})
            print("winding_count", winding_count_per_layer)
            winding_count_remaining = winding_count_remaining - winding_count_per_layer
            remaining_step.update({"winding_count": float(winding_count_remaining)})
            # remaining_step.update({"winding_count": float(winding_count_remaining)*float(reducer_value)})

        if winding_count_remaining <= winding_count_per_layer:
            step.update({"winding_count": winding_count_remaining})
            print("winding_count_remaining", winding_count_remaining)
            winding_count_remaining = 0
            remaining_step = None

        if direction == "right":
            step["direction"] = direction
            print(step)
            gcode.makeBlock(step)
            direction = "left"
        elif direction == "left":
            step["direction"] = direction
            gcode.makeBlock(step)
            direction = "right"

        if remaining_step is not None:
            remaining_step.update({"direction": direction})

    pass


class Worker(QObject):
    aSignal = Signal(object)
    step_number = 0
    last_cmode = None
    last_cmpos = None
    last_state = None
    pause_status = 0
    qq = 0

    def __init__(self):
        super(Worker, self).__init__()

    def start_send(self):
        old_step_id = 0
        while (1):
            gcode._iface_write("?")
            time.sleep(0.04)
            # print(current_program.q.empty())

            if gcode.cmode == "Idle":
                if current_program.q.empty() != True:
                    step = current_program.q.get(block=True, timeout=1)
                    if step["id"] != old_step_id:
                        gcode.makeBlock(step)
                        old_step = step["id"]
                        self.step_number = step["id"]
                        current_program.q.task_done()
                        time.sleep(0.2)

            # global remaining_step
            # if remaining_step != None:

            #   pass
            # create_blocks(current_program.current_step)

            if gcode.cmode == "Alarm":
                #                print(gcode.cmode)
                #                print(gcode.cmpos)
                #                print(gcode.cpn)
                pass

            if gcode.cmode == "Home":
                print(str(gcode.cmode) + " " + str(gcode.cmpos[0]) + " " + str(gcode.cmpos[1]))

            if gcode.cmode == "Run":
                print(str(gcode.cmode) + " " + str(gcode.cmpos[0]) + " " + str(gcode.cmpos[1]))

            if gcode.cmode == "Door":
                print(gcode.cmode)
                print(gcode.cmpos)
                print(gcode.cpn)
                # show_message("Открыта защитная дверь! Закройте дверь и нажмите кнопку \"Старт\" для продолжения намотки")

            if gcode.cmode == "Hold":
                print(gcode.cmode)
                print(gcode.cmpos)
                print(gcode.cpn)
                # show_message("Открыта защитная дверь! Закройте дверь и нажмите кнопку \"Старт\" для продолжения намотки")
                pass
            pass

            if gcode.cmode != self.last_cmode:
                self.last_cmode = gcode.cmode
                current_state = {
                    "RPM": str(current_program.current_step["rpm"]),
                    "layer": str(self.step_number),
                    "X": str(gcode.cmpos[0]),
                    "winding_count": str(round(float(gcode.cmpos[1]) * float(reducer_value), 2)),
                    "state": gcode.cmode,
                    # "qq": self.qq
                }
                self.aSignal.emit(current_state)

            if gcode.cmpos != self.last_cmpos:
                self.last_cmpos = gcode.cmpos
                current_state = {
                    "RPM": str(current_program.current_step["rpm"]),
                    "layer": str(self.step_number),
                    "X": str(gcode.cmpos[0]),
                    "winding_count": str(round(float(gcode.cmpos[1]) * float(reducer_value), 2)),
                    "state": gcode.cmode,
                    # "qq": self.qq
                }
                self.aSignal.emit(current_state)
                self.qq = self.qq + 1


active_property = ""


class MainWindow(QMainWindow):
    pause_status = 0

    def __init__(self):
        super().__init__()
        self.ui = QtUiTools.QUiLoader().load("main.ui")
        self.init_buttons()
        self.speed = 0
        self.winding_count_correction = 0
        self.winding_count = 0
        self.thread = QThread(parent=self)
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.start_send)
        self.worker.aSignal.connect(self.reportProgress)
        # Step 6: Start the thread
        self.thread.start()
        if ENABLE_CONTROLS is True:
            GPIO.add_event_detect(bPedal, GPIO.FALLING, self.pedal_counter)
        self.ui.show()
        self.update_ui()

        # self.ui.exec()

    def pedal_counter(self, pin):
        global pedal_percent
        pedal_percent = pedal_percent + 1

    def clear_pedal_value(self, data):
        global pedal_percent
        self.changeSpeed(pedal_percent)
        # print("speed set to:",pedal_percent)
        pedal_percent = 0

    def reportProgress(self, value):
        # self.ui.lcdNumber_6.setProperty("value", value["qq"])
        # widget.ui.lcdNumber_7.setProperty("value", value[1])
        self.winding_count = abs(round(float(value["winding_count"])-self.winding_count_correction, 0))
        # if self.winding_count_correction == 0:
        #     self.winding_count_correction = self.winding_count
        #
        # if self.winding_count_correction != self.winding_count:
        #     self.winding_count = abs(self.winding_count_correction - abs(self.winding_count))
        #     self.winding_count_correction = self.winding_count

        if str(value['state']).startswith('Hold'):
            self.ui.lblStatus.setProperty("text", 'Пауза')
        elif str(value['state']).startswith('Run'):
            self.ui.lblStatus.setProperty("text", 'Работа')
        elif str(value['state']).startswith('Idle'):
            self.ui.lblStatus.setProperty("text", 'Простой')
        elif str(value['state']).startswith('Alarm'):
            self.ui.lblStatus.setProperty("text", 'Тревога')
        elif str(value['state']).startswith('Home'):
            self.ui.lblStatus.setProperty("text", 'Калибровка')

        self.ui.lcdNumber_2.setProperty("value", value['RPM'])
        self.ui.lcdNumber_3.setProperty("value", value['layer'])
        self.ui.lcdNumber_4.setProperty("text", str(round(round(float(value['X']),3) + 498.5, 3)))
        self.ui.lcdNumber.setProperty("value", self.winding_count)

    def update_ui(self):
        global current_program
        self.ui.btnWindingCount.setText(
            "Намотка\n" + str(current_program.current_step.get("winding_count")))
        # builder.get_object('btnCycle').set_label(
        #   "Цикл\n" + str(current_program.current_step.get("cycle")))
        # self.ui.btnShift.setText(
        #    "Сдвиг\n" + str(current_program.current_step.get("shift")))
        self.ui.btnRPM.setText(
            "Обороты\n" + str(current_program.current_step.get("rpm")))
        # builder.get_object('btnJump').set_label(
        #   "Отскок\n" + str(current_program.current_step.get("jump")))
        self.ui.btnPTR.setText(
            "ПТР\n" + str(current_program.current_step.get("right_reverse_point")))
        self.ui.btnLTR.setText(
            "ЛТР\n" + str(current_program.current_step.get("left_reverse_point")))
        self.ui.btnWindingStep.setText(
            "Шаг н-ки.\n" + str(current_program.current_step.get("winding_step")))
        self.ui.btnPedal.setText(
            "Педаль\n" + str(pedal_state[pedal_mode]))
        if str(current_program.current_step.get("direction")) == "right":
            self.ui.btnDirection.setText(
                "Направление:\n вправо")
        elif str(current_program.current_step.get("direction")) == "left":
            self.ui.btnDirection.setText(
                "Направление:\n влево")
        if current_program.current_step["rotation_direction"] == "CW":
            self.ui.btnRotationDirection.setText("Напр. вращения:\n по часовой")
        elif current_program.current_step["rotation_direction"] == "CCW":
            self.ui.btnRotationDirection.setText("Напр. вращения:\n против часовой")
        # lcdStepNumber
        stepTXT = str(int(current_program.current_step_number) + 1) + " из " + str(current_program.step_count())
        self.ui.lcdStepNumber.setProperty("text", stepTXT)

    def button_start_handler(self):
        # global remaining_step
        # if remaining_step is None:
        #    remaining_step = current_program.current_step
        if current_program.current_step is not None:
            if int(current_program.current_step["winding_count"]) > 0:
                current_program.q.queue.clear()
                # gcode.windingClean()
                current_program.make_queue()
                if pedal_mode == "wind":
                    gcode.hold()
                    self.setMinimalSpeed()
                # print(list(current_program.q.queue))
        print('button_correction_handler')

    def getPropertyByButtonName(self, button_name):
        if button_name == "btnWindingCount":
            return "winding_count"
        if button_name == "btnWindingStep":
            return "winding_step"
        if button_name == "btnRPM":
            return "rpm"
        if button_name == "btnLTR":
            return "left_reverse_point"
        if button_name == "btnPTR":
            return "right_reverse_point"
        if button_name == "btnShift":
            return "shift"

    def set_by_numpad(self):
        global active_property
        action = None
        sender = self.sender()
        active_property = self.getPropertyByButtonName(sender.objectName())
        if sender.objectName() == "btnCopyStep":
            action = "copyStep"
        # @self.ui.btnLTR.setProperty("text", "123\n456")
        print(active_property)
        calc = CalcWindow(action=action)
        self.update_ui()
        pass

    def button_stepplus_handler(self):
        global current_program
        current_program.get_step_by_id(current_program.current_step_number + 1)
        self.update_ui()
        # prop.set_property(current_program.current_step+1)
        print('button_stepplus_handler current step:', current_program.current_step)

    def button_pedal_handler(self):
        global pedal_mode
        if pedal_mode == "none":
            pedal_mode = "wind"
        elif pedal_mode == "wind":
            self.changeSpeed(100)
            pedal_mode = "none"
        self.update_ui()

    def button_stepminus_handler(self):
        global current_program
        if current_program.current_step_number > 0:
            current_program.get_step_by_id(current_program.current_step_number - 1)
        print('button_stepminus_handler current step:', current_program.current_step)
        self.update_ui()

    def button_direction_handler(self):
        global current_program
        if current_program.current_step["direction"] == "left":
            current_program.current_step.update({"direction": "right"})
            self.ui.btnDirection.setText("Направление:\n Вправо")
        elif current_program.current_step["direction"] == "right":
            current_program.current_step.update({"direction": "left"})
            self.ui.btnDirection.setText("Направление:\n Влево")
        current_program.save_program('_current.json')
        print(current_program.current_step["direction"])

    def button_rotationdirection_handler(self):
        global current_program
        if current_program.current_step["rotation_direction"] == "CW":
            current_program.current_step.update({"rotation_direction": "CCW"})
            self.ui.btnRotationDirection.setText("Напр. вращения:\n против часовой")
        elif current_program.current_step["rotation_direction"] == "CCW":
            current_program.current_step.update({"rotation_direction": "CW"})
            self.ui.btnRotationDirection.setText("Напр. вращения:\n по часовой")
        current_program.save_program('_current.json')
        print('button_rotationdirection_handler')

    def delStep(self):
        if len(current_program.current_program) > 1:
            msg = QMessageBox(self)
            msg.setWindowTitle("Удаление шага")
            msg.setIcon(QMessageBox.Question)
            msg.setText("Вы действительно хотите удалить шаг?")

            buttonAccept = msg.addButton("Да", QMessageBox.YesRole)
            buttonCancel = msg.addButton("Нет", QMessageBox.RejectRole)
            msg.setDefaultButton(buttonCancel)
            msg.exec_()

            if msg.clickedButton() == buttonAccept:
                print(current_program.current_step_number)
                current_program.del_step(current_program.current_step_number)
                current_program.get_step_by_id(
                    (current_program.current_step_number - 1) if current_program.current_step_number > 0 else 0)
                self.update_ui()

    # def button_reducer_handler(self, button):
    #     global reducer_value
    #     if reducer_value == 2.5 or reducer_value == 0:
    #         self.ui.btnReducer.setText("Редуктор\n 2к1 \n Скорость 1")
    #         reducer_value = 0.62505
    #     elif reducer_value == 0.62505:
    #         self.ui.btnReducer.setText("Редуктор\n 1к2 \n Скорость 2")
    #         reducer_value = 2.5
    #     pass

    def button_resetX_handler(self):
        gcode.resetX()
        self.worker.last_cmode = None
        self.worker.last_cmpos = None
        pass

    def button_resetY_handler(self):
        # gcode.windingClean()
        print(gcode.cmpos)
        self.winding_count_correction = gcode.cmpos[1]
        self.worker.last_cmode = None
        self.worker.last_cmpos = None
        pass

    def button_reset_program_handler(self):
        gcode.softreset()
        gcode.killalarm()
        current_program.q.queue.clear()
        self.worker.last_cmode = None
        self.worker.last_cmpos = None
        pass

    def button_home_handler(self):
        self.setNormalSpeed()
        # time.sleep(0.5)
        self.winding_count_correction = 0
        gcode.home()


    def button_pause_handler(self):
        if pedal_mode != 'wind':
            if str(gcode.cmode).startswith("Hold"):
                gcode.resume()
                self.pause_status = 0
                print("PAUSE RELEASED")
            elif str(gcode.cmode).startswith("Idle") or str(gcode.cmode).startswith("Run"):
                  gcode.hold()
                  self.pause_status = 1
                  print("PAUSE SET")

    def button_trapezoid_handler(self):
        trapezoid = TrapezoidWindow()

    def init_buttons(self):
        self.ui.btnLTR.clicked.connect(self.set_by_numpad)
        self.ui.btnHint.clicked.connect(self.handle_hint_button)
        self.ui.btnCopyStep.clicked.connect(self.set_by_numpad)
        self.ui.btnDelStep.clicked.connect(self.delStep)
        self.ui.btnPTR.clicked.connect(self.set_by_numpad)
        self.ui.btnWindingStep.clicked.connect(self.set_by_numpad)
        self.ui.btnRPM.clicked.connect(self.set_by_numpad)
        # self.ui.btnShift.clicked.connect(self.set_by_numpad)
        self.ui.btnWindingCount.clicked.connect(self.set_by_numpad)
        self.ui.btnOpenProgram.clicked.connect(self.open_program)
        self.ui.btnSaveProgram.clicked.connect(self.save_program)
        self.ui.btnStepMinus.clicked.connect(self.button_stepminus_handler)
        self.ui.btnStepPlus.clicked.connect(self.button_stepplus_handler)
        self.ui.btnDirection.clicked.connect(self.button_direction_handler)
        self.ui.btnRotationDirection.clicked.connect(self.button_rotationdirection_handler)
        # self.ui.btnReducer.clicked.connect(self.button_reducer_handler)
        self.ui.btnHome.clicked.connect(self.button_home_handler)
        self.ui.btnStart.clicked.connect(self.button_start_handler)
        self.ui.btnResetY.clicked.connect(self.button_resetY_handler)
        # self.ui.btnResetX.clicked.connect(self.button_resetX_handler)
        self.ui.btnResetProgram.clicked.connect(self.button_reset_program_handler)
        self.ui.btnPedal.clicked.connect(self.button_pedal_handler)
        self.ui.btnPause.clicked.connect(self.button_pause_handler)
        # self.ui.btnTrapezoid.clicked.connect(self.button_trapezoid_handler)
        self.ui.speedSlider.valueChanged[int].connect(self.changeSpeed)

    def handle_hint_button(self):
        hintWindow = HintWindow()
        hintWindow = None
        print("handle picture")

    def show_hint(self):
        print("show hint")

    def changeSpeed(self, value):
        if value == 0:
            self.setMinimalSpeed()

        if value > self.speed:
            increaseValue = value - self.speed
            while increaseValue > 0:
                self.increaseSpeedByOne()
                increaseValue = increaseValue - 1
        elif value < self.speed:
            decrease_value = self.speed - value
            while decrease_value > 0:
                self.decreaseSpeedByOne()
                decrease_value = decrease_value - 1
        elif value == 1:
            self.setMinimalSpeed()
            gcode.resume()
        self.speed = value
        self.ui.lblSpeedRatio.setProperty("text", self.speed)

    def increaseSpeedByTen(self):
        gcode._iface.write_b("\x91")
        print("Ratio Increased by 10")

    def increaseSpeedByOne(self):

        gcode._iface.write_b("\x93")
        print("Ratio Increased by 1")

    def decreaseSpeedByTen(self):

        gcode._iface.write_b("\x92")
        print("Ratio Decreased by 10")

    def decreaseSpeedByOne(self):

        gcode._iface.write_b("\x94")
        print("Ratio Decreased by 1")

    def setNormalSpeed(self):
        gcode._iface.write_b("\x90")
        print("Ratio 100%")

    def setMinimalSpeed(self):
        gcode.hold()
        self.setNormalSpeed()
        self.decreaseSpeedByOne()
        x = 9
        while x > 0:
            self.decreaseSpeedByTen()
            x = x - 1
        x = 9
        while x > 1:
            self.decreaseSpeedByOne()
            x = x - 1

    def open_program(self):
        fileName = QFileDialog.getOpenFileName(self, "Открыть программу", "/media", "JSON Files (*.json)")
        if fileName is not None:
            current_program.open_program(fileName[0])
            print(fileName[0])
        self.update_ui()
        pass

    def save_program(self):
        proc = subprocess.Popen("onboard -x400 -y800", shell=True)
        fileName = QFileDialog.getSaveFileName(self, "Сохранить программу", "/media", "JSON Files (*.json)")

        if fileName[0] is not None:
            if str(fileName[0]).endswith(".json"):
                fileName = str(fileName[0])
                pass
            else:
                fileName = str(fileName[0]) + ".json"
            print("BEFORE")
            current_program.save_program(fileName)
            print("AFTER")

        proc = subprocess.Popen("killall onboard", shell=True)


offsetControl = None


class HintWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.hint_filename = None
        self.hint_index = 0
        self.hints = []
        self.ui = QtUiTools.QUiLoader().load("hint.ui")
        self.hints = list(current_program.current_step["hints"])
        self.init_buttons()
        self.ui.setModal(True)
        # self.ui.show()
        self.update_ui()
        self.ui.exec()

    def init_buttons(self):
        self.ui.btnClose.clicked.connect(self.close_clicked)
        self.ui.btnDeleteHint.clicked.connect(self.delete_hint_clicked)
        self.ui.btnAddHint.clicked.connect(self.add_hint_clicked)
        self.ui.btnPreviousHint.clicked.connect(self.previous_hint_clicked)
        self.ui.btnNextHint.clicked.connect(self.next_hint_clicked)
        self.ui.btnLoadImage.clicked.connect(self.load_image_clicked)
        self.ui.btnSave.clicked.connect(self.save_hint_clicked)
        self.ui.textEdit.textChanged.connect(self.update_description)

    def update_ui(self):
        if len(self.hints) <= self.hint_index or len(self.hints) == 0:
            self._append_hint()
        if self.hints[self.hint_index]["picture"] is not None:
            file = base64.b64decode(self.hints[self.hint_index]["picture"])
            pixmap = QPixmap()
            pixmap.loadFromData(file)
            pixmap = pixmap.scaled(self.ui.lblImage.width(), self.ui.lblImage.height())
            print(len(file))
            print("pixmap set")
            self.ui.lblImage.setPixmap(pixmap)
            self.ui.lblImage.update()
        if self.hints[self.hint_index]["description"] is not None:
            self.ui.textEdit.setHtml(self.hints[self.hint_index]["description"])

    def close_clicked(self):
        self.ui.close()

    def update_description(self):

        if len(self.hints) <= self.hint_index:
            self._append_hint()

        self.hints[self.hint_index].update({"description": self.ui.textEdit.toHtml()})
        # print(json.dumps(self.hints))
        print("description updated, hint index=", self.hint_index)

    def save_hint_clicked(self):
        global current_program
        current_program.current_step["hints"] = list(self.hints)
        current_program.save_program('_current.json')
        print("save_hint_clicked")

    def delete_hint_clicked(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Удаление подсказки")
        msg.setIcon(QMessageBox.Question)
        msg.setText("Вы действительно хотите удалить подсказку?")

        buttonAccept = msg.addButton("Да", QMessageBox.YesRole)
        buttonCancel = msg.addButton("Нет", QMessageBox.RejectRole)
        msg.setDefaultButton(buttonCancel)
        msg.exec_()

        if msg.clickedButton() == buttonAccept:
            del self.hints[self.hint_index]
        if self.hint_index >= len(self.hints):
            self.hint_index -= 1
        self.update_ui()
        print("delete hint")

    def add_hint_clicked(self):
        self._append_hint()
        self.hint_index = len(self.hints) - 1
        self.update_ui()
        print("add hint")

    def previous_hint_clicked(self):
        if self.hint_index > 0:
            self.hint_index -= 1
            self.update_ui()

    def next_hint_clicked(self):
        print("next_hint_clicked")
        if len(self.hints) > 1 and len(self.hints) > self.hint_index + 1:
            self.hint_index += 1
            self.update_ui()

    def _append_hint(self):
        print("appending hint")
        self.hints.append({
            "picture": "None",
            "description": "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\np, li { white-space: pre-wrap; }\n</style></head><body style=\" font-family:'Ubuntu'; font-size:11pt; font-weight:400; font-style:normal;\">\n<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Noto Sans, '; font-size:20pt; font-weight:600;\">\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a</span></p>\n<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-family:'Noto Sans, '; font-size:14pt;\"> Описание</span></p></body></html>"

        })

    def load_image_clicked(self, event):
        if len(self.hints) <= self.hint_index:
            self._append_hint()

        self.hint_filename = QFileDialog.getOpenFileName(self, "Открыть изображение", "/media",
                                                         "Image (*.png *.jpg *jpeg *.bmp)")
        print(self.hint_filename[0])
        if os.path.isfile(self.hint_filename[0]):
            file_name = self.hint_filename[0]

            pixmap = QPixmap(file_name).scaled(self.ui.lblImage.width(), self.ui.lblImage.height())
            self.ui.lblImage.setPixmap(pixmap)
            with open(file_name, 'rb') as file:
                self.hints[self.hint_index]["picture"] = base64.b64encode(file.read()).decode("ascii")

        print("load_image_clicked")


class TrapezoidWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.ui = QtUiTools.QUiLoader().load("trapezoid.ui")
        self.current_settings = dict(current_program.current_step["trapezoid_winding"])
        self.active_property = ""
        self.init_buttons()
        self.init_controls()
        self.ui.setModal(True)
        # self.ui.show()
        self.ui.exec()

    def init_buttons(self):
        self.ui.rLeftNotUsed.clicked.connect(self.rLeftNotUsed_clicked)
        self.ui.rRightNotUsed.clicked.connect(self.rRightNotUsed_clicked)
        self.ui.rLeftWide.clicked.connect(self.rLeftWide_clicked)
        self.ui.rRightWide.clicked.connect(self.rRightWide_clicked)
        self.ui.rLeftNarrow.clicked.connect(self.rLeftNarrow_clicked)
        self.ui.rRightNarrow.clicked.connect(self.rRightNarrow_clicked)
        self.ui.btnLeftOffset.clicked.connect(self.btnLeftOffset_clicked)
        self.ui.btnRightOffset.clicked.connect(self.btnRightOffset_clicked)
        self.ui.btnCancel.clicked.connect(self.cancel_clicked)
        self.ui.btnOK.clicked.connect(self.ok_clicked)

    def init_controls(self):

        if self.current_settings["left"]["type"] == "not_used":
            self.ui.rLeftNotUsed.setChecked(True)
        elif self.current_settings["left"]["type"] == "wide":
            self.ui.rLeftWide.setChecked(True)
        elif self.current_settings["left"]["type"] == "narrow":
            self.ui.rLeftNarrow.setChecked(True)

        if self.current_settings["right"]["type"] == "not_used":
            self.ui.rRightNotUsed.setChecked(True)
        elif self.current_settings["right"]["type"] == "wide":
            self.ui.rRightWide.setChecked(True)
        elif self.current_settings["right"]["type"] == "narrow":
            self.ui.rRightNarrow.setChecked(True)

        self.ui.btnLeftOffset.setText(self.current_settings["left"]["offset"])
        self.ui.btnRightOffset.setText(self.current_settings["right"]["offset"])

    def ok_clicked(self):
        global current_program
        pass

    def cancel_clicked(self):
        self.ui.close()

    def rLeftNotUsed_clicked(self):
        pass

    def rRightNotUsed_clicked(self):
        pass

    def rLeftWide_clicked(self):
        pass

    def rRightWide_clicked(self):
        pass

    def rLeftNarrow_clicked(self):
        pass

    def rRightNarrow_clicked(self):
        pass

    def btnLeftOffset_clicked(self):
        blah = 1
        ctrl = OffsetCalcWindow(blah)
        pass

    def btnRightOffset_clicked(self):
        blah = 2
        ctrl = OffsetCalcWindow(blah)
        pass


class CalcWindow(QDialog):
    def __init__(self, action=None):
        self.action = action
        super().__init__()
        self.ui = QtUiTools.QUiLoader().load("calc.ui")
        self.init_buttons()
        self.ui.setModal(True)
        # self.ui.show()
        self.ui.exec()

    def init_buttons(self):
        self.ui.btn0.clicked.connect(self.digit_clicked)
        self.ui.btn1.clicked.connect(self.digit_clicked)
        self.ui.btn2.clicked.connect(self.digit_clicked)
        self.ui.btn3.clicked.connect(self.digit_clicked)
        self.ui.btn4.clicked.connect(self.digit_clicked)
        self.ui.btn5.clicked.connect(self.digit_clicked)
        self.ui.btn6.clicked.connect(self.digit_clicked)
        self.ui.btn7.clicked.connect(self.digit_clicked)
        self.ui.btn8.clicked.connect(self.digit_clicked)
        self.ui.btn9.clicked.connect(self.digit_clicked)
        self.ui.btnDot.clicked.connect(self.digit_clicked)
        self.ui.btnDel.clicked.connect(self.del_clicked)
        self.ui.btnEnter.clicked.connect(self.enter_clicked)
        self.ui.btnClose.clicked.connect(self.close_clicked)

    def close_clicked(self):
        self.ui.close()
        print(active_property)
        print("close")

    def enter_clicked(self):
        global current_program
        global active_property
        if self.action is None:
            current_program.current_step.update({active_property: self.ui.lblNumber.text()})
            current_program.get_step_by_id(current_program.current_step_number).update({
                active_property: float(self.ui.lblNumber.text())})
        elif self.action == "copyStep":
            current_program.copy_step(int(self.ui.lblNumber.text()) - 1, current_program.current_step_number)
            current_program.current_step = current_program.get_step_by_id(current_program.current_step_number)

        current_program.save_program('_current.json')
        active_property = ""
        print('Enter pressed')
        self.ui.close()

    def digit_clicked(self):
        if len(str(self.ui.lblNumber.text())) < 12:
            s = self.sender()
            if s.text() in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'):
                self.ui.lblNumber.setProperty("text", str(self.ui.lblNumber.text()) + s.text())
            elif s.text() == '.':
                if str(self.ui.lblNumber.text()).find('.') < 0:
                    self.ui.lblNumber.setProperty("text", str(self.ui.lblNumber.text()) + s.text())

    def del_clicked(self):
        self.ui.lblNumber.setProperty("text", str(self.ui.lblNumber.text())[0:-1])


class OffsetCalcWindow(CalcWindow):
    _blah = 4

    def __init__(self, blah=3):
        self._blah = blah
        super().__init__()
        self.ui = QtUiTools.QUiLoader().load("calc.ui")
        self.init_buttons()
        self.ui.setModal(True)
        # self.ui.show()
        self.ui.exec()

    def enter_clicked(self):
        # print(self.current_settings)
        print(self._blah)


def init_space():
    global current_program
    try:
        if current_program.open_program('_current.json'):
            return
        else:
            current_program.new_program('_current.json')
    except Exception as E:
        print(E)


def pedal_up_callback(pin):
    time.sleep(.05)
    state = GPIO.input(pin)
    if state == 1:
        if gcode.cmode == "Idle":
            pass
        elif gcode.cmode == "Alarm":
            pass
        elif gcode.cmode == "Run":
            gcode.hold()
            pass
    else:
        if gcode.cmode == "Idle":
            if gcode.cmode == "Idle":
                if pedal_mode == "wind":
                    gcode.resume()
                if pedal_mode == "move":
                    if current_program.current_step["rotation_direction"] == "CW":
                        if reducer_value > 0:
                            gcode.move(0, 0.25 / reducer_value)
                            print("MOVE SENT CW")
                    elif current_program.current_step["rotation_direction"] == "CCW":
                        if reducer_value > 0:
                            gcode.move(0, -0.25 / reducer_value)
                            print("MOVE SENT CCW")
            pass
        elif str(gcode.cmode).startswith("Hold"):
            gcode.resume()  # здесь сбрасывается hold в том числе и при нажатой кнопке
            pass
        elif gcode.cmode == "Alarm":
            pass
    print(gcode.cmode)


def init_GPIO():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(bRed, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(bLeft, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(bRight, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(bUp, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(bDown, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(bPedal, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(bRed, GPIO.RISING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bLeft, GPIO.RISING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bRight, GPIO.RISING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bUp, GPIO.RISING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bDown, GPIO.RISING, button_callback, bouncetime=300)
    # GPIO.add_event_detect(bPedal, GPIO.FALLING, button_callback, bouncetime=300)

    # GPIO.add_event_detect(bPedal, GPIO.BOTH, pedal_up_callback, bouncetime=300)


if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    init_space()

    app = QApplication(sys.argv)
    if ENABLE_CONTROLS is True:
        init_GPIO()
    widget = MainWindow()
    sys.exit(app.exec_())
