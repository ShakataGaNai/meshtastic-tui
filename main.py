import curses
import meshtastic
from meshtastic.tcp_interface import TCPInterface
from meshtastic import mesh_pb2
import threading
import sys
from pprint import pprint
from pubsub import pub


# Initialize Meshtastic interface
interface = TCPInterface("localhost")

# Global variable to store messages
global messages
messages = []
messages.append(("SYSTEM","Startup!"))
users = {}
config = {}

#print(interface.localNode.localConfig);
#print(interface.localNode.moduleConfig);
#print(interface.getMyNodeInfo());
#print()
#print(meshtastic.config_pb2.Config.DeviceConfig.Role)

# nodes = interface.nodes
# for node in nodes.values():
#     #print(node)
#     usr = node["user"]
#     users[usr["id"]] = {"longName": usr.get("longName","UNK"), "shortName": usr.get("shortName","UNK")}
#sys.exit(1)


def getRole(val):
    for name, num in meshtastic.config_pb2.Config.DeviceConfig.Role.items():
        if num == val:
            return name
    return None

def getRegion(val):
    for name, num in meshtastic.config_pb2.Config.LoRaConfig.RegionCode.items():
        if num == val:
            return name
    return None

def getPreset(val):
    for name, num in meshtastic.config_pb2.Config.LoRaConfig.ModemPreset.items():
        if num == val:
            return name
    return None


# def receive_message(packet):
#     if "text" in packet["decoded"]["payload"]:
#         text = packet["decoded"]["payload"]["text"]
#         node = packet["fromId"]
#         messages.append((node, text))
#         users[node] = packet["from"]

# # Add receive_message callback
# interface.on_receive = receive_message

def initialize_config():
    global config
    lc = interface.localNode.localConfig
    lora = getattr(lc, "lora")
    meta = interface.localNode.getMetadata()
    nodeinfo = interface.getMyNodeInfo()
    config = {
        "Lora Region": getRegion(getattr(lora, "region")),
        "Modem Preset": getPreset(getattr(lora, "modem_preset")),
        "Max Hops": getattr(lora, "hop_limit"),
        "Role": getRole(interface.localNode.localConfig.device.role),
        "Long Name": interface.getLongName(),
        "Short Name": interface.getShortName()
    }

def initialize_users():
    global users
    nodes = interface.nodes
    for node in nodes.values():
        usr = node["user"]
        users[node["num"]] = {"longName": usr.get("longName","UNK"), "shortName": usr.get("shortName","UNK")}


def draw_chat_screen(stdscr, message):
    height, width = stdscr.getmaxyx()
    usr = 60

    # Define window for chat
    chat_win = curses.newwin(height - 3, width - usr, 0, 0)
    chat_win.scrollok(True)

    # Define window for users
    users_win = curses.newwin(height, usr, 0, width - usr)

    # Define window for input
    input_win = curses.newwin(3, width - usr, height - 3, 0)
    input_win.scrollok(True)
    input_win.idlok(True)

    chat_win.clear()
    chat_win.box()
    for i, (user, msg) in enumerate(messages[-(height-5):]):
        chat_win.addstr(i + 1, 1, f"{user}: {msg}")
    chat_win.refresh()

    users_win.clear()
    users_win.box()
    users_win.addstr(1, 1, "Users:")
    for i, (node, user) in enumerate(users.items()):
        try:
            users_win.addstr(i + 2, 1, f"{user['longName']} ({user['shortName']} - {node})")
        except:
            pass
    users_win.refresh()

    input_win.clear()
    input_win.box()
    input_win.addstr(1, 1, message)
    input_win.refresh()

