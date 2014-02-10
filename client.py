import curses
import curses.textpad
import json
import Queue
import threading
import urllib2
import my_textbox

HEADER_LINES = 3
SUB_WINDOW_LINES = 20
SUB_LINES = SUB_WINDOW_LINES + 3 # Window + headings + borders
SUB_MSGS = SUB_WINDOW_LINES - 2

PUB_WINDOW_LINES = 10
PUB_LINES = PUB_WINDOW_LINES + 3 # Window + headings + borders

PRESENCE_WINDOW_LINES = 5
PRESENCE_LINES = PRESENCE_WINDOW_LINES + 3 # Window + headings + borders

LOG_QUEUE = Queue.Queue()
MSG_QUEUE = Queue.Queue()

KEY_ESC = 27
COLOR_DEFAULT = -1
MSG_BUFFER = []
MSG_CURSOR = 0

class Window:
    def __init__(self, sc, offset, height):
        self.win = None
        self.winY = 1
        self.draw(sc, offset, height)

    def draw(self, sc, offset, height):
        maxy, maxx = sc.getmaxyx()

        if self.win is None:
            self.win = curses.newwin(height, maxx, offset + 1, 0)
        self.win.border()

        return self.win

    def write(self, message):
        self.win.addstr(self.winY, 1, message)
        self.winY += 1
        self.refresh()

    def refresh(self):
        self.win.refresh()

def main(sc, origin, pubkey, subkey, channel):
    global MSG_CURSOR

    MAXY, MAXX = sc.getmaxyx()

    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, COLOR_DEFAULT)
    curses.init_pair(2, curses.COLOR_CYAN, COLOR_DEFAULT)
    curses.init_pair(3, curses.COLOR_YELLOW, COLOR_DEFAULT)
    curses.init_pair(4, curses.COLOR_MAGENTA, COLOR_DEFAULT)

    draw_header(sc, origin, pubkey, subkey, channel)

    sc.addstr(HEADER_LINES + 1, 0, "Messages:", curses.color_pair(1))
    sub_win = Window(sc, HEADER_LINES + 1, SUB_WINDOW_LINES)

    pub_win, pub_text = draw_pubbox(sc)

    sc.addstr(HEADER_LINES + SUB_LINES + PUB_LINES + 2, 0, "Presence:", curses.color_pair(1))
    presence_win = Window(sc, HEADER_LINES + SUB_LINES + PUB_LINES + 2, PRESENCE_LINES)

    # Setup stdscr
    sc.refresh()
    sub_win.refresh()
    pub_win.refresh()
    presence_win.refresh()

    logger = threading.Thread(target=message_log, args=(sub_win,))
    logger.daemon=True
    logger.start()

    log_parser = threading.Thread(target=parse_logs, args=(sc,))
    log_parser.daemon = True
    log_parser.start()

    subscriber = threading.Thread(target=subscribe, args=(origin, subkey, channel))
    subscriber.daemon=True
    subscriber.start()

    presence_thread = threading.Thread(target=presence, args=(origin, subkey, channel, presence_win))
    presence_thread.daemon = True
    presence_thread.start()

    while True:
        cmd = sc.getch()

        if cmd == ord('q'):
            break

        elif cmd == KEY_ESC:
            MSG_CURSOR = len(MSG_BUFFER) - SUB_MSGS - 1
            draw_messages(sub_win, MSG_BUFFER[MSG_CURSOR:MSG_CURSOR+SUB_MSGS])

        elif cmd == ord('p'):
            #TODO: redrawing all is overkill
            pub_win, pub_text = draw_pubbox(sc)
            publish(origin, pubkey, subkey, channel, pub_text.edit())

        elif cmd == ord('r'):
            publish(origin, pubkey, subkey, channel, pub_text.gather())

        elif cmd == curses.KEY_UP:
            if len(MSG_BUFFER) <= SUB_MSGS: continue
            MSG_CURSOR = max(0, MSG_CURSOR - 1)
            draw_messages(sub_win, MSG_BUFFER[MSG_CURSOR:MSG_CURSOR+SUB_MSGS])

        elif cmd == curses.KEY_DOWN:
            if len(MSG_BUFFER) <= SUB_MSGS: continue
            MSG_CURSOR = max(len(MSG_BUFFER) - 1, MSG_CURSOR + 1)
            draw_messages(sub_win, MSG_BUFFER[MSG_CURSOR:MSG_CURSOR+SUB_MSGS])

def parse_logs(sc):
    global LOG_QUEUE

    while True:
        message = LOG_QUEUE.get()
        maxy, maxx = sc.getmaxyx()
        sc.addstr(maxy - 1, 0, message, curses.color_pair(4))
        sc.refresh()

def log(message):
    global LOG_QUEUE

    LOG_QUEUE.put(message)

