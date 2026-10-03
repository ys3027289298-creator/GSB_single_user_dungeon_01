import json
import random
import sys

from game.libraries import *

# Language interface file
engine = language["engine"]


# CLASS OBJECTS ================================================================
class SudObject:
    def __init__(self, name, sight, collide = engine["nothing_happens"], usability = engine["unusable"]):
        self.name = name
        self.sight = sight.capitalize()
        self.collide = collide.capitalize()
        self.usability = usability.capitalize()

    def view(self):
        return self.sight + "\n"

    def touch(self):
        return self.collide + "\n"

    def use(self):
        return self.usability + "\n"


# CLASS PLAYER =================================================================
class SudPlayer:
    def __init__(self, name):
        self.inventory = {}
        self.name = name
        self.ST = 10
        self.DX = 10
        self.IQ = 10
        self.HT = 10
        self.hp = self.HT
        self.quests = {}
    
    def drop(self, name):
        if name in self.inventory:
            if self.inventory[name]["quantity"] > 1:
                self.inventory[name]["quantity"] -= 1
                return self.inventory[name]["object"]
            else:
                return self.inventory.pop(name)["object"]

    def move(self, area):
        clear()
        return area.view()

    def say(self, what):
        return engine["you_says"] % (what) + '\n'

    def status(self, args):
        status = engine["char_sheet"] % (self.name, self.ST, self.DX, self.IQ, self.HT)
        return status

    @property
    def is_alive(self):
        return self.hp > 0

    @property
    def attack_power(self):
        return self.ST // 2

    @property
    def defense(self):
        return self.DX // 3

    def start_quest(self, quest_id):
        self.quests[quest_id] = {"state": "active", "progress": 0}

    def update_quests_on_kill(self, monster_id, quests_data):
        completed = []
        for quest_id, quest_def in quests_data.items():
            state = self.quests.get(quest_id)
            if state and state["state"] == "active" and quest_def["target"] == monster_id:
                state["progress"] += 1
                if state["progress"] >= int(quest_def["count"]):
                    state["state"] = "completed"
                    completed.append(quest_id)
        return completed

    def take(self, obj):
        if obj.name in self.inventory:
            self.inventory[obj.name]["quantity"] += 1
        else:
            self.inventory[obj.name] = {"object": obj, "quantity": 1}
        return engine["placed_inventory"] % (obj.name) + "\n"

    def touch(self, name):
        if name in self.inventory:
            return self.inventory[name]["object"].touch()

    def use(self, what):
        if what in self.inventory:
            return self.inventory[what]["object"].use()
        else:
            return engine["you_not_have"] % (what) + '\n'


# CLASS AREA ===================================================================
class SudArea:
    def __init__(self, sight):
        self.objects = {}
        self.monsters = {}
        self.panorama = {}
        self.sight = sight
        self.inverted_directions = {'north':'south', 'south':'north', 'east':'west', 'west':'east'}

    def addMonster(self, monster):
        self.monsters[monster.id] = monster

    def getMonster(self, monster_id):
        return self.monsters.get(monster_id)

    def removeMonster(self, monster_id):
        return self.monsters.pop(monster_id, None)

    def addArea(self, direction, area):
        area.panorama[self.inverted_directions[direction]] = self
        self.panorama[direction] = area

    def relocate(self, args):
        return self.panorama.get(args, None)

    def addObject(self, obj):
        if obj is not None:
            if obj.name in self.objects:
                self.objects[obj.name]["quantity"] += 1
            else:
                self.objects[obj.name] = {"object": obj, "quantity": 1}
            return engine["item_was_dropped"] % (obj.name) + "\n"

    def getObject(self, name):
        if name in self.objects:
            if self.objects[name]["quantity"] > 1:
                self.objects[name]["quantity"] -= 1
                return self.objects[name]["object"]
            else:
                return self.objects.pop(name)["object"]
        else:
            return engine["there_isnt_around"] % (name) + "\n"

    def touchObject(self, name):
        if name in self.objects:
            return self.objects[name]["object"].touch()
        else:
            return engine["there_isnt_around"] % (name) + "\n"

    def view(self, args='around'):
        if args and args != 'around':
            if args in self.panorama:
                return self.panorama[args].view()
            elif args in self.objects:
                return self.objects[args]["object"].view()
            else:
                return engine["there_isnt_around"] % (args) + "\n"
        else:
            if not self.objects:
                return self.sight

            objects_list = []
            for name, data in sorted(self.objects.items()):
                qty = data["quantity"]
                if qty > 1:
                    item_desc = f"{name} ({qty})"
                else:
                    item_desc = name

                article = engine["an_item_is_here"] if item_desc[0].lower() in 'aeiou' else engine["a_item_is_here"]
                objects_list.append(article % item_desc)

            obsight = span('\n' + '\n'.join(objects_list), 'yellow')
            return self.sight + obsight


