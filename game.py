import threading
import enum
import socket

import utils

CLIENT_RECV_MAX_SIZE = 1024


class PlayerInGame:
    def __init__(self, speed=1, max_hp=3):
        self.pos = utils.Coordinate(0, 0)
        self.speed = speed
        self.hp = 0
        self.max_hp = max_hp
    
    def game_start_init(self, pos):
        self.pos = pos
        self.hp = self.max_hp

    def move(self, direction):
        self.pos.move(direction, self.speed)

    def hit(self, direction):
        pass


class GameRoomManager:
    __instance = None

    def __init__(self):
        assert (GameRoomManager.__instance is None), 'GameRoomManager is singleton design. Only one instance can exist'
        self.list_lock = threading.Lock()
        self.room_dict = dict()
    
    @classmethod
    def init_instance(cls):
        if cls.__instance is None:
            cls.__instance = GameRoomManager()

    @classmethod
    def add_room(cls, name, room):
        cls.__instance.list_lock.acquire()
        cls.__instance.room_dict[name] = room
        cls.__instance.list_lock.release()
    
    @classmethod
    def create_room(cls, name, host):
        if name in cls.__instance.room_dict:
            raise utils.ActionCannotBeDone('room name duplicated')
        room = GameRoom(name, host)
        cls.add_room(name, room)
        return room

    @classmethod
    def remove_room(cls, name):
        cls.__instance.list_lock.acquire()
        cls.__instance.room_dict.pop(name, None)
        cls.__instance.list_lock.release()
    
    @classmethod
    def get_room(cls, name):
        return cls.__instance.room_dict[name]

    @classmethod
    def get_room_dict(cls) -> dict:
        return cls.__instance.room_dict


class GameRoomStatus(enum.Enum):
    WAITING = 0
    FULL = 1
    GAMING = 2

    @classmethod
    def get_status_string(cls, code):
        if code == cls.WAITING:
            return 'waiting'
        elif code == cls.FULL:
            return 'full'
        elif code == cls.GAMING:
            return 'gaming'
        else:
            return 'idk it\'s out of control'


class GameRoom:
    def __init__(self, name, host_player):
        self.name = name
        self.player_list = []
        self.player_list.append(host_player)
        self.host = host_player
        self.max_players = 2
        self.status = GameRoomStatus.WAITING
        self.chat_list = []
        self.chat_limit = 10
        self.__room_bot = Player(None, (None, None))
        self.__room_bot.name = 'room_system'

        self.player_list_lock = threading.Lock()
        self.chat_lock = threading.Lock()

    def render_room_view(self, player):
        result = ''
        result += player.renderer.render_player_info(player)
        result += player.renderer.render_room_info(self)
        return result

    def delete_room(self):
        # force leave all player
        for p in self.player_list:
            self.player_leave(p)
        GameRoomManager.remove_room(self.name)  # wait for garbage collection~

    def force_broadcast(self, player):
        for p in self.player_list:
            if p != player:
                try:
                    new_view = self.render_room_view(p).encode()
                    p.client.send(new_view)
                except:
                    self.player_leave(p)
                    p.client.close()

    def player_join(self, player):
        self.player_list_lock.acquire()
        if len(self.player_list) >= self.max_players:
            raise utils.ActionCannotBeDone('The room is full')
        self.player_list.append(player)
        if len(self.player_list) == self.max_players:
            self.status = GameRoomStatus.FULL
        self.say(self.__room_bot, '{} join the room'.format(player.name))
        self.player_list_lock.release()

    def player_leave(self, player):
        self.player_list_lock.acquire()
        self.player_list.remove(player)

        if len(self.player_list) < self.max_players:
            self.status = GameRoomStatus.WAITING
        if len(self.player_list) <= 0:
            self.delete_room()

        self.say(self.__room_bot, '{} leave the room'.format(player.name))
        if player == self.host and len(self.player_list) > 0:
            self.host = self.player_list[0]
            self.say(self.__room_bot, '{} become the new host'.format(self.host.name))
        self.player_list_lock.release()

    def say(self, player, content):
        self.chat_lock.acquire()
        if len(self.chat_list) > self.chat_limit:
            self.chat_list.pop(0)
        self.chat_list.append('[{}]: {}'.format(player.name, content))
        self.force_broadcast(player)
        self.chat_lock.release()

    def init_game(self):
        pass

    def start_game(self):
        pass


