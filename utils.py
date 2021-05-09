import enum

import game


class Direction(enum.Enum):
    LEFT = 0
    DOWN = 1
    UP = 2
    RIGHT = 3


class Coordinate:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, direction, value):
        if direction == Direction.LEFT:
            self.left(value)
        elif direction == Direction.UP:
            self.up(value)
        elif direction == Direction.DOWN:
            self.down(value)
        elif direction == Direction.RIGHT:
            self.right(value)
        else:
            raise ValueError("Invalid direction")

    def left(self, value):
        self.y -= value

    def up(self, value):
        self.x -= value

    def down(self, value):
        self.x += value

    def right(self, value):
        self.y += value


class SyntaxError(Exception):
    pass


class ArgumentError(Exception):
    pass


class ActionCannotBeDone(Exception):
    pass


class CommandSet:
    def __init__(self):
        self.cmd_list = []

    def nothing(self, *any_arg):
        pass

    def add_cmd(self, cmd):
        assert (type(cmd) == Command), 'cmd must be Command type'
        self.cmd_list.append(cmd)

    def get_cmds(self):
        return self.cmd_list

    def __parse_args(self, input_string):
        return input_string.split()

    def process_input_cmd(self, player, input_string):
        """process input command. If the command exists then execute the command function

        Args:
            player (Player): player
            input_string (str): the input string

        Raises:
            ArgumentError: 

        Returns:
            str: the result message from the command
            enum: the function that needed to jump_to
        """
        result = None
        jump_to = None
        args = self.__parse_args(input_string)

        if len(args) <= 0:
            return '', jump_to
        for cmd in self.cmd_list:
            if cmd.name == args[0]:
                try:
                    result = cmd.cmd_func(player, args)
                    jump_to = cmd.jump_to
                except ArgumentError as err:
                    result = '== Command: \'{}\' raise ArgumentError =='.format(args[0])
                    result += ''.join(err.args)
                    jump_to = None
                    break
                except ActionCannotBeDone as err:
                    result = '== Command: {} cannot be done! =='.format(args[0])
                    result += ''.join(err.args)
                    jump_to = None
                    break

        if result is None:
            result = '== Command: \'{}\' not found =='.format(args[0])

        return result, jump_to


class Command:
    def __init__(self, name, help_msg, cmd_func, jump_to):
        self.name = name
        self.help_msg = help_msg
        self.cmd_func = cmd_func
        self.jump_to = jump_to

    def get_help(self):
        return self.help_msg


class Renderer:
    def __init__(self, resolution=Coordinate(10, 10)):
        self.resolution = resolution

    def clear_screen(self):
        return '\n' * self.resolution.x

    def render_player_info(self, player):
        result = '-------------------------------\n'
        result += '| player name: {} |\n| login info: {} |\n'.format(player.name, player.addr)
        result += '------------------------------\n'
        return result

    def render_room_dict(self, room_dict: dict):
        result = 'Rooms: ===========\n'
        name: str
        for name, room in room_dict.items():
            result += '\t[Room: {} | [{}/{}] | status: {} |\n'.format(name,
                                                                      len(room.player_list),
                                                                      room.max_players,
                                                                      game.GameRoomStatus.get_status_string(room.status)
                                                                      )
        if len(room_dict) <= 0:
            result += 'It\'s empty here. You can be the first one UwU.\n'
        result += '==============='
        return result

    def render_command_set(self, command_set):
        cmd_list = command_set.get_cmds()
        result = 'Commands:\n'
        for cmd in cmd_list:
            result += '\t' + cmd.get_help() + '\n'
        return result

    def render_room_info(self, room):
        result = ''
        result += 'Room: [{}] ======\n'.format(room.name)
        result += 'players: [{}/{}]\n'.format(len(room.player_list), room.max_players)
        for p in room.player_list:
            result += '\t{}\n'.format(p.name)
        result += '================\n'
        result += 'Chat: ---------------\n'
        for c in room.chat_list:
            result += c + '\n'
        result += '----------------------\n'
        return result