# CLASS COMMANDS ===============================================================
class SudCommand:
    __doc__ = "\n " + engine["available_commands"] + "\n"
    
    def __init__(self, char, area):
        self.char = char
        self.area = area

        # Map aliases to real methods
        self.aliases = {
            'd': self.drop,
            'x': self.exit,
            'quit': self.exit,
            'q': self.exit,
            'g': self.get,
            'h': self.help,
            'i': self.inventory,
            'l': self.look,
            'n': lambda args: self.move('north'),
            's': lambda args: self.move('south'),
            'e': lambda args: self.move('east'),
            'w': lambda args: self.move('west'),
            'y': self.say,
            'st': self.status,
            't': self.touch,
            'u': self.use
        }

    def __getattr__(self, name):
        if name in self.aliases:
            return self.aliases[name]
        raise AttributeError(f"'SudCommand' object has no attribute '{name}'")

    def drop(self, args):
        return self.area.addObject(self.char.drop(args))
    drop.__doc__ = "\n " + engine["drop"] + "\n"

    def exit(self, args):
        print(span("\n " + engine["bye"]  + "\n", 'magenta'))
        sys.exit()
    exit.__doc__ = "\n " + engine["exit"] + "\n"

    def get(self, args):
        try:
            return self.char.take(self.area.getObject(args))
        except AttributeError:
            return engine["cant_take"] + ' ' + args + '.\n'
    get.__doc__ = "\n " + engine["get"] + "\n"

    def help(self, args):
        if args == '':
            return self.__doc__
        else:
            try:
                return getattr(self, args).__doc__
            except AttributeError:
                return span(engine["help_topic_not_found"], 'red') + "\n\n " + engine["available_commands"] + "\n"
    help.__doc__ = "\n " + engine["help"] + "\n"

    def inventory(self, args):
        if self.char.inventory:
            inv_list = [f"{name} ({data['quantity']})" if data["quantity"] > 1 else name 
                        for name, data in self.char.inventory.items()]
            return engine["your_inventory"] + ':\n - ' + '\n - '.join(inv_list) + '\n'
        else:
            return engine["inventory_empty"] + "\n"
    inventory.__doc__ = "\n " + engine["inventory"] + "\n"

    def look(self, args):
        if args == "":
            clear()
        return self.area.view(args)
    look.__doc__ = "\n " + engine["look"] + "\n"

    def move(self, args):
        area = self.area.relocate(args)
        if area is not None:
            self.area = area
            return self.char.move(self.area)
        else:
            return engine["nothing_that_way"] + "\n"
    move.__doc__ = "\n " + engine["move"] + "\n"

    def say(self, args):
        return self.char.say(args)
    say.__doc__ = "\n " + engine["say"] + "\n"

    def status(self, args):
        return self.char.status(args)
    status.__doc__ = "\n " + engine["status"] + "\n"

    def touch(self, args):
        if args in self.char.inventory:
            return self.char.touch(args)
        else:
            return self.area.touchObject(args)
    touch.__doc__ = "\n " + engine["touch"] + "\n"

    def use(self, args):
        return self.char.use(args)
    use.__doc__ = "\n " + engine["use"] + "\n"


# CLASS GAME ===================================================================
class SudGame:
    def __init__(self, char, area):
        self.cmd = SudCommand(char, area)
        self.FirstSight = area.view()

    def run(self):
        print(self.FirstSight)
        while True:
            try:
                command = input('> ');
            except EOFError:
                print()
                sys.exit()
            self.parse(command)

    def parse(self, command):
        comm = command.lower().split(' ')
        
        try:
            cmd = comm[0]
        except IndexError:
            cmd = 'help'
        
        try:
            args = comm[1:]
        except IndexError:
            args = []
        
        try:
            result = getattr(self.cmd, cmd)(' '.join(args).strip())
        except AttributeError:
            result = span(engine["unknown_command"], 'red') + "\n\n " + engine["available_commands"] + "\n"
        
        print(result)


