import json
import random
import sys
import textwrap

from game.libraries import *

# Language interface file
engine = language["engine"]


SAVE_VERSION = 1


# DATA INTEGRITY VALIDATION ===================================================
# Missing structural data raises DataIntegrityError at load time. Missing
# optional flavor text degrades to engine defaults. Runtime player actions
# (moving into a wall, taking what is not there) always degrade to messages.

OBJECT_FIELDS = ("look", "touch", "use")
ROOM_FIELDS = ("title", "exits", "spawns")
MONSTER_FIELDS = ("ST", "DX", "IQ", "HT", "damage")
DIRECTIONS = ("north", "south", "east", "west")
INVERTED_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_language(data):
    """Validate rooms/objects/monsters/quests definitions.

    Raises DataIntegrityError listing every structural problem found.
    """
    errors = []

    if not isinstance(data, dict):
        raise DataIntegrityError("language data must be a JSON object")

    objects = data.get("objects", {})
    rooms = data.get("rooms")
    if not rooms:
        raise DataIntegrityError("language data must define at least one room")

    for obj_id, obj in objects.items():
        if not isinstance(obj, dict):
            errors.append('object "%s" must be an object' % obj_id)

    for room_id, room in rooms.items():
        if not isinstance(room, dict):
            errors.append('room "%s" must be an object' % room_id)
            continue
        for field in ROOM_FIELDS:
            if field not in room:
                errors.append('room "%s" is missing field "%s"' % (room_id, field))
        exits = room.get("exits", {})
        if exits is None or not isinstance(exits, dict):
            errors.append('room "%s" exits must be an object (use {} for a dead end)' % room_id)
        else:
            for direction, target in exits.items():
                if direction not in DIRECTIONS:
                    errors.append('room "%s" has invalid exit direction "%s"' % (room_id, direction))
                if target not in rooms:
                    errors.append(
                        'room "%s" exit "%s" points to undefined room "%s"'
                        % (room_id, direction, target)
                    )
        spawns = room.get("spawns", {})
        if spawns is None or not isinstance(spawns, dict):
            errors.append('room "%s" spawns must be an object' % room_id)
        else:
            for spawn, quantity in spawns.items():
                if spawn not in objects:
                    errors.append(
                        'room "%s" spawns undefined object "%s"' % (room_id, spawn)
                    )
                if not _is_int(quantity) or quantity < 1:
                    errors.append(
                        'room "%s" spawn quantity for "%s" must be a positive integer'
                        % (room_id, spawn)
                    )

    # Reciprocal exits: addArea links both ways, so contradictory data would
    # silently create passages the data does not declare.
    for room_id, room in rooms.items():
        exits = room.get("exits")
        if not isinstance(exits, dict):
            continue
        for direction, target in exits.items():
            if direction not in INVERTED_DIRECTIONS:
                continue
            if target not in rooms:
                continue
            back = INVERTED_DIRECTIONS[direction]
            other_exit = rooms[target].get("exits", {}).get(back)
            if other_exit is not None and other_exit != room_id:
                errors.append(
                    'exit mismatch: room "%s" %s -> "%s", but room "%s" %s -> "%s"'
                    % (room_id, direction, target, target, back, other_exit)
                )

    for monster_id, monster in data.get("monsters", {}).items():
        if not isinstance(monster, dict):
            errors.append('monster "%s" must be an object' % monster_id)
            continue
        for field in MONSTER_FIELDS:
            if field not in monster:
                errors.append(
                    'monster "%s" is missing required attribute "%s"'
                    % (monster_id, field)
                )
        if not _is_int(monster.get("ST", 0)) or monster.get("ST", 0) < 1:
            errors.append('monster "%s" ST must be a positive integer' % monster_id)
        if not _is_int(monster.get("DX", 0)) or monster.get("DX", 0) < 1:
            errors.append('monster "%s" DX must be a positive integer' % monster_id)
        if not _is_int(monster.get("IQ", 0)) or monster.get("IQ", 0) < 1:
            errors.append('monster "%s" IQ must be a positive integer' % monster_id)
        if not _is_int(monster.get("HT", 0)) or monster.get("HT", 0) < 1:
            errors.append('monster "%s" HT must be a positive integer' % monster_id)
        damage = monster.get("damage")
        if not _is_int(damage) or damage < 1:
            errors.append('monster "%s" damage must be a positive integer' % monster_id)

    for room_id, monsters in data.get("encounters", {}).items():
        if room_id not in rooms:
            errors.append('encounters reference undefined room "%s"' % room_id)
        if not isinstance(monsters, list):
            errors.append('encounters for room "%s" must be a list' % room_id)
            continue
        for monster_id in monsters:
            if monster_id not in data.get("monsters", {}):
                errors.append(
                    'room "%s" spawns undefined monster "%s"' % (room_id, monster_id)
                )

    for quest_id, quest in data.get("quests", {}).items():
        if not isinstance(quest, dict):
            errors.append('quest "%s" must be an object' % quest_id)
            continue
        for field in ("name", "target"):
            if field not in quest:
                errors.append('quest "%s" is missing field "%s"' % (quest_id, field))
        target = quest.get("target", {})
        if isinstance(target, dict):
            kind = target.get("type")
            if kind == "item":
                if target.get("id") not in objects:
                    errors.append(
                        'quest "%s" targets undefined object "%s"'
                        % (quest_id, target.get("id"))
                    )
                if not _is_int(target.get("count", 1)) or target.get("count", 1) < 1:
                    errors.append('quest "%s" target count must be a positive integer' % quest_id)
            elif kind not in ("item",):
                errors.append('quest "%s" has unknown target type "%s"' % (quest_id, kind))

    if errors:
        raise DataIntegrityError("invalid game data:\n - " + "\n - ".join(errors))

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
        self.HP = self.HT
    
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
# CLASS MONSTERS ===============================================================
class SudMonster:
    def __init__(self, monster_id, data):
        missing = [field for field in MONSTER_FIELDS if field not in data]
        if missing:
            # Bad monster attributes are a data error, never a silent zero.
            raise DataIntegrityError(
                'monster "%s" is missing required attribute(s): %s'
                % (monster_id, ", ".join(missing))
            )
        self.id = monster_id
        self.name = data.get("name", monster_id)
        self.ST = data["ST"]
        self.DX = data["DX"]
        self.IQ = data["IQ"]
        self.HT = data["HT"]
        self.damage = data["damage"]
        # Optional flavor: degrade to a plain sight message.
        self.sight = data.get("look", engine["monster_is_here"] % (self.name,))
        self.HP = self.HT
        self.alive = True

    def view(self):
        return self.sight.capitalize() + "\n"

    def to_dict(self):
        return {"id": self.id, "HP": self.HP, "alive": self.alive}


