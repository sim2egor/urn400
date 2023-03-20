# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
# import event_handlers
import subprocess
from gc import callbacks
import queue
from gcodeGen import GcodeGen
import threading
import time
import math

import RPi.GPIO as GPIO

# 3 states: IDLE, START, STOP
STATE = 0

cnc_port = '/dev/ttyACM0'
cnc_speed = 115200
filename = "_current.json"
gcode = GcodeGen(cnc_port, cnc_speed)
# 2.5
# 0.626
reducer_value = 2.5

remaining_step = None


class WINDING:
    def get_programs(self):
        print('not finished yet')
        return 0

    def open_program(self, program):
        print('not finished yet')
        return 0


states = {
    'IDLE': 0,
    'START': 1,
    'STOP': 2,
}


def set_state(state_received, STATE=None):
    if state_received in states:
        if states[state_received] != STATE:
            STATE = states[state_received]
            return 0
        else:
            return 0
    else:
        return 1


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


def create_blocks(self, step):
    global remaining_step
    step = dict(remaining_step)
    step.update({"winding_count": float(step["winding_count"]) / float(reducer_value)})
    step.update({"winding_step": float(step["winding_step"]) * float(reducer_value)})
    step.update({"rpm": float(step["rpm"]) / float(reducer_value)})

    block_count = math.ceil(float(step["winding_count"]) * float(step["winding_step"]) / abs(
        float(step["left_reverse_point"]) - float(step["right_reverse_point"])))
    direction = step["direction"]
    winding_count_remaining = float(step["winding_count"])
    winding_count_per_layer = abs(float(step["left_reverse_point"]) - float(step["right_reverse_point"])) / float(
        step["winding_step"])

    for layer_number in (1, block_count + 1):
        builder.get_object("lblLayer").set_text(str(layer_number))
        if winding_count_remaining <= 0:
            return
        if winding_count_remaining >= winding_count_per_layer:
            step.update({"winding_count": winding_count_per_layer})
            print("winding_count", winding_count_per_layer)
            winding_count_remaining = winding_count_remaining - winding_count_per_layer
            remaining_step.update({"winding_count": float(winding_count_remaining)})
            #remaining_step.update({"winding_count": float(winding_count_remaining)*float(reducer_value)})

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


# Press the green button in the gutter to run the script.


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
import json

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


class PROGRAM(PROPERTIES):

    def __init__(self):
        self.current_program = []
        self.current_property = ''
        self.file_name = ''
        self.current_step_number = 0
        self.current_step = None
        self.q = queue.Queue()

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
            'layer_stop': 0
        }
        self.current_program.append(empty_step)
        self.save_program('_current.json')

    def new_program(self, filename):
        try:
            with open(filename, 'w') as write_file:
                self.current_program = []
                self.add_step()
                json.dump(self.current_program, write_file)
                return 0
        except Exception as exp:
            print(exp)
            return 1

    def save_program(self, filename):
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
                ui.update_ui()
                return True
        except Exception as exp:
            print(exp)
            return False

    def make_queue(self):
        # self.q.mutex.acquire()
        # self.q.queue.clear()

        step = dict(self.current_step)
        step.update({"winding_count": float(step["winding_count"]) / float(reducer_value)})
        #step.update({"winding_step": float(step["winding_count"]) * float(reducer_value)})
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