# CLASS MONSTER ================================================================
class SudMonster:
    def __init__(self, monster_id, data):
        self.id = monster_id
        self.name = data["name"]
        self.look = data.get("look", "")
        self.max_hp = int(data["hp"])
        self.hp = self.max_hp
        self.attack = int(data["attack"])
        self.defense = int(data["defense"])

    @property
    def is_alive(self):
        return self.hp > 0


# COMBAT =======================================================================
def resolve_combat(player, monster, quests=None, rng=None):
    rng = rng if rng is not None else random.Random()
    rounds = 0
    log = []
    while player.is_alive and monster.is_alive:
        rounds += 1
        damage = max(1, player.attack_power - monster.defense) + rng.randint(0, 2)
        monster.hp = max(0, monster.hp - damage)
        log.append(("player", damage, monster.hp))
        if not monster.is_alive:
            break
        damage = max(1, monster.attack - player.defense) + rng.randint(0, 2)
        player.hp = max(0, player.hp - damage)
        log.append(("monster", damage, player.hp))

    result = {
        "winner": "player" if player.is_alive else "monster",
        "rounds": rounds,
        "log": log,
        "completed_quests": [],
    }
    if not monster.is_alive and quests:
        result["completed_quests"] = player.update_quests_on_kill(monster.id, quests)
    return result


# WORLD BUILDING ===============================================================
REQUIRED_ROOM_FIELDS = ("title", "description", "exits", "spawns")
REQUIRED_MONSTER_FIELDS = ("name", "hp", "attack", "defense")
REQUIRED_QUEST_FIELDS = ("name", "description", "target", "count")
VALID_DIRECTIONS = frozenset(("north", "south", "east", "west"))


def validate_world_data(language):
    rooms = language.get("rooms", {})
    objects = language.get("objects", {})
    monsters = language.get("monsters", {})
    quests = language.get("quests", {})

    for room_id, room in rooms.items():
        for field in REQUIRED_ROOM_FIELDS:
            if field not in room:
                raise WorldDataError(
                    f"Room '{room_id}' is missing required field '{field}'."
                )
        for direction, target in room["exits"].items():
            if direction not in VALID_DIRECTIONS:
                raise WorldDataError(
                    f"Room '{room_id}' has unknown exit direction '{direction}'."
                )
            if target not in rooms:
                raise WorldDataError(
                    f"Room '{room_id}' exit '{direction}' points to undefined"
                    f" room '{target}'."
                )
        for object_id in room["spawns"]:
            if object_id not in objects:
                raise WorldDataError(
                    f"Room '{room_id}' spawns undefined object '{object_id}'."
                )
        for monster_id in room.get("monsters", {}):
            if monster_id not in monsters:
                raise WorldDataError(
                    f"Room '{room_id}' spawns undefined monster '{monster_id}'."
                )

    for monster_id, monster in monsters.items():
        for field in REQUIRED_MONSTER_FIELDS:
            if field not in monster:
                raise WorldDataError(
                    f"Monster '{monster_id}' is missing required field '{field}'."
                )
        if int(monster["hp"]) <= 0:
            raise WorldDataError(f"Monster '{monster_id}' must have positive hp.")
        if int(monster["attack"]) < 0 or int(monster["defense"]) < 0:
            raise WorldDataError(
                f"Monster '{monster_id}' attack/defense must be >= 0."
            )

    for quest_id, quest in quests.items():
        for field in REQUIRED_QUEST_FIELDS:
            if field not in quest:
                raise WorldDataError(
                    f"Quest '{quest_id}' is missing required field '{field}'."
                )
        if quest["target"] not in monsters:
            raise WorldDataError(
                f"Quest '{quest_id}' targets undefined monster '{quest['target']}'."
            )
        if int(quest["count"]) < 1:
            raise WorldDataError(f"Quest '{quest_id}' count must be >= 1.")