class SudArea:
    def __init__(self, sight):
        self.objects = {}
        self.monsters = []
        self.panorama = {}
        self.sight = sight
        self.id = None
        self.inverted_directions = {'north':'south', 'south':'north', 'east':'west', 'west':'east'}

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
            result = self.char.take(self.area.getObject(args))
        except AttributeError:
            return engine["cant_take"] + ' ' + args + '.\n'
        journal = getattr(self, "journal", None)
        if journal is not None:
            journal.update(self.char)
        return result
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
# CLASS COMBAT ================================================================
class CombatResult:
    def __init__(self, winner, rounds, log):
        self.winner = winner  # "player", "monster" or "draw"
        self.rounds = rounds
        self.log = log


def _roll_3d6(rng):
    return sum(rng.randint(1, 6) for _ in range(3))


def resolve_combat(char, monster, rng=None, max_rounds=100):
    """Resolve char vs monster with GURPS-style attack rolls.

    A 3d6 roll at or below DX hits; damage is applied to HP. First side
    whose HP drops to 0 or below loses. Pass a seeded random.Random for
    reproducible fights.
    """
    if rng is None:
        rng = random
    log = []
    player_hp = char.HP
    monster_hp = monster.HP
    rounds = 0

    while player_hp > 0 and monster_hp > 0 and rounds < max_rounds:
        rounds += 1

        if _roll_3d6(rng) <= char.DX:
            monster_hp -= char.ST // 2
            log.append("player hits %s" % monster.name)
        else:
            log.append("player misses %s" % monster.name)
        if monster_hp <= 0:
            break

        if _roll_3d6(rng) <= monster.DX:
            player_hp -= monster.damage
            log.append("%s hits" % monster.name)
        else:
            log.append("%s misses" % monster.name)

    if player_hp <= 0 and monster_hp <= 0:
        winner = "draw"
    elif monster_hp <= 0:
        winner = "player"
    elif player_hp <= 0:
        winner = "monster"
    else:
        winner = "draw"

    char.HP = player_hp
    monster.HP = monster_hp
    monster.alive = monster_hp > 0
    return CombatResult(winner, rounds, log)


