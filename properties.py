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
        'range': [0, 10000]
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
            'shift_speed': 100  # Скорость сдвига
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
                return True
        except Exception as exp:
            print(exp)
            return False