class Handlers:
    _thread_statechange = None
    last_cmode = None
    last_cmpos = None
    last_state = None
    pause_status = 0
    step_number = 0

    def __init__(self):
        self.calcUI = None
        self.openProgramDialog = None
        self.active_property = None

        if self._thread_statechange is None:
            self._thread_statechange = threading.Thread(target=self.poll_state)
            self._thread_statechange.start()
            # print("{}: State change polling started".format(self.name))
        else:
            pass
            # print("{}: State change polling already running...".format(self.name))

    def poll_state(self):
        old_step_id = 0
        while (1):
            gcode._iface_write("?")
            time.sleep(0.5)
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
                print(gcode.cmode)
                print(gcode.cmpos)
                print(gcode.cpn)

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
            self.last_cmode = gcode.cmode

            if gcode.cmpos != self.last_cmpos:
                self.last_cmpos = gcode.cmpos
                builder.get_object("lblRPM").set_text(str(current_program.current_step["rpm"]))
                builder.get_object("lblLayer").set_text(str(self.step_number))
                builder.get_object("lblX").set_text(str(gcode.cmpos[0]))
                builder.get_object("lblWindingCount").set_text(str(round(float(gcode.cmpos[1])*float(reducer_value),2)))
                pass

    def set_property_by_numpad(self, property_name):
        self.active_property = property_name
        print(self.active_property)
        ui.show_form('calcWindow', property_name=property_name)

    def quit_form_handler(self, button):
        button.get_toplevel().hide()
        builder.get_object('mainWindow').set_sensitive(True)
        self.active_property = None
        print('That\'s button')

    def numeric_handler(self, button):
        print(str(button.get_toplevel().lblResult.get_label()).find('.'))
        if str(button.get_toplevel().lblResult.get_label()).find('.') >= 0 and str(button.get_label()) == '.':
            return
        button.get_toplevel().lblResult.set_text(button.get_toplevel().lblResult.get_label() + button.get_label())
        print(button.get_label())
        x = is_property_valid('rotation_direction', 'CWW')
        y = 0

    def open_dialog_ok_handler(self, button):
        print(button.get_toplevel().get_filename())
        button.get_toplevel().hide()
        ui.update_ui(self)
        builder.get_object('mainWindow').set_sensitive(True)
        pass

    def open_dialog_cancel_handler(self, button):
        button.get_toplevel().hide()
        ui.update_ui(self)
        builder.get_object('mainWindow').set_sensitive(True)
        pass

    def button_enter_handler(self, button):
        global current_program
        current_program.current_step.update({self.active_property: button.get_toplevel().lblResult.get_label()})
        current_program.get_step_by_id(current_program.current_step_number).update({
            self.active_property: float(button.get_toplevel().lblResult.get_label())})
        current_program.save_program('_current.json')
        button.get_toplevel().hide()
        ui.update_ui()
        builder.get_object('mainWindow').set_sensitive(True)
        print('Enter pressed')

    def button_del_handler(self, button):
        button.get_toplevel().lblResult.set_text(button.get_toplevel().lblResult.get_label()[0:-1])
        print('Del pressed')

    def button_stoplayer_handler(self, button):
        if int(current_program.current_step["layer_stop"]) == 0:
            builder.get_object("btnStopLayer").set_label("СТОП_СЛОЙ\nВКЛ")
            current_program.current_step.update({"layer_stop": 1})
        else:
            builder.get_object("btnStopLayer").set_label("СТОП_СЛОЙ\nВЫКЛ")
            current_program.current_step.update({"layer_stop": 0})
        current_program.save_program("_current.json")
        print('Stop layer pressed')

    def button_handler(self, button):
        print('Button pressed')

    def button_reducer_handler(self, button):
        global reducer_value
        if reducer_value == 2.5:
            builder.get_object("btnReducer").set_label("Редуктор\n 2к1 \n Коэффициент 0.5")
            reducer_value = 0.624
        elif reducer_value == 0.624:
            builder.get_object("btnReducer").set_label("Редуктор\n 1к2 \n Коэффициент 2")
            reducer_value = 2.5
        pass

    def button_load_image_handler(self, button):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file('sunshine.png')
        print("load image")

    def button_stepplus_handler(self, button):
        global current_program
        current_program.get_step_by_id(current_program.current_step_number + 1)
        ui.update_ui()
        # prop.set_property(current_program.current_step+1)
        print('button_stepplus_handler current step:', current_program.current_step)

    def button_stepminus_handler(self, button):
        global current_program
        if current_program.current_step_number > 0:
            current_program.get_step_by_id(current_program.current_step_number - 1)
        print('button_stepminus_handler current step:', current_program.current_step)
        ui.update_ui()

    def button_leftreversepoint_handler(self, button):
        self.set_property_by_numpad('left_reverse_point');
        print('button_leftreversepoint_handler')

    def button_windingstep_handler(self, button):
        self.set_property_by_numpad('winding_step');
        print('button_windingstep_handler')

    def button_rightreversepoint_handler(self, button):
        self.set_property_by_numpad('right_reverse_point');
        print('button_rightreversepoint_handler')

    def button_cycle_handler(self, button):

        print('button_cycle_handler')

    def button_shift_handler(self, button):
        self.set_property_by_numpad('shift');
        print('button_shift_handler')

    def button_direction_handler(self, button):
        if current_program.current_step["direction"] == "left":
            current_program.current_step.update({"direction": "right"})
            builder.get_object("btnDirection").set_label("Направление:\n Вправо")
        elif current_program.current_step["direction"] == "right":
            current_program.current_step.update({"direction": "left"})
            builder.get_object("btnDirection").set_label("Направление:\n Влево")
        current_program.save_program('_current.json')
        print(current_program.current_step["direction"])

    def button_rotationdirection_handler(self, button):
        if current_program.current_step["rotation_direction"] == "CW":
            current_program.current_step.update({"rotation_direction": "CCW"})
            builder.get_object("btnRotationDirection").set_label("Направление вращения:\n против часовой")
        elif current_program.current_step["rotation_direction"] == "CCW":
            current_program.current_step.update({"rotation_direction": "CW"})
            builder.get_object("btnRotationDirection").set_label("Направление вращения:\n по часовой")
        current_program.save_program('_current.json')
        print('button_rotationdirection_handler')

    def button_rpm_handler(self, button):
        self.set_property_by_numpad('rpm')
        print('button_rpm_handler')

    def button_jump_handler(self, button):
        self.set_property_by_numpad('jump')
        print('button_jump_handler')

    def button_correction_handler(self, button):
        # global remaining_step
        # if remaining_step is None:
        #    remaining_step = current_program.current_step
        if current_program.current_step is not None:
            if int(current_program.current_step["winding_count"]) > 0:
                current_program.q.queue.clear()
                gcode.windingClean()
                current_program.make_queue()
                print(list(current_program.q.queue))
        print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')

    def button_pedal_handler(self, button):
        self.set_property_by_numpad('pedal')
        print('button_pedal_handler')

    def button_functions_handler(self, button):
        print('button_functions_handler')

    def button_pause_handler(self, button):
        if self.pause_status == 0:
            gcode.hold()
            builder.get_object("btnPause").set_label("Возобновить")
            self.pause_status = 1
            time.sleep(1)
        elif self.pause_status == 1:
            gcode.resume()
            builder.get_object("btnPause").set_label("Пауза")
            self.pause_status = 0
            time.sleep(1)

    def button_windng_handler(self, button):
        self.set_property_by_numpad('winding_count')
        print('button_windng_handler')

    def button_open_program_handler(self, button):
        fc = FileChooserWindow()
        current_program.open_program(filename=filename)
        print('button_open_program_handler')

    def button_save_program_handler(self, button):
        proc = subprocess.Popen("onboard")
        fc = FileChooserWindow(action="save")
        current_program.save_program(filename=filename)
        proc.kill()
        print('button_save_program_handler')

    def button_reset_coordinates_handler(self, button):
        current_program.q.queue.clear()
        gcode.softreset()
        gcode.home()
        print("Reset coordinates")

    def button_menu_handler(self, button):
        print('button_menu_handler')

    def update_ui(self, x, y):
        print('set_focus')