# CLASS QUESTS ================================================================
class SudQuest:
    def __init__(self, quest_id, data):
        self.id = quest_id
        self.name = data["name"]
        self.target = data["target"]
        self.state = "active"

    def update(self, char):
        target = self.target
        if self.state == "active" and target.get("type") == "item":
            owned = char.inventory.get(target["id"], {}).get("quantity", 0)
            if owned >= target.get("count", 1):
                self.state = "done"
        return self.state

    def to_dict(self):
        return {"state": self.state}


class QuestJournal:
    def __init__(self, quest_data):
        self.quests = {qid: SudQuest(qid, q) for qid, q in quest_data.items()}

    def update(self, char):
        for quest in self.quests.values():
            quest.update(char)

    def get(self, quest_id):
        return self.quests.get(quest_id)

    def states(self):
        return {qid: quest.state for qid, quest in self.quests.items()}

    def restore_states(self, states):
        for quest_id, state in states.items():
            if state not in ("active", "done"):
                raise DataIntegrityError(
                    'quest "%s" has invalid saved state "%s"' % (quest_id, state)
                )
            if quest_id in self.quests:
                self.quests[quest_id].state = state


# WORLD BUILDER ===============================================================
def _plain_room_sight(room):
    title = span(room["title"], 'cyan', 'bold')
    exits = "".join((direction[0] + " ") for direction in room.get("exits", {}))
    desc = textwrap.fill(
        room.get("description", engine["no_description"]),
        80,
        replace_whitespace=False,
        initial_indent="    ",
    )
    return title + "\n" + "[ Exits: " + span(exits, 'yellow') + "]\n" + desc + "\n"


def build_world(data, player_name='Test Player Name', start_room=None):
    """Build a validated, fully wired game: rooms, objects, monsters, quests."""
    validate_language(data)

    objects_dic = {}
    for obj_id, obj in data["objects"].items():
        objects_dic[obj_id] = SudObject(
            obj_id,
            obj.get("look", engine["nothing_happens"]),
            obj.get("touch", engine["nothing_happens"]),
            obj.get("use", engine["unusable"]),
        )

    rooms_dic = {}
    for room_id, room in data["rooms"].items():
        area = SudArea(_plain_room_sight(room))
        area.id = room_id
        rooms_dic[room_id] = area

    for room_id, room in data["rooms"].items():
        for spawn, quantity in room.get("spawns", {}).items():
            for _ in range(int(quantity)):
                rooms_dic[room_id].addObject(objects_dic[spawn])

    for room_id, room in data["rooms"].items():
        for direction, target in room.get("exits", {}).items():
            rooms_dic[room_id].addArea(direction, rooms_dic[target])

    for room_id, monster_ids in data.get("encounters", {}).items():
        for monster_id in monster_ids:
            rooms_dic[room_id].monsters.append(
                SudMonster(monster_id, data["monsters"][monster_id])
            )

    char = SudPlayer(player_name)
    start_id = start_room or sorted(rooms_dic)[0]
    if start_id not in rooms_dic:
        raise DataIntegrityError('undefined start room "%s"' % start_id)
    game = SudGame(char, rooms_dic[start_id])
    game.rooms_by_id = rooms_dic
    game.objects_by_id = objects_dic
    game.monster_defs = data.get("monsters", {})
    game.journal = QuestJournal(data.get("quests", {}))
    game.cmd.journal = game.journal
    game.language_data = data
    return game


