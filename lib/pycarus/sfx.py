import pyglet
import pyglet.media

wingflap = pyglet.media.StaticSource(pyglet.resource.media('sounds/flap.wav'))
level_start = pyglet.media.StaticSource(pyglet.resource.media('sounds/level_start.wav'))
level_win = pyglet.media.StaticSource(pyglet.resource.media('sounds/level_win.wav'))

walk_sound = pyglet.media.StaticSource(pyglet.resource.media('sounds/step.wav'))
walk_player = pyglet.media.Player()
walk_player.queue(walk_sound)
walk_player.volume = 0.5

heart = pyglet.media.StaticSource(pyglet.resource.media('sounds/heartbeat.wav'))
heart_player = pyglet.media.Player()
heart_player.queue(heart)

sizzle_sound = pyglet.media.StaticSource(pyglet.resource.media('sounds/sizzle.wav'))
sizzle_player = pyglet.media.Player()
sizzle_player.queue(sizzle_sound)
sizzle_player.volume = 0.3

wind = pyglet.media.StaticSource(pyglet.resource.media('sounds/wind.wav'))
wind_player = pyglet.media.Player()
wind_player.queue(wind)wind_player.volume = 0.5

players = []

def flap():
	player = wingflap.play()
	players.append(player)
def start():
	player = level_start.play()
	players.append(player)
def win():
	player = level_win.play()
	players.append(player)

def walk():
    walk_player.eos_action = walk_player.EOS_LOOP
    walk_player.play()
    walk_player.seek(0)
def walk_stop():
    walk_player.pause()
def heartbeat():
    heart_player.eos_action = walk_player.EOS_LOOP
    heart_player.play()
    heart_player.seek(0)
def heartbeat_stop():
    heart_player.pause()
def sizzle():
    sizzle_player.eos_action = walk_player.EOS_LOOP
    sizzle_player.play()
    sizzle_player.seek(0)
def sizzle_stop():
    sizzle_player.pause()
def wind():
    wind_player.eos_action = walk_player.EOS_LOOP
    wind_player.play()
    wind_player.seek(0)
def wind_stop():
    wind_player.pause()

def pause_all():
    walk_player.pause()
    heart_player.pause()
    sizzle_player.pause()
    wind_player.pause()
    for player in players:
        player.pause()
