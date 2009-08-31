from __future__ import division

from Box2D import *
from feather import config
import pyglet
from pyglet.gl import *
import rabbyt
import sys

def clamp(x, min_x, max_x):
    return max(min_x, min(max_x, x))

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

class Sun(Actor):
    def __init__(self, game_screen, position=(0, 0)):
        self.game_screen = game_screen
        self.position = position

    def step(self, dt):
        segment = b2Segment()
        segment.p1 = self.position
        segment.p2 = self.game_screen.icarus.body.position
        _, _, shape = self.game_screen.world.RaycastOne(segment, True, None)
        if shape is not None and shape.GetBody().userData is self.game_screen.icarus:
            self.game_screen.icarus.heating = 1
        else:
            self.game_screen.icarus.heating = 0

class Icarus(Actor):
    def __init__(self, game_screen, position=(0, 0)):
        self.game_screen = game_screen
        self.init_body(position)
        self.init_sprite()
        self.keys = set()
        self.heating = 0
        self.temperature = 0
        self.damage = 0
        self.fatigue = 0
        self.state = 'flying'
        self.facing = 1

    def init_body(self, position):
        body_def = b2BodyDef()
        body_def.position = position
        self.body = self.game_screen.world.CreateBody(body_def)
        self.body.userData = self
        shape_def = b2CircleDef()
        shape_def.radius = 0.5
        shape_def.density = 1
        self.body.CreateShape(shape_def)
        self.body.SetMassFromShapes()

    def init_sprite(self):
        texture = pyglet.resource.texture('images/icarus.png')
        self.sprite = rabbyt.Sprite(texture, scale=0.02)

    def delete(self):
        self.game_screen.world.DestroyBody(self.body)

    def draw(self):
        self.sprite.xy = self.body.position.tuple()
        self.sprite.scale_x = self.facing * abs(self.sprite.scale_x)
        if self.state == 'falling':
            self.sprite.scale_y = -abs(self.sprite.scale_y)
        else:
            self.sprite.scale_y = abs(self.sprite.scale_y)

        # Fade to red as Icarus is heated by the sun, then fade to black as he
        # is burnt.
        damage_factor = 0.5 + 0.5 * clamp(1 - self.damage, 0, 1)
        temperature_factor = clamp(1 - self.temperature, 0, 1)
        self.sprite.red = damage_factor
        self.sprite.green = damage_factor * temperature_factor
        self.sprite.blue = damage_factor * temperature_factor

        self.sprite.render()

    def step(self, dt):
        if self.heating:
            self.temperature = (dt / config.heat_duration +
                                clamp(self.temperature, 0, 1))
            if self.temperature >= 1:
                self.damage = (dt / config.burn_duration +
                               clamp(self.damage, 0, 1))
        else:
            self.temperature = min(1, self.temperature)
            self.temperature = (clamp(self.temperature, 0, 1) -
                                dt / config.cool_duration)
        if self.damage >= 1 or self.fatigue >= 1:
            self.state = 'falling'
        if self.state == 'flying':
            self.step_flying(dt)

    def step_flying(self, dt):
        self.fatigue = dt / config.flight_duration + clamp(self.fatigue, 0, 1)
        up = pyglet.window.key.UP in self.keys
        left = pyglet.window.key.LEFT in self.keys
        right = pyglet.window.key.RIGHT in self.keys
        if left ^ right:
            self.facing = right - left
        lift_force = up * config.icarus_lift_force
        side_force = (right - left) * config.icarus_side_force
        left = pyglet.window.key.LEFT in self.keys
        right = pyglet.window.key.LEFT in self.keys
        air_force = -(self.body.linearVelocity * config.icarus_air_resistance)
        self.body.ApplyForce(b2Vec2(side_force, lift_force) + air_force,
                             self.body.position)

    def on_key_press(self, symbol, modifiers):
        self.keys.add(symbol)
    
    def on_key_release(self, symbol, modifiers):
        self.keys.discard(symbol)

class Cloud(Actor):
    def __init__(self, game_screen, position=(0, 0)):
        self.game_screen = game_screen
        self.init_body(position)
        self.init_sprite()

    def init_body(self, position):
        body_def = b2BodyDef()
        body_def.position = position
        self.body = self.game_screen.world.CreateBody(body_def)
        shape_def = b2PolygonDef()
        shape_def.SetAsBox(2, 0.5)
        # shape_def.density = 0.1
        self.body.CreateShape(shape_def)
        self.body.SetMassFromShapes()

    def init_sprite(self):
        texture = pyglet.resource.texture('images/cloud.png')
        self.sprite = rabbyt.Sprite(texture, scale=0.02)

    def delete(self):
        self.game_screen.world.DestroyBody(self.body)

    def draw(self):
        self.sprite.xy = self.body.position.tuple()
        self.sprite.render()

    def step(self, dt):
        anti_gravity_force = self.body.massData.mass * config.gravity
        self.body.ApplyForce((0, anti_gravity_force), self.body.position)

class GameScreen(Screen):
    def __init__(self, window):
        super(GameScreen, self).__init__(window)
        self.init_world()
        self.clock_display = pyglet.clock.ClockDisplay()
        self.icarus = Icarus(self)
        self.clouds = [Cloud(self, (-5, 3)), Cloud(self, (5, 4))]
        self.sun = Sun(self, (0, 20))
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
            self.icarus.step(self.dt)
            self.sun.step(self.dt)
            for cloud in self.clouds:
                cloud.step(self.dt)
            self.world.Step(self.dt, config.position_iterations,
                            config.velocity_iterations)

    def init_world(self):
        aabb = b2AABB()
        aabb.lowerBound = -100, -100
        aabb.upperBound = 100, 100
        self.world = b2World(aabb, (0, -config.gravity), True)

    def on_draw(self):
        red, green, blue = config.background_color
        glClearColor(red, green, blue, 0)
        self.window.clear()
        glPushMatrix()
        glTranslatef(self.window.width // 2, self.window.height // 2, 0)
        scale = self.window.height / 15
        glScalef(scale, scale, scale)
        self.icarus.draw()
        for cloud in self.clouds:
            cloud.draw()
        glPopMatrix()
        if config.fps:
            self.clock_display.draw()
        if self.icarus.fatigue >= 0.5:
            glBindTexture(GL_TEXTURE_2D, 0)
            glColor4f(0, 0, 0, clamp(self.icarus.fatigue, 0, 1) - 0.5)
            glBegin(GL_QUADS)
            glVertex2f(0, 0)
            glVertex2f(self.window.width, 0)
            glVertex2f(self.window.width, self.window.height)
            glVertex2f(0, self.window.height)
            glEnd()
        else:
            fatigue_factor = 1
        return pyglet.event.EVENT_HANDLED

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.delete()
        else:
            self.icarus.on_key_press(symbol, modifiers)
        return pyglet.event.EVENT_HANDLED

    def on_key_release(self, symbol, modifiers):
        self.icarus.on_key_release(symbol, modifiers)
        return pyglet.event.EVENT_HANDLED

def main():
    window = pyglet.window.Window(fullscreen=config.fullscreen)
    rabbyt.set_default_attribs()
    TitleScreen(window)
    pyglet.app.run()

if __name__ == '__main__':
    main()
