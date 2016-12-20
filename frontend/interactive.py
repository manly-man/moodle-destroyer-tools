import curses
from curses.textpad import Textbox, rectangle
import asyncio
import readline
import rlcompleter



# import readline # optional, will allow Up/Down/History in the console
# import code
# vars = globals().copy()
# vars.update(locals())
# shell = code.InteractiveConsole(vars)
# shell.interact()


class CursesUi:
    def __init__(self):
        self.screen = curses.initscr()
        self.screen.clear()

    def __enter__(self):
        print('__enter__')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('__exit__')
        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()


def main(stdscr):
    stdscr.addstr(0, 0, "Enter IM message: (hit Ctrl-G to send)")

    editwin = curses.newwin(5,30, 2,1)
    rectangle(stdscr, 1,0, 1+5+1, 1+30+1)
    stdscr.refresh()

    box = Textbox(editwin, True)

    # Let the user edit until Ctrl-G is struck.
    box.edit()

    # Get resulting contents
    message = box.gather()


if __name__ == '__main__':
    curses.wrapper(main)


class MyCompleter(rlcompleter.Completer):
    def complete(self, text, state):
        print(text)
        print(state)
        if state == 2:
            return None
        return text+str(state)