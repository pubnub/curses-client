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

HISTORY_WINDOW_LINES = 5
HISTORY_LINES = HISTORY_WINDOW_LINES + 3
HISTORY_Y = HEADER_LINES + SUB_LINES + PUB_LINES + PRESENCE_LINES + 2

LOG_QUEUE = Queue.Queue()
MSG_QUEUE = Queue.Queue()

KEY_ESC = 27
COLOR_DEFAULT = -1

class Window:
    def __init__(self, sc, offset, height, title=None):
        if title != None:
            sc.addstr(offset, 0, title, curses.color_pair(1))
            self.title = title

        self.cursor = 0
        self.messages = []
        self.win = None
        self.height = height
        self.draw(sc, offset, height)

    # Assign and draw the window + border
    def draw(self, sc, offset, height):
        maxy, maxx = sc.getmaxyx()

        if self.win is None:
            self.win = curses.newwin(height, maxx, offset + 1, 0)
        self.win.border()

        return self.win

    # Writes a new message and scrolls to the bottom of the log
    def write(self, message):
        self.messages.append(message)
        self.scroll(-999999) # Scroll back to top
        self.scroll(len(self.messages) - self.height + 2) # Scroll to bottom of messages
        self.draw_messages(self.cursor)

    # Draws the message log from a given starting cursor
    def draw_messages(self, cursor=0):
        self.cursor = cursor
        maxy, maxx = self.win.getmaxyx()
        num = cursor + maxy - 2
        messages = self.messages[cursor:num]

        self.win.erase()

        for i, message in enumerate(messages):
            filler = ' ' * (maxx - 2 - len(message))
            self.win.addstr(i + 1, 1, message + filler)

        self.refresh()

    # Scroll the text in a given direct i.e. scroll(1) or scroll(-1)
    def scroll(self, amount=0):
        self.cursor += amount
        if self.cursor < 0:
            self.cursor = 0

        if len(self.messages) < self.cursor:
            self.cursor = len(self.messages)

        self.draw_messages(self.cursor)

    def refresh(self):
        self.win.border()
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

    # Draw winows
    sub_win = Window(sc, HEADER_LINES + 1, SUB_WINDOW_LINES, "Messages:")
    presence_win = Window(sc, HEADER_LINES + SUB_LINES + PUB_LINES + 1, PRESENCE_LINES, "Presence:")
    history_win = Window(sc, HISTORY_Y, HISTORY_LINES, "History:")

    # Draw history controls
    sc.addstr(HISTORY_Y, 10, "Refresh", curses.color_pair(1))
    sc.addstr(HISTORY_Y, 18, "(h)", curses.color_pair(2))

    pub_win, pub_text = draw_pubbox(sc)

    # Setup stdscr
    sc.refresh()
    sub_win.refresh()
    pub_win.refresh()
    presence_win.refresh()
    history_win.refresh()

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

    history(origin, subkey, channel, history_win)

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

        elif cmd == ord('h'):
            history(origin, subkey, channel, history_win)

        elif cmd == curses.KEY_UP:
            sub_win.scroll(-1)

        elif cmd == curses.KEY_DOWN:
            sub_win.scroll(1)

def parse_logs(sc):
    global LOG_QUEUE

    while True:
        message = LOG_QUEUE.get()
        maxy, maxx = sc.getmaxyx()
        filler = ' ' * (maxx - 2 - len(message))
        sc.addstr(maxy - 1, 0, message + filler, curses.color_pair(4))
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

def history(origin, subkey, channel, win):
    timetoken = '0'
    response = None

    parts = urllib2.quote('/'.join([origin, 'v2', 'history', 'sub-key', subkey, 'channel', channel]))
    parts += '?stringtoken=true&count=100&reverse=false&pnsdk=PubNub-JS-Web%2F3.5.48'

    try:
        response = urllib2.urlopen('http://%s' % (parts), timeout=300).read()
    except urllib2.URLError:
        pass

    if response:
        messages = json.loads(response)

        for msg in map(json.dumps, messages[0]):
            win.write(msg)

def message_log(win):
    global MSG_QUEUE

    while True:
        message = MSG_QUEUE.get()
        win.write(message)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='PubNub Console')
    parser.add_argument('-p', '--pubkey', default='demo')
    parser.add_argument('-s', '--subkey', default='demo')
    parser.add_argument('-c', '--channel', default='my_channel')
    parser.add_argument('-o', '--origin', default='pubsub.pubnub.com')
    args = parser.parse_args()

    curses.wrapper(main, args.origin, args.pubkey, args.subkey, args.channel)