def publish(origin, pubkey, subkey, channel, data):
    try:
        data = json.dumps(json.loads(data))
    except ValueError as e:
        # TODO: expose this in some way
        log("Incorrect JSON")
        return False

    path = '/'.join([origin, 'publish', pubkey, subkey, '0', channel, '0', data])

    try:
        response = urllib2.urlopen('http://%s' % urllib2.quote(path)).read()
    except urllib2.URLError as e:
        log("Error publishing: {0}".format(e.reason))
        response = ""
        pass

    return response

def draw_colors(sc):
    colors = 16

    for i in range(colors):
        curses.init_pair(i+1, i, i)

    for i in range(colors):
        sc.addstr(i, 0, str(i))
        sc.addstr(i, 5, "X" * 20, curses.color_pair(i+1))

    sc.refresh()
    sc.getch()

def draw_header(sc, origin, pubkey, subkey, channel):
    maxy, maxx = sc.getmaxyx()

    headings = [
        ('Origin: ', origin),
        ('Publish Key: ', pubkey),
        ('Subscribe Key: ', subkey),
        ('Channel: ', channel)
    ]

    offset = 0
    for heading in headings:
        key, value = heading
        value += '  '
        sc.addstr(0, offset, key, curses.color_pair(1))
        sc.addstr(0, offset + len(key), value, curses.color_pair(2))
        offset += (len(key) + len(value))

    sc.attron(curses.color_pair(3))
    sc.hline(1, 0, curses.ACS_HLINE, maxx)
    sc.attroff(curses.color_pair(3))

    legends = [
        ('Compose Publish: ', '(p)'),
        ('Quit: ', '(q)'),
    ]

    offset = 0
    for legend in legends:
        key, value = legend
        value += '  '
        sc.addstr(2, offset, key, curses.color_pair(1))
        sc.addstr(2, offset + len(key), value, curses.color_pair(2))
        offset += (len(key) + len(value))

def draw_pubbox(sc, pub_win=None):
    maxy, maxx = sc.getmaxyx()
    offset = HEADER_LINES + SUB_LINES + 1

    if pub_win is None:
        # TODO: use draw_header
        sc.addstr(offset, 0, "Publish:          Re-Publish last", curses.color_pair(1))
        sc.addstr(offset, 9, "(Ctrl-G)", curses.color_pair(2))
        sc.addstr(offset, 34, "(r)", curses.color_pair(2))
        curses.textpad.rectangle(sc, offset+1,0, offset+PUB_WINDOW_LINES+2, maxx-1)
        pub_win = curses.newwin(PUB_WINDOW_LINES, maxx-2, offset+2, 1)

    tp = my_textbox.MyTextbox(pub_win)

    return pub_win, tp

def draw_messages(win, messages):
    maxy, maxx = win.win.getmaxyx()

    for i, message in enumerate(messages):
        filler = ' ' * (maxx-2 - len(message))
        win.win.addstr(i+1, 1, message + filler)

    win.refresh()

def subscribe(origin, subkey, channel):
    global MSG_QUEUE
    timetoken = '0'
    response = None

    parts = urllib2.quote('/'.join([origin, 'subscribe', subkey, channel,'0']))
    while True:
        try:
            response = urllib2.urlopen(
                'http://%s/%s' % (parts, timetoken), timeout=300).read()
        except urllib2.URLError:
            pass

        if response:
            messages, timetoken = json.loads(response)

        for msg in map(json.dumps, messages):
            MSG_QUEUE.put(msg)

def presence(origin, subkey, channel, win):
    global MSG_QUEUE
    timetoken = '0'
    response = None

    channel = channel + '-pnpres'

    parts = urllib2.quote('/'.join([origin, 'subscribe', subkey, channel,'0']))
    while True:
        try:
            response = urllib2.urlopen(
                'http://%s/%s' % (parts, timetoken), timeout=300).read()
        except urllib2.URLError:
            pass

        if response:
            messages, timetoken = json.loads(response)

        for msg in map(json.dumps, messages):
            win.write(msg)

def message_log(win):
    global MSG_BUFFER
    global MSG_CURSOR
    global MSG_QUEUE

    while True:
        message = MSG_QUEUE.get()
        if MSG_CURSOR == len(MSG_BUFFER) - SUB_MSGS - 1:
            MSG_CURSOR += 1
        MSG_BUFFER.append(message)
        draw_messages(win, MSG_BUFFER[MSG_CURSOR:MSG_CURSOR+SUB_MSGS])

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='PubNub Console')
    parser.add_argument('-p', '--pubkey', default='demo')
    parser.add_argument('-s', '--subkey', default='demo')
    parser.add_argument('-c', '--channel', default='my_channel')
    parser.add_argument('-o', '--origin', default='pubsub.pubnub.com')
    args = parser.parse_args()

    curses.wrapper(main, args.origin, args.pubkey, args.subkey, args.channel)

