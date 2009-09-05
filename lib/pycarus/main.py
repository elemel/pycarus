from __future__ import division

from math import *
from pycarus import b2
from pycarus import config
from pycarus import sfx
import pyglet
from pyglet.gl import *
import rabbyt
import random
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

class Icarus(Actor):
    def __init__(self, game_screen, position=(0, 0)):
        self.game_screen = game_screen
        self.init_body(position)
        self.init_sprite()
        self.keys = set()
        self.sun_distance = 1000
        self.cloud_distance = 1000
        
        self.damage = 0
        self.fatigue = 0
        self.state = 'flying'
        self.facing = 1
        self.immortal = config.immortal
        self.melting = False
        self.flapped = False

    def init_body(self, position):
        body_def = b2.b2BodyDef()
        body_def.position = position
        self.body = self.game_screen.world.CreateBody(body_def)
        self.body.userData = self
        shape_def = b2.b2CircleDef()
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
        if self.state in ('standing', 'walking'):
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
        old_state = self.state
        if self.cloud_distance > config.shadow_length and not self.immortal:
            if not self.melting:
                self.melting = True
                sfx.sizzle()
            self.damage = (dt / self.sun_distance / config.melt_duration +
                           clamp(self.damage, 0, 1))
        else:
            if self.melting:
                self.melting = False
                sfx.sizzle_stop()
        self.update_distances()
        self.update_state()
        if self.state == 'standing':
            self.step_standing(dt)
        elif self.state == 'walking':
            self.step_walking(dt)
        elif self.state == 'flying':
            self.step_flying(dt)
        elif self.state == 'falling':
            self.step_falling(dt)
        if self.state != old_state:
            self.update_sound(old_state)
        if self.state == 'flying' and not self.flapped:
            sfx.flap()
            self.flapped = True
            pyglet.clock.schedule_once(self.clear_flapped, 1)

    def clear_flapped(self, dt):
        self.flapped = False

    def update_sound(self, old_state):
        if old_state == 'walking':
            sfx.walk_stop()
        if self.state == 'walking':
            sfx.walk()

    def update_distances(self):
        self.update_sun_distance()
        self.update_cloud_distance()

    def update_sun_distance(self):
        sun_position = b2.b2Vec2(*self.game_screen.sun.position)
        self.sun_distance = (self.body.position - sun_position).Length()

    def update_cloud_distance(self):
        segment = b2.b2Segment()
        segment.p1 = self.body.position
        segment.p2 = self.game_screen.sun.position
        _, _, shape = self.game_screen.world.RaycastOne(segment, False, None)
        if shape is not None and isinstance(shape.GetBody().userData, Cloud):
            cloud_position = shape.GetBody().position
            self.cloud_distance = (self.body.position -
                                   cloud_position).Length()
        else:
            self.cloud_distance = 1000

    def update_state(self):
        if (not self.immortal and (self.damage >= 1 or self.fatigue >= 1) or
            self.body.position.y <= 0):
            self.state = 'falling'
        elif pyglet.window.key.UP in self.keys:
            self.state = 'flying'
        else:
            # See if there's any ground beneath Icarus's feet.
            segment = b2.b2Segment()
            segment.p1 = self.body.position
            segment.p2 = segment.p1 + b2.b2Vec2(0, -0.6)
            _, _, shape = self.game_screen.world.RaycastOne(segment, False,
                                                            None)
            if shape is not None and not shape.isSensor:
                if self.state not in ('standing', 'walking'):
                    self.state = 'standing'
            else:
                self.state = 'flying'

    def step_standing(self, dt):
        # Rest on the ground.
        self.fatigue = clamp(self.fatigue, 0, 1) - dt / config.rest_duration
        left = pyglet.window.key.LEFT in self.keys
        right = pyglet.window.key.RIGHT in self.keys
        if left or right:
            self.state = 'walking'
        force = -self.body.linearVelocity
        self.body.ApplyForce(force, self.body.position)
        torque = -(self.body.angle * config.icarus_angular_k +
                   self.body.angularVelocity * config.icarus_angular_damping)
        self.body.ApplyTorque(torque)

    def step_walking(self, dt):
        left = pyglet.window.key.LEFT in self.keys
        right = pyglet.window.key.RIGHT in self.keys
        if not left and not right:
            self.state = 'standing'
            return
        if left ^ right:
            self.facing = right - left
        force = b2.b2Vec2(right - left, 0) * 10 - self.body.linearVelocity
        self.body.ApplyForce(force, self.body.position)
        torque = -(self.body.angle * config.icarus_angular_k +
                   self.body.angularVelocity * config.icarus_angular_damping)
        self.body.ApplyTorque(torque)

    def step_flying(self, dt):
        up = pyglet.window.key.UP in self.keys
        left = pyglet.window.key.LEFT in self.keys
        right = pyglet.window.key.RIGHT in self.keys
        if up or left or right:
            # Grow tired from flapping those wings.
            self.fatigue = (dt / config.flight_duration +
                            clamp(self.fatigue, 0, 1))
        if left ^ right:
            self.facing = right - left

        # Fatigue and damage affect flight capabilities.
        fatigue_factor = 1 - 2 * clamp(self.fatigue - 0.5, 0, 0.5)
        damage_factor = 1 - 2 * clamp(self.damage - 0.5, 0, 0.5)
        lift_force = up * fatigue_factor * damage_factor * config.icarus_lift_force

        side_force = (right - left) * config.icarus_side_force
        left = pyglet.window.key.LEFT in self.keys
        right = pyglet.window.key.LEFT in self.keys
        air_force = -(self.body.linearVelocity * config.icarus_air_resistance)
        self.body.ApplyForce(b2.b2Vec2(side_force, lift_force) + air_force,
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
    def __init__(self, game_screen, position=(0, 0), linear_velocity=(0, 0),
                 sensor=True, static=False):
        self.game_screen = game_screen
        self.width = 4.5
        self.init_body(position, linear_velocity, sensor, static)
        self.init_sprite()

    def init_body(self, position, linear_velocity, sensor, static):
        body_def = b2.b2BodyDef()
        body_def.position = position
        self.body = self.game_screen.world.CreateBody(body_def)
        self.body.userData = self
        shape_def = b2.b2PolygonDef()
        shape_def.SetAsBox(self.width / 2, config.cloud_height / 2)
        shape_def.isSensor = sensor
        shape_def.density = 1
        self.body.CreateShape(shape_def)
        if static:
            self.mass = 0
        else:
            self.body.SetMassFromShapes()
            self.mass = self.body.massData.mass
            self.body.linearVelocity = linear_velocity

    def init_sprite(self):
        texture = pyglet.resource.texture('images/cloud.png')
        self.sprite = rabbyt.Sprite(texture, scale=0.02)

    def delete(self):
        self.game_screen.world.DestroyBody(self.body)

    def draw_shadow(self):
        sun_position = b2.b2Vec2(*self.game_screen.sun.position)
        cloud_position = self.body.position
        top_left = cloud_position - b2.b2Vec2(self.width / 2, 0)
        top_right = cloud_position + b2.b2Vec2(self.width / 2, 0)
        left_slope = top_left - sun_position
        left_slope.Normalize()
        right_slope = top_right - sun_position
        right_slope.Normalize()
        bottom_left = top_left + left_slope * config.shadow_length
        bottom_right = top_right + right_slope * config.shadow_length
        glBindTexture(GL_TEXTURE_2D, 0)
        glBegin(GL_QUADS)
        red, green, blue = config.shadow_color
        glColor4f(red, green, blue, 1)
        glVertex2f(top_left.x, top_left.y)
        glVertex2f(top_right.x, top_right.y)
        glColor4f(red, green, blue, 0)
        glVertex2f(bottom_right.x, bottom_right.y)
        glVertex2f(bottom_left.x, bottom_left.y)
        glEnd()

    def draw(self):
        self.sprite.xy = self.body.position.tuple()
        self.sprite.render()

    def step(self, dt):
        anti_gravity_force = self.mass * config.gravity
        self.body.ApplyForce((0, anti_gravity_force), self.body.position)
        linear_velocity = self.body.linearVelocity
        linear_velocity.y = 0
        self.body.linearVelocity = linear_velocity

class Island(Actor):
    def __init__(self, game_screen, position=(0, 0)):
        self.game_screen = game_screen
        self.init_body(position)
        self.init_sprite()

    def init_body(self, position):
        body_def = b2.b2BodyDef()
        body_def.position = position
        self.body = self.game_screen.world.CreateBody(body_def)
        shape_def = b2.b2PolygonDef()
        shape_def.SetAsBox(3.5, 1)
        self.body.CreateShape(shape_def)

    def init_sprite(self):
        texture = pyglet.resource.texture('images/island.png')
        self.sprite = rabbyt.Sprite(texture, scale=0.02)

    def delete(self):
        self.game_screen.world.DestroyBody(self.body)

    def draw(self):
        self.sprite.xy = (self.body.position +
                          b2.b2Vec2(*config.island_offset)).tuple()
        self.sprite.render()

class GameScreen(Screen):
    def __init__(self, window):
        super(GameScreen, self).__init__(window)
        self.clock_display = pyglet.clock.ClockDisplay()

        self.init_time()

        self.clouds = []
        self.temples = []
        self.init_world()
        self.init_level()
        self.init_fade()
        self.icarus = Icarus(self, (2, 1.5))

        self.respawning = False
        self.winning = False
        pyglet.clock.schedule_interval(self.step, self.dt)
        sfx.wind()
        sfx.start()

    def delete(self):
        sfx.pause_all()
        pyglet.clock.unschedule(self.step)
        pyglet.clock.unschedule(self.respawn)
        super(GameScreen, self).delete()

    def init_time(self):
        self.time = 0
        self.dt = 1 / 60
        self.world_time = 0

    def init_fade(self):
        self.fade_tone = 0
        self.fade_alpha = 1
        self.fade_delta_tone = 0
        self.fade_delta_alpha = 0
        self.fade(tone=0, alpha=0)

    def init_level(self):
        self.sun = Sun(self, (0, 100))
        self.clouds.append(Cloud(self, (5, 95), static=True))
        self.pearly_gates_position = (10, 90)
        self.create_pearly_gates(self.pearly_gates_position)
        self.create_temple((-10, 80))
        self.create_temple((-15, 70))
        self.create_temple((10, 60))
        self.create_temple((-20, 50))
        self.create_temple((25, 40))
        self.create_temple((15, 30))
        self.create_temple((5, 20))
        self.create_temple((-10, 10))
        self.clouds.append(Cloud(self, (1.5, 8), static=True))
        self.island = Island(self)
        self.create_clouds(init=True)

    def create_temple(self, position):
        texture = pyglet.resource.texture('images/temple.png')
        temple = rabbyt.Sprite(texture=texture, scale=0.02,
                               xy=position)
        self.temples.append(temple)
        x, y = position
        self.clouds.append(Cloud(self, (x, y - 1.5), sensor=False,
                                 static=True))

    def create_pearly_gates(self, position):
        texture = pyglet.resource.texture('images/temple.png')
        self.pearly_gates = rabbyt.Sprite(texture=texture, scale=0.02,
                                          xy=position, rgb=(1, 1, 0))
        x, y = position
        self.clouds.append(Cloud(self, (x, y - 1.5), sensor=False,
                                 static=True))

    def step(self, dt):
        self.time += dt
        if self.icarus.state == 'falling' and not self.respawning:
            self.respawning = True
            pyglet.clock.schedule_once(self.respawn,
                                       config.fade_alpha_duration)
            self.fade(tone=0, alpha=1)
        if (self.icarus.state == 'standing' and not self.winning
            and abs(self.icarus.body.position.y -
                    self.pearly_gates_position[1]) < 2):
            self.winning = True
            pyglet.clock.schedule_once(self.win,
                                       config.fade_alpha_duration)
            self.fade(tone=1, alpha=1)
            sfx.win()
        self.step_fade(self.dt)
        while self.world_time + self.dt <= self.time:
            self.world_time += self.dt
            self.icarus.step(self.dt)
            self.sun.step(self.dt)
            for cloud in self.clouds:
                cloud.step(self.dt)
            self.step_clouds(dt)
            self.world.Step(self.dt, config.position_iterations,
                            config.velocity_iterations)

    def respawn(self, dt):
        self.respawning = False
        self.icarus.delete()
        self.icarus = Icarus(self, (2, 1.5))
        self.fade(tone=0, alpha=0)
        sfx.start()

    def win(self, dt):
        self.delete()

    def step_clouds(self, dt):
        self.delete_clouds()
        self.create_clouds()

    def delete_clouds(self):
        clouds = [c for c in self.clouds
                  if abs(c.body.position.x) > config.cloud_max_x]
        for cloud in clouds:
            self.clouds.remove(cloud)
            cloud.delete()

    def create_clouds(self, init=False):
        while len(self.clouds) < config.cloud_count:
            side = random.choice([-1, 1])
            if init:
                x = random.uniform(-config.cloud_max_x, config.cloud_max_x)
            else:
                x = config.cloud_max_x * side
            y = random.uniform(config.cloud_min_y, config.cloud_max_y)
            dx = -side * random.uniform(config.cloud_min_dx,
                                        config.cloud_max_dx)
            cloud = Cloud(self, position=(x, y), linear_velocity=(dx, 0))
            self.clouds.append(cloud)

    def step_fade(self, dt):
        self.fade_tone = clamp(self.fade_tone, 0, 1)
        self.fade_alpha = clamp(self.fade_alpha, 0, 1)
        self.fade_tone += self.fade_delta_tone * dt
        self.fade_alpha += self.fade_delta_alpha * dt

    def init_world(self):
        aabb = b2.b2AABB()
        aabb.lowerBound = -100, -10
        aabb.upperBound = 100, 100
        self.world = b2.b2World(aabb, (0, -config.gravity), True)

    def on_draw(self):
        red, green, blue = config.sky_color
        glClearColor(red, green, blue, 0)
        self.window.clear()
        glPushMatrix()
        glTranslatef(self.window.width // 2, self.window.height // 2, 0)
        scale = self.window.height / 15
        glScalef(scale, scale, scale)
        camera_position = (self.icarus.body.position +
                           b2.b2Vec2(*config.camera_offset))
        camera_position.y = clamp(camera_position.y, config.camera_min_y,
                                  config.camera_max_y)
        glTranslatef(-camera_position.x, -camera_position.y, 0)
        for cloud in self.clouds:
            cloud.draw_shadow()
        self.draw_sea()
        self.island.draw()
        self.pearly_gates.render()
        rabbyt.render_unsorted(self.temples)
        self.icarus.draw()
        for cloud in self.clouds:
            cloud.draw()
        glPopMatrix()
        self.draw_fade()
        if config.fps:
            self.clock_display.draw()
        return pyglet.event.EVENT_HANDLED

    def draw_sea(self):
        glBindTexture(GL_TEXTURE_2D, 0)
        glColor3f(*config.sea_color)
        glBegin(GL_QUADS)
        glVertex2f(-1000, 1.5)
        glVertex2f(1000, 1.5)
        glVertex2f(1000, -1000)
        glVertex2f(-1000, -1000)
        glEnd()

    def fade(self, tone, alpha):
        if self.fade_alpha <= 0:
            self.fade_tone = tone
            self.fade_delta_tone = 0
        else:
            self.fade_delta_tone = (2 if tone else -2) / config.fade_tone_duration
        self.fade_delta_alpha = (2 if alpha else -2) / config.fade_alpha_duration

    def draw_fade(self):
        if self.fade_alpha > 0:
            glBindTexture(GL_TEXTURE_2D, 0)
            glColor4f(self.fade_tone, self.fade_tone, self.fade_tone,
                      self.fade_alpha)
            glBegin(GL_QUADS)
            glVertex2f(0, 0)
            glVertex2f(self.window.width, 0)
            glVertex2f(self.window.width, self.window.height)
            glVertex2f(0, self.window.height)
            glEnd()

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.delete()
        elif symbol == pyglet.window.key.F12:
            save_screenshot('pycarus-screenshot.png')
        else:
            self.icarus.on_key_press(symbol, modifiers)
        return pyglet.event.EVENT_HANDLED

    def on_key_release(self, symbol, modifiers):
        self.icarus.on_key_release(symbol, modifiers)
        return pyglet.event.EVENT_HANDLED

def main():
    window = pyglet.window.Window(fullscreen=config.fullscreen)
    window.set_exclusive_mouse(config.fullscreen)
    window.set_exclusive_keyboard(config.fullscreen)
    rabbyt.set_default_attribs()
    pyglet.resource.path = ['@pycarus']
    TitleScreen(window)
    pyglet.app.run()

if __name__ == '__main__':
    main()