class SudGame:
    def __init__(self, char, area):
        self.cmd = SudCommand(char, area)
        self.FirstSight = area.view()
        self.rooms_by_id = None
        self.objects_by_id = {}
        self.monster_defs = {}
        self.journal = QuestJournal({})
        self.language_data = None
        self.cmd.journal = self.journal

    def to_dict(self):
        """Snapshot the mutable game state for saving.

        Room object quantities, monster HP/alive and quest states are part
        of the state; picking an item up must be reflected here.
        """
        area = self.cmd.area
        rooms_state = {}
        if self.rooms_by_id is not None:
            for room_id, room in self.rooms_by_id.items():
                rooms_state[room_id] = {
                    "objects": {
                        name: data["quantity"]
                        for name, data in room.objects.items()
                    },
                    "monsters": [monster.to_dict() for monster in room.monsters],
                }
        else:
            rooms_state[area.id] = {
                "objects": {
                    name: data["quantity"] for name, data in area.objects.items()
                },
                "monsters": [],
            }

        char = self.cmd.char
        return {
            "version": SAVE_VERSION,
            "current_room": area.id,
            "player": {
                "name": char.name,
                "ST": char.ST,
                "DX": char.DX,
                "IQ": char.IQ,
                "HT": char.HT,
                "HP": getattr(char, "HP", char.HT),
                "inventory": {
                    name: data["quantity"]
                    for name, data in char.inventory.items()
                },
            },
            "rooms": rooms_state,
            "quests": self.journal.states(),
        }

    def save(self, path):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, ensure_ascii=False, indent=2)
        return path

    @classmethod
    def load(cls, path, data=None):
        """Rebuild a validated world from data, then apply the save file.

        Corrupt or incompatible saves raise DataIntegrityError instead of
        silently producing a half-loaded game.
        """
        try:
            with open(path, encoding="utf-8") as file:
                saved = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise DataIntegrityError('cannot read save file "%s": %s' % (path, error))
        return cls.from_dict(saved, data=data)

    @classmethod
    def from_dict(cls, saved, data=None):
        if not isinstance(saved, dict):
            raise DataIntegrityError("save file must contain a JSON object")
        if saved.get("version") != SAVE_VERSION:
            raise DataIntegrityError(
                'unsupported save version "%s" (expected %d)'
                % (saved.get("version"), SAVE_VERSION)
            )
        errors = []
        if data is None:
            data = language

        player_data = saved.get("player")
        if not isinstance(player_data, dict):
            errors.append('save is missing "player"')
        room_id = saved.get("current_room")
        if room_id not in data.get("rooms", {}):
            errors.append('save points to undefined room "%s"' % room_id)
        rooms_state = saved.get("rooms")
        if not isinstance(rooms_state, dict):
            errors.append('save is missing "rooms" state')
        quests_state = saved.get("quests", {})
        if not isinstance(quests_state, dict):
            errors.append('save "quests" must be an object')
        inventory_state = player_data.get("inventory", {}) if isinstance(player_data, dict) else {}
        if not isinstance(inventory_state, dict):
            errors.append('player inventory must be an object')
        for name, quantity in inventory_state.items():
            if name not in data.get("objects", {}):
                errors.append('save inventory references undefined object "%s"' % name)
            if not _is_int(quantity) or quantity < 0:
                errors.append('saved quantity for "%s" must be a non-negative integer' % name)
        if isinstance(rooms_state, dict):
            for rid, state in rooms_state.items():
                if rid not in data.get("rooms", {}):
                    errors.append('save state references undefined room "%s"' % rid)
                if not isinstance(state, dict) or not isinstance(state.get("objects"), dict):
                    errors.append('room "%s" state must contain an "objects" map' % rid)
                    continue
                for name, quantity in state["objects"].items():
                    if name not in data.get("objects", {}):
                        errors.append(
                            'room "%s" state references undefined object "%s"' % (rid, name)
                        )
                    if not _is_int(quantity) or quantity < 0:
                        errors.append(
                            'room "%s" saved quantity for "%s" must be non-negative' % (rid, name)
                        )
        if errors:
            raise DataIntegrityError("invalid save data:\n - " + "\n - ".join(errors))

        game = build_world(data, player_name=player_data["name"], start_room=room_id)
        char = game.cmd.char

        for attr in ("ST", "DX", "IQ", "HT"):
            value = player_data.get(attr)
            if _is_int(value) and value >= 1:
                setattr(char, attr, value)
            else:
                errors.append('player "%s" must be a positive integer' % attr)
        hp = player_data.get("HP", char.HT)
        char.HP = hp if _is_int(hp) and hp >= 0 else char.HT

        for rid, area in game.rooms_by_id.items():
            area.objects = {}
            state = rooms_state.get(rid)
            for name, quantity in (state or {}).get("objects", {}).items():
                if quantity > 0:
                    area.objects[name] = {
                        "object": game.objects_by_id[name],
                        "quantity": quantity,
                    }
            monsters_state = {m["id"]: m for m in (state or {}).get("monsters", [])}
            for monster in area.monsters:
                snap = monsters_state.get(monster.id)
                if snap is not None:
                    monster.HP = snap.get("HP", monster.HP)
                    monster.alive = snap.get("alive", monster.alive)

        char.inventory = {}
        for name, quantity in inventory_state.items():
            if quantity > 0:
                char.inventory[name] = {
                    "object": game.objects_by_id[name],
                    "quantity": quantity,
                }

        if isinstance(quests_state, dict):
            game.journal.restore_states(quests_state)
        game.FirstSight = game.cmd.area.view()
        return game

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