import gi

gi.require_version('Gtk', '3.0')
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf

builder = Gtk.Builder()
builder.add_from_file('winding_bck.glade')
handlers = Handlers()
builder.connect_signals(handlers)


def get_element_by_id(widget, element_id):
    x = widget.get_toplevel().get_children()[0].get_children()
    print('get_element_by_id')


def init_space():
    global current_program
    try:
        if current_program.open_program('_current.json'):
            return
        else:
            current_program.new_program('_current.json')
    except Exception as E:
        print(E)


class FileChooserWindow(Gtk.Window):
    r = ""

    def __init__(self, action="open"):
        global filename
        if action == "open":
            dialog = Gtk.FileChooserDialog("Выберите файл", None,
                                           Gtk.FileChooserAction.OPEN,
                                           (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                            Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        else:
            dialog = Gtk.FileChooserDialog("Выберите файл", None,
                                           Gtk.FileChooserAction.SAVE,
                                           (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                            Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        self.add_filters(dialog)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Open clicked")
            print("File selected: " + dialog.get_filename())
            filename = dialog.get_filename()

        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()

    def add_filters(self, dialog):
        filter_text = Gtk.FileFilter()
        filter_text.set_name("JSON program files")
        filter_text.add_mime_type("application/json")
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)


class UI:

    def __init__(self):
        print("INIT UI")
        # self.handles_obj = handlers.Handlers()

    def show_form(self, form_name, parent_form_name=None, property_name=None):
        global current_program

        window = builder.get_object(form_name)

        if form_name == 'mainWindow':
            init_space()
            window.lblWindingCount = builder.get_object('lblWindingCount')
            # window.btnCycle = builder.get_object('btnCycle')
            window.btnWinding = builder.get_object('btnWinding')
            window.btnRightReversePoint = builder.get_object('btnRightReversePoint')
            window.btnShift = builder.get_object('btnShift')
            window.btnLeftReversePoint = builder.get_object('btnLeftReversePoint')
            # window.btnJump = builder.get_object('btnJump')
            window.btnPedal = builder.get_object('btnPedal')
            window.btnEnterExit = builder.get_object('btnEnterExit')
            window.btnCorrection = builder.get_object('btnCorrection')
            window.btnProgram = builder.get_object('btnProgram')
            window.btnFunctions = builder.get_object('btnFunctions')
            window.btnWindingStep = builder.get_object('btnWindingStep')
            window.btnPause = builder.get_object('btnPause')
            window.btnRPM = builder.get_object('btnRPM')
            window.btnMenu = builder.get_object('btnMenu')
            window.btnStepMinus = builder.get_object('btnStepMinus')
            window.btnStepPlus = builder.get_object('btnStepPlus')

        if form_name == 'calcWindow':
            window.lblResult = builder.get_object('lblResult')
            window.lblResult.set_text(str(
                current_program.current_step.get(property_name)))
            window.set_transient_for(builder.get_object('mainWindow'))
            builder.get_object('mainWindow').set_sensitive(False)
            window.set_modal(True)

        if form_name == 'openDialog':
            window.set_transient_for(builder.get_object('mainWindow'))
            builder.get_object('mainWindow').set_sensitive(False)
            window.set_modal(True)

        window.show_all()
        window.connect("delete-event", Gtk.main_quit)

        self.update_ui()
        Gtk.main()

    def update_ui(self):
        global current_program
        builder.get_object('btnWinding').set_label(
            "Намотка\n" + str(current_program.current_step.get("winding_count")))
        # builder.get_object('btnCycle').set_label(
        #   "Цикл\n" + str(current_program.current_step.get("cycle")))
        builder.get_object('btnShift').set_label(
            "Сдвиг\n" + str(current_program.current_step.get("shift")))
        builder.get_object('btnRPM').set_label(
            "Обороты\n" + str(current_program.current_step.get("rpm")))
        # builder.get_object('btnJump').set_label(
        #   "Отскок\n" + str(current_program.current_step.get("jump")))
        builder.get_object('btnRightReversePoint').set_label(
            "ПТР\n" + str(current_program.current_step.get("right_reverse_point")))
        builder.get_object('btnLeftReversePoint').set_label(
            "ЛТР\n" + str(current_program.current_step.get("left_reverse_point")))
        builder.get_object('btnWindingStep').set_label(
            "Шаг н-ки.\n" + str(current_program.current_step.get("winding_step")))
        builder.get_object('btnPedal').set_label(
            "Педаль\n" + str(current_program.current_step.get("pedal")))
        if str(current_program.current_step.get("direction")) == "right":
            builder.get_object('btnDirection').set_label(
                "Направление:\n вправо")
        elif str(current_program.current_step.get("direction")) == "left":
            builder.get_object('btnDirection').set_label(
                "Направление:\n влево")
        if current_program.current_step["rotation_direction"] == "CW":
            builder.get_object("btnRotationDirection").set_label("Направление вращения:\n по часовой")
        elif current_program.current_step["rotation_direction"] == "CCW":
            builder.get_object("btnRotationDirection").set_label("Направление вращения:\n против часовой")
        builder.get_object('lblStepNumber').set_text(
            "Шаг № " + str(current_program.current_step_number))

    def on_file_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a file", parent=self, action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        self.add_filters(dialog)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Open clicked")
            print("File selected: " + dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()

    def add_filters(self, dialog):
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        filter_py = Gtk.FileFilter()
        filter_py.set_name("Python files")
        filter_py.add_mime_type("text/x-python")
        dialog.add_filter(filter_py)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

    def close_form(self):
        shared_controls = {

        }
        Gtk.main_quit()


ui = UI()

bRed = 13
bLeft = 27
bRight = 6
bUp = 26
bDown = 5
bPedal = 17


def button_callback(pin):
    if pin == bRed:
        gcode.resume()
    elif pin == bLeft:
        gcode.move(-1, 0)
    elif pin == bRight:
        gcode.move(1, 0)
    elif pin == bUp:
        gcode.move(0, 0.1)
    elif pin == bDown:
        gcode.move(0, -0.1)


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
            pass
        elif str(gcode.cmode).startswith("Hold"):
            gcode.resume()
            pass
        elif gcode.cmode == "Alarm":
            pass
    print(gcode.cmode)

if __name__ == '__main__':
    # GLib.thread_init(None)
    threading.Thread(target=lambda: None).start()
    GObject.threads_init()

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(bRed, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(bLeft, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(bRight, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(bUp, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(bDown, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(bPedal, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(bRed, GPIO.FALLING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bLeft, GPIO.FALLING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bRight, GPIO.FALLING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bUp, GPIO.FALLING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bDown, GPIO.FALLING, button_callback, bouncetime=300)
    # GPIO.add_event_detect(bPedal, GPIO.FALLING, button_callback, bouncetime=300)
    GPIO.add_event_detect(bPedal, GPIO.BOTH, pedal_up_callback, bouncetime=300)

    gcode.home()
    Gdk.threads_enter()
    ui.show_form('mainWindow')
    Gdk.threads_leave()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