def draw_config_screen(stdscr, selected_idx):
    height, width = stdscr.getmaxyx()

    config_win = curses.newwin(height, width, 0, 0)
    config_win.clear()
    config_win.box()

    config_win.addstr(1, 1, "Configuration", curses.A_BOLD | curses.A_UNDERLINE)
    for idx, (key, value) in enumerate(config.items()):
        if idx == selected_idx:
            config_win.addstr(idx + 3, 1, f"{key}: {value}", curses.A_REVERSE)
        else:
            config_win.addstr(idx + 3, 1, f"{key}: {value}")

    if selected_idx == len(config):
        config_win.addstr(len(config) + 4, 1, "Exit", curses.A_REVERSE)
    else:
        config_win.addstr(len(config) + 4, 1, "Exit")

    config_win.refresh()

def main(stdscr):
    curses.curs_set(0)
    #stdscr.clear()
    #stdscr.nodelay(True)
    stdscr.timeout(1000)

    message = ''
    screen = 'chat'
    selected_config_idx = 0

    initialize_config()
    initialize_users()

    while True:
        try:
            if screen == 'chat':
                draw_chat_screen(stdscr, message)

                try:
                    key = stdscr.getkey()
                except curses.error:
                    curses.napms(100)
                    continue

                if key == '\n':
                    # Send message via Meshtastic
                    interface.sendText(message)
                    messages.append((f"Me ({config['Short Name']})", message))
                    message = ''
                elif key == '\b' or key == '\x7f':
                    message = message[:-1]
                elif key == '\x0f':  # Ctrl+O
                    screen = 'config'
                elif key == '\x03':  # Ctrl+C
                    break
                else:
                    message += key

                curses.napms(100)

            elif screen == 'config':
                draw_config_screen(stdscr, selected_config_idx)

                try:
                    key = stdscr.getkey()
                except curses.error:
                    curses.napms(100)
                    continue

                if key == 'KEY_DOWN':
                    selected_config_idx = (selected_config_idx + 1) % (len(config) + 1)
                elif key == 'KEY_UP':
                    selected_config_idx = (selected_config_idx - 1) % (len(config) + 1)
                elif key == '\n':
                    if selected_config_idx == len(config):
                        screen = 'chat'
                        # Save the config settings to Meshtastic
                        # region = mesh_pb2.RegionCode.Value(config["Lora Region"])
                        # interface.localNode.localConfig.device.region = region
                        # preset = mesh_pb2.ModemPreset.Value(config["Modem Preset"])
                        # interface.localNode.localConfig.device.modem_preset = preset
                        # interface.localNode.localConfig.device.hop_limit = int(config["Max Hops"])
                        # interface.localNode.setOwner(long_name=config["Long Name"], short_name=config["Short Name"])
                        # interface.writeConfig()
                    else:
                        key = list(config.keys())[selected_config_idx]
                        # stdscr.addstr(height - 2, 1, f"Enter new value for {key}: ")
                        # curses.echo()
                        # new_value = stdscr.getstr(height - 2, len(f"Enter new value for {key}: ") + 1).decode('utf-8')
                        # config[key] = new_value
                        # curses.noecho()
        except KeyboardInterrupt:
            break

def onReceive(packet, interface):  # pylint: disable=unused-argument
    """called when a packet arrives"""
    #print(f"Received: {packet}")
    if packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
        hexId = packet['fromId']
        numId = packet['from']
        messages.append((users[numId]['longName'], packet['decoded']['text']))
    else:
        messages.append((users[numId]['longName'], f"==Packet==  {packet['decoded']['portnum']}"))

def onConnection(interface, topic=pub.AUTO_TOPIC):  # pylint: disable=unused-argument
    """called when we (re)connect to the radio"""
    messages.append(("SYSTEM", "Connected to radio!"))

if __name__ == "__main__":
    
    pub.subscribe(onConnection, "meshtastic.connection.established")
    pub.subscribe(onReceive, "meshtastic.receive")
    try:
        # Run the main function in a separate thread
        thread = threading.Thread(target=lambda: curses.wrapper(main))
        thread.start()
        thread.join()
    except KeyboardInterrupt:
        #interface.close()
        print("Exiting...")
        #sys.exit(1)
    finally:
        #interface.close()
        #print("Exiting...")
        sys.exit(1)