class RoomConsole(utils.CommandSet):
    def __init__(self):
        super(RoomConsole, self).__init__()
        self.add_cmd(utils.Command('ready', 'ready', self.nothing, PlayerStatus.ROOM))
        self.add_cmd(utils.Command('start', 'start', self.nothing, PlayerStatus.ROOM))
        self.add_cmd(utils.Command('leave', 'leave', self.leave_func, PlayerStatus.LOBBY))
        self.add_cmd(utils.Command('say', 'say [content]', self.say_func, PlayerStatus.ROOM))

    @staticmethod
    def leave_func(player, args):
        player.game_room.player_leave(player)
        room_name = player.game_room.name
        player.game_room = None
        return '== you leave the room: {} !=='.format(room_name)

    @staticmethod
    def say_func(player, args):
        if len(args) <= 1:
            raise utils.ArgumentError
        content = ''
        for i in range(1, len(args)):
            content += args[i] + ' '
        player.game_room.say(player, content)
        return '== you said sth !=='


class LobbyConsole(utils.CommandSet):
    def __init__(self):
        super(LobbyConsole, self).__init__()
        self.add_cmd(utils.Command('setname', 'setname [your nick name]', self.setname_func, PlayerStatus.LOBBY))
        self.add_cmd(utils.Command('create', 'create [room name]', self.create_room_func, PlayerStatus.ROOM))
        self.add_cmd(utils.Command('join', 'join [room name]', self.join_room_func, PlayerStatus.ROOM))
        self.add_cmd(utils.Command('refresh', 'refresh', self.refresh_func, PlayerStatus.LOBBY))
        self.add_cmd(utils.Command('exit', 'exit', self.exit_func, PlayerStatus.DISCONNECTED))

    @staticmethod
    def setname_func(player, args):
        if len(args) < 2:
            raise utils.ArgumentError
        name = ''
        for i in range(1, len(args)):
            name += args[i]
        player.name = name
        return '== set your name to \'{}\'! =='.format(player.name)

    @staticmethod
    def refresh_func(player, args):
        return '== refresh page! =='

    @staticmethod
    def create_room_func(player, args):
        if len(args) < 2:
            raise utils.ArgumentError
        room = GameRoomManager.create_room(args[1], player)
        player.game_room = room
        return '== Game room created! =='

    @staticmethod
    def join_room_func(player, args):
        if len(args) < 2:
            raise utils.ArgumentError
        room = GameRoomManager.get_room(args[1])
        player.game_room = room
        room.player_join(player)
        return '== join the room! =='

    @staticmethod
    def exit_func(player, args):
        return '== Exit! =='

    def render_lobby(self, player):
        result = ''
        result += 'Online players: {}\n'.format(Player.online_player_number)
        result += player.renderer.render_player_info(player)
        result += player.renderer.render_room_dict(GameRoomManager.get_room_dict())
        result += '\nPlease enter the command'
        result += player.renderer.render_command_set(self)
        return result


class PlayerStatus(enum.Enum):
    DISCONNECTED = 0
    LOBBY = 1
    ROOM = 2
    IN_GAME = 3


class Player:
    online_player_number = 0

    def __init__(self, client, addr):
        """
        Args:
            client (socket.socket): the socket client
            addr (tuple): the information of the socket client
        """
        self.client = client
        self.addr = addr
        self.status = PlayerStatus.DISCONNECTED
        self.name = addr[1]
        self.game_room = None
        self.renderer = utils.Renderer()

    def on_connect(self):
        # Print some welcoming messages; then entering the lobby console
        Player.online_player_number += 1
        welcome_msg = "Welcome to the server!\nNumber of online player:{}\n".format(Player.online_player_number)
        self.client.send(welcome_msg.encode())
        self.lobby_console()
        #TODO: set name before entering the lobby

    def disconnect(self):
        self.client.close()
        Player.online_player_number -= 1
        exit()

    def lobby_console(self):
        self.status = PlayerStatus.LOBBY
        console = LobbyConsole()
        while True:
            # render lobby
            lobby_view = console.render_lobby(self).encode()
            self.client.send(lobby_view)
            # get input
            input_str = self.client.recv(CLIENT_RECV_MAX_SIZE).decode()
            # clear screen
            self.client.send(self.renderer.clear_screen().encode())

            if len(input_str) == 0:
                self.disconnect()

            # Process input
            result, jump_to = console.process_input_cmd(self, input_str)
            self.client.send((result + '\n').encode())

            # Change stage or not
            if jump_to == PlayerStatus.DISCONNECTED:
                self.status = jump_to
                self.disconnect()
            elif jump_to == PlayerStatus.ROOM:
                self.status = jump_to
                self.room_console()

    def room_console(self):
        console = RoomConsole()
        room = self.game_room
        while self.status == PlayerStatus.ROOM:
            room_view = room.render_room_view(self).encode()
            self.client.send(room_view)
            input_str = self.client.recv(CLIENT_RECV_MAX_SIZE).decode()

            if len(input_str) == 0:
                self.disconnect()
            result, jump_to = console.process_input_cmd(self, input_str)
            self.client.send((result + '\n').encode())

            if jump_to == PlayerStatus.LOBBY:
                self.status = jump_to

    def ingame_console(self):
        pass
