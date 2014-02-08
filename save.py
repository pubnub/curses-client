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

PUB_WINDOW_LINES = 20
PUB_LINES = PUB_WINDOW_LINES + 3 # Window + headings + borders

STATUS_WINDOW_LINES = PUB_WINDOW_LINES + 2 # 2 columns tied to pubwindow
STATUS_LINES = PUB_LINES

SUB_SCROLLBACK = 100
COLOR_DEFAULT = -1

SUB_URL = 'http://pubsub.pubnub.com/subscribe/%s/%s/0/'
PUB_URL = 'http://pubsub.pubnub.com/publish/%s/%s/%s/%s/%s/%s'

def main(sc, origin, pubkey, subkey, channel):
    MAXY, MAXX = sc.getmaxyx()

    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, COLOR_DEFAULT)
    curses.init_pair(2, curses.COLOR_CYAN, COLOR_DEFAULT)
    curses.init_pair(3, curses.COLOR_YELLOW, COLOR_DEFAULT)

    draw_header(sc, origin, pubkey, subkey, channel)
    subbox = draw_subbox(sc)
    statsbox = draw_statusbox(sc)
    pubbox, pubtext = draw_pubbox(sc)

    sc.refresh()
    subbox.refresh()
    pubbox.refresh()
    statsbox.refresh()

    subscriber = threading.Thread(
        target=subscribe, args=(sc, subkey, channel, 4,4, 24, MAXX-8))
    subscriber.daemon=True
    subscriber.start()

    while True:
        cmd = sc.getch()
        if cmd == ord('q'):
            break
        elif cmd == ord('p'):
            publish(pubkey, subkey, channel, pubtext.edit())



    #pubtext.edit()
    sc.getch()
    #draw_pubbox(sc)
    #sc.getch()
    return

    """
    #draw_headings(sc, pubkey, subkey, channel)
    draw_sub(sc)
    sc.getch()
    return
    draw_pubbox(sc)
    #subscribe(sc, subkey, channel, 4,4, 24, MAXX-8)
    subscriber = threading.Thread(
        target=subscribe, args=(sc, subkey, channel, 4,4, 24, MAXX-8))
    subscriber.daemon=True
    subscriber.start()
    draw_pubbox(sc)

    while True:
        cmd = sc.getch()
        if cmd == ord('q'):
            break
        elif cmd == ord(':'):
            commands(sc)
    """

def publish(pubkey, subkey, channel, data):
    #TODO: validate
    data = json.loads(data)
    url = PUB_URL % (pubkey, subkey, '0', channel, '0', data)
    response = urllib2.urlopen(urllib2.quote(url)).read()
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
        ('Compose Publish: ', '(p)')
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

def subscribe(sc, win, subkey, channel, y, x, y2, x2):
    url = SUB_URL % (subkey, channel)

    timetoken = '0'
    response = None
    mbuff = collections.deque(maxlen=SUB_SCROLLBACK)

    while True:
        try:
            response = urllib2.urlopen(url+str(timetoken), timeout=300).read()
        except urllib2.URLError:
            pass

        if response:
            messages, timetoken = json.loads(response)
            for message in messages:
                mbuff.append(json.dumps(message))
            draw_subpad(pad, list(mbuff), y, x, y2, x2)
            pad.refresh(0,0, y,x, y2,x2)


def old_subscribe(sc, subkey, channel, y, x, y2, x2):
    url = SUB_URL % (subkey, channel)


    pad = curses.newpad(y2-y, x2-x)
    draw_subpad(pad, [], y, x, y2, x2)
    pad.refresh(0,0, y,x, y2,x2)

    timetoken = '0'
    response = None
    mbuff = collections.deque(maxlen=SUB_SCROLLBACK)

    while True:
        try:
            response = urllib2.urlopen(url+str(timetoken), timeout=300).read()
        except urllib2.URLError:
            pass

        if response:
            messages, timetoken = json.loads(response)
            for message in messages:
                mbuff.append(json.dumps(message))
            draw_subpad(pad, list(mbuff), y, x, y2, x2)
            pad.refresh(0,0, y,x, y2,x2)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='PubNub Console')
    parser.add_argument('-p', '--pubkey', default='demo')
    parser.add_argument('-s', '--subkey', default='demo')
    parser.add_argument('-c', '--channel', default='my_channel')
    parser.add_argument('-o', '--origin', default='pubsub.pubnub.com')
    args = parser.parse_args()

    curses.wrapper(main, args.origin, args.pubkey, args.subkey, args.channel)

