from __future__ import division

import pyglet
import sys

class MyWindow(pyglet.window.Window):
    def __init__(self, **kwargs):
        super(MyWindow, self).__init__(**kwargs)
        TitleScreen(self)

class Screen(object):
    def __init__(self, window):
        self.window = window
        self.window.push_handlers(self)

    def delete(self):
        self.window.pop_handlers()

class TitleScreen(Screen):
    def __init__(self, window):
        super(TitleScreen, self).__init__(window)
        self.image = pyglet.resource.image('images/title.jpg')
        self.image.anchor_x = self.image.width // 2
        self.image.anchor_y = self.image.height // 2
        self.sprite = pyglet.sprite.Sprite(self.image)

    def delete(self):
        self.sprite.delete()
        super(TitleScreen, self).delete()

    def on_draw(self):
        self.window.clear()
        self.sprite.scale = max(self.window.width / self.image.width,
                                self.window.height / self.image.height)
        self.sprite.x = self.window.width // 2
        self.sprite.y = self.window.height // 2
        self.sprite.draw()
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.delete()
            self.window.close()
        if symbol == pyglet.window.key.ENTER:
            GameScreen(self.window)
        return pyglet.event.EVENT_HANDLED

class GameScreen(Screen):
    def __init__(self, window):
        super(GameScreen, self).__init__(window)

    def on_draw(self):
        self.window.clear()
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.delete()
        return pyglet.event.EVENT_HANDLED

def main():
    fullscreen = '--windowed' not in sys.argv
    window = MyWindow(fullscreen=fullscreen)
    pyglet.app.run()

if __name__ == '__main__':
    main()
