import gi
import event_handlers

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

builder = Gtk.Builder()
builder.add_from_file('winding_bck.glade')
handlers = event_handlers.Handlers()
builder.connect_signals(handlers)


def get_element_by_id(widget, element_id):
    x = widget.get_toplevel().get_children()[0].get_children()
    print('get_element_by_id')


def init_space():
    try:
        if event_handlers.current_program.open_program('_current.json'):
            return
        else:
            event_handlers.current_program.new_program('_current.json')
    except Exception as E:
        print(E)


class FileChooserWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="FileChooser Example")

        box = Gtk.Box(spacing=6)
        self.add(box)

        button1 = Gtk.Button(label="Choose File")
        button1.connect("clicked", self.on_file_clicked)
        box.add(button1)

        button2 = Gtk.Button(label="Choose Folder")
        button2.connect("clicked", self.on_folder_clicked)
        box.add(button2)

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

    def on_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK
        )
        dialog.set_default_size(800, 400)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Select clicked")
            print("Folder selected: " + dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()


class UI:

    def __init__(self):
        print("INIT UI")
        # self.handles_obj = handlers.Handlers()

    def show_form(self, form_name, parent_form_name=None, property_name=None):

        window = builder.get_object(form_name)

        if form_name == 'mainWindow':
            window.lblWindingCount = builder.get_object('lblWindingCount')
            window.btnCycle = builder.get_object('btnCycle')
            window.btnWinding = builder.get_object('btnWinding')
            window.btnRightReversePoint = builder.get_object('btnRightReversePoint')
            window.btnShift = builder.get_object('btnShift')
            window.btnLeftReversePoint = builder.get_object('btnLeftReversePoint')
            window.btnJump = builder.get_object('btnJump')
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
                event_handlers.current_program.current_step.get(property_name)))
            window.set_transient_for(builder.get_object('mainWindow'))
            builder.get_object('mainWindow').set_sensitive(False)
            window.set_modal(True)

        if form_name == 'openDialog':
            window.set_transient_for(builder.get_object('mainWindow'))
            builder.get_object('mainWindow').set_sensitive(False)
            window.set_modal(True)

        window.show_all()
        window.connect("delete-event", Gtk.main_quit)
        init_space()
        self.update_ui()
        Gtk.main()

    def update_ui(self):
        builder.get_object('btnWinding').set_label(
            "Намотка\n" + str(event_handlers.current_program.current_step.get("winding_count")))
        builder.get_object('btnCycle').set_label(
            "Цикл\n" + str(event_handlers.current_program.current_step.get("cycle")))
        builder.get_object('btnShift').set_label(
            "Сдвиг\n" + str(event_handlers.current_program.current_step.get("shift")))
        builder.get_object('btnRPM').set_label(
            "Обороты\n" + str(event_handlers.current_program.current_step.get("rpm")))
        builder.get_object('btnJump').set_label(
            "Отскок\n" + str(event_handlers.current_program.current_step.get("jump")))
        builder.get_object('btnRightReversePoint').set_label(
            "ПТР\n" + str(event_handlers.current_program.current_step.get("right_reverse_point")))
        builder.get_object('btnLeftReversePoint').set_label(
            "ЛТР\n" + str(event_handlers.current_program.current_step.get("left_reverse_point")))
        builder.get_object('btnWindingStep').set_label(
            "Шаг н-ки.\n" + str(event_handlers.current_program.current_step.get("winding_step")))
        builder.get_object('btnPedal').set_label(
            "Педаль\n" + str(event_handlers.current_program.current_step.get("pedal")))
        builder.get_object('btnDirection').set_label(
            "Напр.\n" + str(event_handlers.current_program.current_step.get("direction")))
        builder.get_object('btnRotationDirection').set_label(
            "Напр.\n" + str(event_handlers.current_program.current_step.get("rotation_direction")))
        builder.get_object('lblStepNumber').set_text(
            "Шаг №\n" + str(event_handlers.current_program.current_step_number))

    def close_form(self):
        shared_controls = {

        }
        Gtk.main_quit()
