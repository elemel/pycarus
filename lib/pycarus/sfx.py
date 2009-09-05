import pyglet
import pyglet.media

wingflap = pyglet.media.StaticSource(pyglet.media.load('flap.wav'))
level_start = pyglet.media.StaticSource(pyglet.media.load('level_start.wav'))
level_win = pyglet.media.StaticSource(pyglet.media.load('level_win.wav'))

walk = pyglet.media.StaticSource(pyglet.media.load('step.wav'))
walk_player = pyglet.media.Player()
walk_player.queue(walk)

heart = pyglet.media.StaticSource(pyglet.media.load('heartbeat.wav'))
heart_player = pyglet.media.Player()
heart_player.queue(heart)

sizzle = pyglet.media.StaticSource(pyglet.media.load('sizzle.wav'))
sizzle_player = pyglet.media.Player()
sizzle_player.queue(sizzle)

wind = pyglet.media.StaticSource(pyglet.media.load('wind.wav'))
wind_player = pyglet.media.Player()
wind_player.queue(wind)



def flap():
	player = wingflap.play()
def start():
	player = level_start.play()
def win():
	player = level_win.play()

def walk():
	walk_player.eos_action = walk_player.EOS_LOOP
	walk_player.play()
def walk_stop():
	walk_player.eos_action = walk_player.EOS_PAUSE
def heartbeat():
	heart_player.eos_action = walk_player.EOS_LOOP
	heart_player.play()
def heartbeat_stop():
	heart_player.eos_action = walk_player.EOS_PAUSE
def sizzle():
	sizzle_player.eos_action = walk_player.EOS_LOOP
	sizzle_player.play()
def sizzle_stop():
	sizzle_player.eos_action = walk_player.EOS_PAUSE
def wind():
	wind_player.eos_action = walk_player.EOS_LOOP
	wind_player.play()
def wind_stop():
	wind_player.eos_action = walk_player.EOS_PAUSE
