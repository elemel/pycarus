from __future__ import division

from Box2D import *
from feather import config
import pyglet
from pyglet.gl import *
import rabbyt
import sys

class Screen(object):
    def __init__(self, window):
        self.window = window
        self.window.push_handlers(self)

    def delete(self):
        self.window.pop_handlers()

class TitleScreen(Screen):
    def __init__(self, window):
        super(TitleScreen, self).__init__(window)
        texture = pyglet.resource.texture('images/title.jpg')
        self.sprite = rabbyt.Sprite(texture)

    def on_draw(self):
        self.window.clear()
        scale_x = self.window.width / self.sprite.texture.width
        scale_y = self.window.height / self.sprite.texture.height
        self.sprite.scale = max(scale_x, scale_y)
        self.sprite.x = self.window.width // 2
        self.sprite.y = self.window.height // 2
        self.sprite.render()
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.delete()
            self.window.close()
        if symbol == pyglet.window.key.ENTER:
            GameScreen(self.window)
        return pyglet.event.EVENT_HANDLED

class Actor(object):
    def step(self, dt):
        pass

    def draw(self):
        pass

class Icarus(Actor):
    def __init__(self, game_screen, position=(0, 0)):
        self.game_screen = game_screen
        self._init_body(position)
        self._init_sprite()
        self._keys = set()
        self._power = 1
        self._facing = 1

    def _init_body(self, position):
        body_def = b2BodyDef()
        body_def.position = position
        self.body = self.game_screen.world.CreateBody(body_def)
        shape_def = b2CircleDef()
        shape_def.radius = 0.5
        shape_def.density = 1
        self.body.CreateShape(shape_def)
        self.body.SetMassFromShapes()

    def _init_sprite(self):
        texture = pyglet.resource.texture('images/icarus.png')
        self.sprite = rabbyt.Sprite(texture, scale=0.02)

    def delete(self):
        self.game_screen.world.DestroyBody(self.body)

    def draw(self):
        self.sprite.xy = self.body.position.tuple()
        self.sprite.scale_x = self._facing * abs(self.sprite.scale_x)
        self.sprite.render()

    def step(self, dt):
        up = pyglet.window.key.UP in self._keys
        left = pyglet.window.key.LEFT in self._keys
        right = pyglet.window.key.RIGHT in self._keys
        if left ^ right:
            self._facing = right - left
        lift_force = up * self._power * config.icarus_lift_force
        side_force = (right - left) * config.icarus_side_force
        left = pyglet.window.key.LEFT in self._keys
        right = pyglet.window.key.LEFT in self._keys
        air_force = -(self.body.linearVelocity * config.icarus_air_resistance)
        self.body.ApplyForce(b2Vec2(side_force, lift_force) + air_force,
                             self.body.position)

    def on_key_press(self, symbol, modifiers):
        self._keys.add(symbol)
    
    def on_key_release(self, symbol, modifiers):
        self._keys.discard(symbol)

class Cloud(Actor):
    pass

class GameScreen(Screen):
    def __init__(self, window):
        super(GameScreen, self).__init__(window)
        self._init_world()
        self._clock_display = pyglet.clock.ClockDisplay()
        self._icarus = Icarus(self)
        self.time = 0
        self.dt = 1 / 60
        self.world_time = 0
        pyglet.clock.schedule_interval(self.step, self.dt)

    def delete(self):
        pyglet.clock.unschedule(self.step)
        super(GameScreen, self).delete()

    def step(self, dt):
        self.time += dt
        while self.world_time + self.dt <= self.time:
            self.world_time += self.dt
            self._icarus.step(self.dt)
            self.world.Step(self.dt, config.position_iterations,
                            config.velocity_iterations)

    def _init_world(self):
        aabb = b2AABB()
        aabb.lowerBound = -100, -100
        aabb.upperBound = 100, 100
        self.world = b2World(aabb, config.gravity, True)

    def on_draw(self):
        self.window.clear()
        glPushMatrix()
        glTranslatef(self.window.width // 2, self.window.height // 2, 0)
        scale = self.window.height / 10
        glScalef(scale, scale, scale)
        self._icarus.draw()
        glPopMatrix()
        if config.fps:
            self._clock_display.draw()
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.delete()
        else:
            self._icarus.on_key_press(symbol, modifiers)
        return pyglet.event.EVENT_HANDLED

    def on_key_release(self, symbol, modifiers):
        self._icarus.on_key_release(symbol, modifiers)
        return pyglet.event.EVENT_HANDLED

def main():
    window = pyglet.window.Window(fullscreen=config.fullscreen)
    rabbyt.set_default_attribs()
    TitleScreen(window)
    pyglet.app.run()

if __name__ == '__main__':
    main()
