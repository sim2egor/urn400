import properties

import user_interface

prop = properties.PROPERTIES()
current_program = properties.PROGRAM()


class Handlers:

    def __init__(self):
        self.calcUI = None
        self.openProgramDialog = None
        self.active_property = None

    def set_property_by_numpad(self, property_name):
        self.active_property = property_name
        print(self.active_property)
        self.calcUI = user_interface.UI()
        self.calcUI.show_form('calcWindow', property_name=property_name)

    def quit_form_handler(self, button):
        button.get_toplevel().hide()
        user_interface.builder.get_object('mainWindow').set_sensitive(True)
        self.active_property = None
        print('That\'s button')

    def numeric_handler(self, button):
        print(str(button.get_toplevel().lblResult.get_label()).find('.'))
        if str(button.get_toplevel().lblResult.get_label()).find('.') >= 0 and str(button.get_label()) == '.':
            return
        button.get_toplevel().lblResult.set_text(button.get_toplevel().lblResult.get_label() + button.get_label())
        print(button.get_label())
        x = properties.is_property_valid('rotation_direction', 'CWW')
        y = 0

    def open_dialog_ok_handler(self, button):
        print(button.get_toplevel().get_filename())
        button.get_toplevel().hide()
        user_interface.UI.update_ui(self)
        user_interface.builder.get_object('mainWindow').set_sensitive(True)
        pass

    def open_dialog_cancel_handler(self, button):
        button.get_toplevel().hide()
        user_interface.UI.update_ui(self)
        user_interface.builder.get_object('mainWindow').set_sensitive(True)
        pass

    def button_enter_handler(self, button):
        current_program.current_step.update({self.active_property: button.get_toplevel().lblResult.get_label()})
        current_program.get_step_by_id(current_program.current_step_number).update({
            self.active_property: button.get_toplevel().lblResult.get_label()})
        current_program.save_program('_current.json')
        button.get_toplevel().hide()
        user_interface.UI.update_ui(self)
        user_interface.builder.get_object('mainWindow').set_sensitive(True)
        print('Enter pressed')

    def button_del_handler(self, button):
        button.get_toplevel().lblResult.set_text(button.get_toplevel().lblResult.get_label()[0:-1])
        print('Del pressed')

    def button_handler(self, button):
        print('Button pressed')

    def button_stepplus_handler(self, button):
        current_program.get_step_by_id(current_program.current_step_number + 1)
        user_interface.UI.update_ui(self)
        # prop.set_property(current_program.current_step+1)
        print('button_stepplus_handler current step:', current_program.current_step)

    def button_stepminus_handler(self, button):
        if current_program.current_step_number > 0:
            current_program.get_step_by_id(current_program.current_step_number - 1)
        print('button_stepminus_handler current step:', current_program.current_step)
        user_interface.UI.update_ui(self)

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
        print('button_direction_handler')

    def button_rotationdirection_handler(self, button):
        print('button_rotationdirection_handler')

    def button_rpm_handler(self, button):
        self.set_property_by_numpad('rpm')
        print('button_rpm_handler')

    def button_jump_handler(self, button):
        self.set_property_by_numpad('jump')
        print('button_jump_handler')

    def button_correction_handler(self, button):

        print('button_correction_handler')

    def button_pedal_handler(self, button):
        self.set_property_by_numpad('pedal')
        print('button_pedal_handler')

    def button_functions_handler(self, button):
        print('button_functions_handler')

    def button_pause_handler(self, button):
        print('button_pause_handler')

    def button_windng_handler(self, button):
        self.set_property_by_numpad('winding_count')
        print('button_windng_handler')

    def button_program_handler(self, button):
        print(self.active_property)
        self.openProgramDialog = user_interface.UI()
        self.openProgramDialog.show_form('openDialog')
        print('button_program_handler')

    def button_menu_handler(self, button):
        print('button_menu_handler')

    def update_ui(self, x, y):
        print('set_focus')
