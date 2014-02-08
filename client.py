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

LOG_WINDOW_LINES = 5
LOG_LINES = LOG_WINDOW_LINES + 3 # Window + headings + borders

MSG_QUEUE = Queue.Queue()
KEY_ESC = 27
COLOR_DEFAULT = -1
MSG_BUFFER = []
MSG_CURSOR = 0

def main(sc, origin, pubkey, subkey, channel):
    global MSG_CURSOR

    MAXY, MAXX = sc.getmaxyx()

    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, COLOR_DEFAULT)
    curses.init_pair(2, curses.COLOR_CYAN, COLOR_DEFAULT)
    curses.init_pair(3, curses.COLOR_YELLOW, COLOR_DEFAULT)

    draw_header(sc, origin, pubkey, subkey, channel)
    sub_win = draw_subbox(sc)
    log_win = draw_logbox(sc)
    pub_win, pub_text = draw_pubbox(sc)

    # Setup stdscr
    sc.refresh()
    log_win.refresh()
    sub_win.refresh()
    pub_win.refresh()

    logger = threading.Thread(target=message_log, args=(sub_win,))
    logger.daemon=True
    logger.start()

    subscriber = threading.Thread(target=subscribe, args=(origin, subkey, channel))
    subscriber.daemon=True
    subscriber.start()

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
            publish(origin, pubkey, subkey, channel, pub_text.edit(), log_win)

        elif cmd == ord('r'):
            publish(origin, pubkey, subkey, channel, pub_text.gather(), log_win)

        elif cmd == curses.KEY_UP:
            if len(MSG_BUFFER) <= SUB_MSGS: continue
            MSG_CURSOR = max(0, MSG_CURSOR - 1)
            draw_messages(sub_win, MSG_BUFFER[MSG_CURSOR:MSG_CURSOR+SUB_MSGS])

        elif cmd == curses.KEY_DOWN:
            if len(MSG_BUFFER) <= SUB_MSGS: continue
            MSG_CURSOR = max(len(MSG_BUFFER) - 1, MSG_CURSOR + 1)
            draw_messages(sub_win, MSG_BUFFER[MSG_CURSOR:MSG_CURSOR+SUB_MSGS])

        log_win.refresh()

def publish(origin, pubkey, subkey, channel, data, log_win):
    try:
        data = json.dumps(json.loads(data))
    except ValueError as e:
        # TODO: expose this in some way
        log_win.addstr("Incorrect JSON {0}".format('\n'))
        pass

    path = '/'.join([origin, 'publish', pubkey, subkey, '0', channel, '0', data])

    try:
        response = urllib2.urlopen('http://%s' % urllib2.quote(path)).read()
    except urllib2.URLError as e:
        log_win.addstr("Error publishing: {0} {1}".format(e.reason, '\n'))
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

def draw_logbox(sc, log_win=None):
    maxy, maxx = sc.getmaxyx()
    offset = HEADER_LINES + SUB_LINES + PUB_LINES + 1

    if log_win is None:
        log_win = curses.newwin(PUB_WINDOW_LINES, maxx-2, offset+2, 1)
    log_win.border()

    return log_win

def draw_subbox(sc):
    maxy, maxx = sc.getmaxyx()
    offset = HEADER_LINES + 1

    sc.addstr(offset, 0, "Messages:", curses.color_pair(1))
    win = curses.newwin(SUB_WINDOW_LINES, maxx, offset+1, 0)
    win.border()
    return win

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
    #tp = curses.textpad.Textbox(pub_win)

    return pub_win, tp

def draw_messages(win, messages):
    maxy, maxx = win.getmaxyx()

    for i, message in enumerate(messages):
        filler = ' ' * (maxx-2 - len(message))
        win.addstr(i+1, 1, message + filler)

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

