from __future__ import division

from Box2D import *
from feather import config
from math import *
import pyglet
from pyglet.gl import *
import rabbyt
import sys

def save_screenshot(name='screenshot.png', format='RGB'):
    image = pyglet.image.get_buffer_manager().get_color_buffer().image_data
    image.format = format
    image.save(name)

def clamp(x, min_x, max_x):
    return max(min_x, min(max_x, x))

def normalize_signed_angle(angle):
    while angle < -pi:
        angle += 2 * pi
    while angle >= pi:
        angle -= 2 * pi
    return angle

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
        flying_texture = pyglet.resource.texture('images/icarus-flying.png')
        self.flying_sprite = rabbyt.Sprite(flying_texture, scale=0.02)
        walking_texture = pyglet.resource.texture('images/icarus-walking.png')
        self.walking_sprite = rabbyt.Sprite(walking_texture, scale=0.03)
        self.sprite = self.flying_sprite

    def delete(self):
        self.game_screen.world.DestroyBody(self.body)

    def draw(self):
        if self.state == 'walking':
            self.sprite = self.walking_sprite
        else:
            self.sprite = self.flying_sprite
        self.sprite.xy = self.body.position.tuple()
        self.sprite.rot = self.body.angle * 180 / pi
        self.sprite.scale_x = self.facing * abs(self.sprite.scale_x)
        self.sprite.green = 1 - clamp(self.damage, 0, 1)
        self.sprite.blue = 1 - clamp(self.damage, 0, 1)
        self.sprite.render()

    def step(self, dt):
        self.step_heating(dt)
        self.update_state()
        if self.state == 'walking':
            self.step_walking(dt)
        elif self.state == 'flying':
            self.step_flying(dt)
        elif self.state == 'falling':
            self.step_falling(dt)

    def update_state(self):
        if self.damage >= 1 or self.fatigue >= 1:
            self.state = 'falling'
        elif pyglet.window.key.UP in self.keys:
            self.state = 'flying'
        else:
            # See if there's any ground beneath Icarus's feet.
            segment = b2Segment()
            segment.p1 = self.body.position
            segment.p2 = segment.p1 + b2Vec2(0, -1)
            _, _, shape = self.game_screen.world.RaycastOne(segment, False,
                                                            None)
            if shape is not None:
                self.state = 'walking'
            else:
                self.state = 'flying'


    def step_heating(self, dt):
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

    def step_walking(self, dt):
        self.fatigue = clamp(self.fatigue, 0, 1) - dt / config.rest_duration
        left = pyglet.window.key.LEFT in self.keys
        right = pyglet.window.key.RIGHT in self.keys
        if left ^ right:
            self.facing = right - left
        force = b2Vec2(right - left, 0) * 10 - self.body.linearVelocity
        self.body.ApplyForce(force, self.body.position)
        torque = -(self.body.angle * config.icarus_angular_k +
                   self.body.angularVelocity * config.icarus_angular_damping)
        self.body.ApplyTorque(torque)

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
        torque = -(self.body.angle * config.icarus_angular_k +
                   self.body.angularVelocity * config.icarus_angular_damping)
        self.body.ApplyTorque(torque)

    def step_falling(self, dt):
        angle_error = normalize_signed_angle(pi - self.body.angle)
        torque = (angle_error * config.icarus_angular_k -
                  self.body.angularVelocity * config.icarus_angular_damping)
        self.body.ApplyTorque(torque)

    def on_key_press(self, symbol, modifiers):
        self.keys.add(symbol)
    
    def on_key_release(self, symbol, modifiers):
        self.keys.discard(symbol)

class Cloud(Actor):
    def __init__(self, game_screen, position=(0, 0), width=5):
        self.game_screen = game_screen
        self.width = width
        self.init_body(position)
        self.init_sprite()

    def init_body(self, position):
        body_def = b2BodyDef()
        body_def.position = position
        self.body = self.game_screen.world.CreateBody(body_def)
        shape_def = b2PolygonDef()
        shape_def.SetAsBox(self.width / 2, config.cloud_height / 2)
        self.body.CreateShape(shape_def)
        self.body.SetMassFromShapes()

    def init_sprite(self):
        texture = pyglet.resource.texture('images/cloud.png')
        self.sprite = rabbyt.Sprite(texture, scale=0.02)
        self.sprite.alpha = 0.8

    def delete(self):
        self.game_screen.world.DestroyBody(self.body)

    def draw_shadow(self):
        sun_position = b2Vec2(self.game_screen.sun.position)
        cloud_position = self.body.position
        top_left = cloud_position - b2Vec2(self.width / 2, 0)
        top_right = cloud_position + b2Vec2(self.width / 2, 0)
        left_slope = top_left - sun_position
        right_slope = top_right - sun_position
        bottom_left = top_left + left_slope * 1000
        bottom_right = top_right + right_slope * 1000
        glBindTexture(GL_TEXTURE_2D, 0)
        glColor3f(*config.shadow_color)
        glBegin(GL_QUADS)
        glVertex2f(top_left.x, top_left.y)
        glVertex2f(top_right.x, top_right.y)
        glVertex2f(bottom_right.x, bottom_right.y)
        glVertex2f(bottom_left.x, bottom_left.y)
        glEnd()

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
        self.clouds = [Cloud(self, (-3, 3)), Cloud(self, (8, 4)),
                       Cloud(self, (-4, 10))]
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
        red, green, blue = config.sky_color
        glClearColor(red, green, blue, 0)
        self.window.clear()
        glPushMatrix()
        glTranslatef(self.window.width // 2, self.window.height // 2, 0)
        scale = self.window.height / 15
        glScalef(scale, scale, scale)
        x, y = self.icarus.body.position.tuple()
        y += config.camera_dy
        glTranslatef(-x, -y, 0)
        for cloud in self.clouds:
            cloud.draw_shadow()
        self.icarus.draw()
        for cloud in self.clouds:
            cloud.draw()
        glPopMatrix()
        self.draw_temperature()
        if config.fps:
            self.clock_display.draw()
        return pyglet.event.EVENT_HANDLED

    def draw_temperature(self):
        glBindTexture(GL_TEXTURE_2D, 0)
        glBegin(GL_QUADS)
        glColor4f(0, 0, 0, 0)
        glVertex2f(0, 0)
        glVertex2f(self.window.width, 0)
        glColor4f(1, 1, 0, 0.5 * clamp(self.icarus.temperature, 0, 1))
        glVertex2f(self.window.width, self.window.height)
        glVertex2f(0, self.window.height)
        glEnd()

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.delete()
        elif symbol == pyglet.window.key.F12:
            save_screenshot('feather-screenshot.png')
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