def build_world(language):
    validate_world_data(language)

    objects_dic = {}
    for i in language["objects"]:
        objects_dic[i] = SudObject(
            i,
            language["objects"][i]["look"],
            language["objects"][i]["touch"],
            language["objects"][i]["use"]
        )

    rooms_dic = {}
    for i in language["rooms"]:
        room = language["rooms"][i]
        sight = room["title"] + "\n" + room["description"]
        rooms_dic[i] = SudArea(sight)

    for room in language["rooms"]:
        for spawn, quantity in language["rooms"][room]["spawns"].items():
            for _ in range(int(quantity)):
                rooms_dic[room].addObject(objects_dic[spawn])
        for monster_id, quantity in language["rooms"][room].get("monsters", {}).items():
            for _ in range(int(quantity)):
                rooms_dic[room].addMonster(SudMonster(monster_id, language["monsters"][monster_id]))

    for room in rooms_dic:
        exits = language["rooms"][room]["exits"]
        for direction in exits:
            rooms_dic[room].addArea(direction, rooms_dic[exits[direction]])

    return objects_dic, rooms_dic


# SAVE / LOAD ==================================================================
class SaveGameError(Exception):
    pass


SAVE_VERSION = 1


def save_game(player, current_room_id, rooms_dic, path):
    data = {
        "version": SAVE_VERSION,
        "current_room": current_room_id,
        "player": {
            "name": player.name,
            "ST": player.ST,
            "DX": player.DX,
            "IQ": player.IQ,
            "HT": player.HT,
            "hp": player.hp,
            "inventory": {
                name: entry["quantity"]
                for name, entry in player.inventory.items()
            },
            "quests": player.quests,
        },
        "rooms": {
            room_id: {
                "objects": {
                    name: entry["quantity"]
                    for name, entry in room.objects.items()
                },
                "monsters": {
                    monster_id: monster.hp
                    for monster_id, monster in room.monsters.items()
                },
            }
            for room_id, room in rooms_dic.items()
        },
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_game(path, language):
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise SaveGameError(f"Save file '{path}' is corrupted: {exc}") from exc

    try:
        version = data["version"]
        current_room_id = data["current_room"]
        player_data = data["player"]
        rooms_data = data["rooms"]
    except (KeyError, TypeError) as exc:
        raise SaveGameError(
            f"Save file '{path}' is missing required data: {exc}"
        ) from exc

    if version != SAVE_VERSION:
        raise SaveGameError(
            f"Save file version {version} is not supported"
            f" (expected {SAVE_VERSION})."
        )

    objects_dic, rooms_dic = build_world(language)

    if current_room_id not in rooms_dic:
        raise SaveGameError(
            f"Save file references unknown room '{current_room_id}'."
        )

    if not isinstance(player_data, dict) or "name" not in player_data:
        raise SaveGameError(f"Save file '{path}' has no valid player data.")

    player = SudPlayer(player_data["name"])
    for stat in ("ST", "DX", "IQ", "HT"):
        setattr(player, stat, int(player_data.get(stat, getattr(player, stat))))
    player.hp = int(player_data.get("hp", player.HT))

    for name, quantity in player_data.get("inventory", {}).items():
        if name not in objects_dic:
            raise SaveGameError(f"Save file references unknown object '{name}'.")
        player.inventory[name] = {
            "object": objects_dic[name],
            "quantity": int(quantity),
        }

    quests_data = language.get("quests", {})
    for quest_id, state in player_data.get("quests", {}).items():
        if quest_id not in quests_data:
            raise SaveGameError(f"Save file references unknown quest '{quest_id}'.")
        if state.get("state") not in ("active", "completed"):
            raise SaveGameError(
                f"Save file has invalid state for quest '{quest_id}'."
            )
        player.quests[quest_id] = {
            "state": state["state"],
            "progress": int(state.get("progress", 0)),
        }

    for room_id, room_state in rooms_data.items():
        if room_id not in rooms_dic:
            raise SaveGameError(f"Save file references unknown room '{room_id}'.")
        room = rooms_dic[room_id]

        objects = {}
        for name, quantity in room_state.get("objects", {}).items():
            if name not in objects_dic:
                raise SaveGameError(
                    f"Save file references unknown object '{name}'."
                )
            objects[name] = {"object": objects_dic[name], "quantity": int(quantity)}
        room.objects = objects

        monsters = {}
        for monster_id, hp in room_state.get("monsters", {}).items():
            monster = room.monsters.get(monster_id)
            if monster is None:
                raise SaveGameError(
                    f"Save file references unknown monster '{monster_id}'"
                    f" in room '{room_id}'."
                )
            monster.hp = int(hp)
            monsters[monster_id] = monster
        room.monsters = monsters

    return player, current_room_id, rooms_dic
