import collections
import curses
import curses.textpad
import json
import signal
import threading
import urllib2


HEADER_LINES = 3
SUB_WINDOW_LINES = 20
SUB_LINES = SUB_WINDOW_LINES + 3 # Window + headings + borders
SUB_MSGS = SUB_WINDOW_LINES - 2

PUB_WINDOW_LINES = 20
PUB_LINES = PUB_WINDOW_LINES + 3 # Window + headings + borders

STATUS_WINDOW_LINES = PUB_WINDOW_LINES + 2 # 2 columns tied to pubwindow
STATUS_LINES = PUB_LINES

COLOR_DEFAULT = -1
MSG_BUFFER = []

def main(sc, origin, pubkey, subkey, channel):
    MAXY, MAXX = sc.getmaxyx()

    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, COLOR_DEFAULT)
    curses.init_pair(2, curses.COLOR_CYAN, COLOR_DEFAULT)
    curses.init_pair(3, curses.COLOR_YELLOW, COLOR_DEFAULT)

    draw_header(sc, origin, pubkey, subkey, channel)
    sub_win = draw_subbox(sc)
    stat_win = draw_statusbox(sc)
    pub_win, pub_text = draw_pubbox(sc)

    sc.refresh()
    sub_win.refresh()
    pub_win.refresh()
    stat_win.refresh()

    subscriber = threading.Thread(
        target=subscribe, args=(sub_win, origin, subkey, channel))
    subscriber.daemon=True
    subscriber.start()

    while True:
        cmd = sc.getch()
        if cmd == ord('q'):
            break
        elif cmd == ord('p'):
            publish(origin, pubkey, subkey, channel, pub_text.edit())
        elif cmd == ord('r'):
            publish(origin, pubkey, subkey, channel, pub_text.gather())
        elif cmd == ord('f'):
            focus_messages(sc, sub_win)

def publish(origin, pubkey, subkey, channel, data):
    #TODO: validate
    data = json.dumps(json.loads(data))
    parts = urllib2.quote('/'.join([origin, 'publish', pubkey, subkey, '0', channel, '0', data]))
    response = urllib2.urlopen('http://%s' % parts).read()
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
        ('Repeat Publish: ', '(r)')
    ]

    offset = 0
    for legend in legends:
        key, value = legend
        value += '  '
        sc.addstr(2, offset, key, curses.color_pair(1))
        sc.addstr(2, offset + len(key), value, curses.color_pair(2))
        offset += (len(key) + len(value))

def draw_subbox(sc):
    maxy, maxx = sc.getmaxyx()
    offset = HEADER_LINES + 1

    sc.addstr(offset, 0, "Messages:", curses.color_pair(1))
    win = curses.newwin(SUB_WINDOW_LINES, maxx, offset+1, 0)
    win.border()
    return win

def draw_pubbox(sc):
    maxy, maxx = sc.getmaxyx()
    offset = HEADER_LINES + SUB_LINES + 1

    sc.addstr(offset, 0, "Publish Message (              ):", curses.color_pair(1))
    sc.addstr(offset, 17, "Ctrl-G to Send", curses.color_pair(2))
    curses.textpad.rectangle(sc, offset+1,0, offset+PUB_WINDOW_LINES+2, maxx/2-1)
    win = curses.newwin(PUB_WINDOW_LINES, maxx/2-2, offset+2, 1)
    tp = curses.textpad.Textbox(win)

    return win, tp

def draw_statusbox(sc):
    maxy, maxx = sc.getmaxyx()
    offset = HEADER_LINES + SUB_LINES + 1

    sc.addstr(offset, maxx/2+1, "Status:", curses.color_pair(1))
    win = curses.newwin(STATUS_WINDOW_LINES, maxx/2-1, offset+1, maxx/2+1)
    win.border()
    return win

def draw_messages(win, messages):
    maxy, maxx = win.getmaxyx()

    for i, message in enumerate(messages):
        filler = ' ' * (maxx-2 - len(message))
        win.addstr(i+1, 1, message + filler)

    win.refresh()

def scroll_messages(sc, win):
    slice_start = max(0, len(MSG_BUFFER) - SUB_MSGS - 1)

    while True:
        cmd = sc.getch()

        if cmd == ord('q'):
            break

        elif len(MSG_BUFFER) <= SUB_MSGS:
            continue

        elif cmd == curses.KEY_UP:
            slice_start = max(0, slice_start - 1)

        elif cmd == curses.KEY_DOWN:
            slice_start += max(len(MSG_BUFFER)-1, slice_start)

        draw_messages(win, MSG_BUFFER[slice_start:slice_start+SUB_MSGS])

def subscribe(win, origin, subkey, channel):
    global MSG_BUFFER

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

            MSG_BUFFER += map(json.dumps, messages)
            draw_messages(win, MSG_BUFFER[-SUB_MSGS:])

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='PubNub Console')
    parser.add_argument('-p', '--pubkey', default='demo')
    parser.add_argument('-s', '--subkey', default='demo')
    parser.add_argument('-c', '--channel', default='asdfasdf')
    parser.add_argument('-o', '--origin', default='pubsub.pubnub.com')
    args = parser.parse_args()

    curses.wrapper(main, args.origin, args.pubkey, args.subkey, args.channel)

