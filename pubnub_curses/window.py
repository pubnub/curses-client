import curses
import json

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

    def clear(self):
        self.messages = []
        self.scroll(-999999)
        self.draw_messages()

    def refresh(self):
        self.win.border()
        self.win.refresh()