#!/usr/bin/env python3
"""
Big Bad Wolf eyes: two screens, one eye each.

Each screen is the white of the eye; a cartoon amber iris wanders around it,
blinks, and every so often the wolf goes into a mood (angry, sly, sleepy...)
with a matching sound.

    python3 wolf_eyes.py                 # auto: two screens on the Pi, preview window elsewhere
    python3 wolf_eyes.py --mode preview  # both eyes side by side in a window (for testing on a laptop)
    python3 wolf_eyes.py --swap          # eyes on the wrong screens? swap them

Keys:  1-9 trigger a mood   0 back to normal   b blink   s random sound
       m mute/unmute        q or Esc quit
"""
import argparse
import glob
import math
import os
import random
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
import pygame.gfxdraw

HERE = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(HERE, "sounds")

# --------------------------------------------------------------------------
# Settings you might want to tweak
# --------------------------------------------------------------------------
FPS = 30
IDLE_SECONDS = (10, 20)        # normal wandering between moods
FIRST_MOOD_AFTER = (6, 10)     # first mood after startup
BLINK_EVERY = (2.5, 6.0)       # seconds between blinks
DOUBLE_BLINK_CHANCE = 0.2
AMBIENT_SOUND_EVERY = (25, 45) # random sniff/growl while just wandering
AMBIENT_SOUNDS = "sniff/*|growl/*|voice/hungry*|voice/big_bad_wolf*|voice/come_closer*"
VOLUME = 1.0

# Look (cartoon wolf). Sizes are fractions of the screen height so any resolution works.
WHITE = (255, 255, 255)
IRIS_OUTER = (205, 104, 8)
IRIS_INNER = (255, 212, 52)
IRIS_STREAK = (176, 82, 6)
IRIS_RING = (72, 36, 8)
PUPIL = (14, 11, 10)
LID = (112, 114, 130)          # wolf-grey fur
LID_EDGE = (34, 32, 42)
IRIS_SIZE = 0.36               # iris radius / screen height
PUPIL_SIZE = 0.44              # pupil radius / iris radius
LID_EDGE_WIDTH = 0.028         # dark line along the lid / screen height
MEET_Y = 0.60                  # where the lids meet when closed (fraction of height)
FORESHORTEN = 0.16             # iris squashes a little when looking to the side

# Default eye shape. Moods override some of these.
#   u / l      upper / lower lid closed amount (0 = out of sight, 1 = shut)
#   tilt       + = inner corners down (angry), - = inner corners up (worried/sad)
#   archU/L    how curved the lid edges are
#   pupil      pupil size multiplier, iris = iris size multiplier
#   tremble    shake in pixels (at 600px tall), sparkle = highlight size
NEUTRAL = dict(u=0.0, l=0.0, tilt=0.0, archU=1.0, archL=1.0,
               pupil=1.0, iris=1.0, tremble=0.0, sparkle=1.0)
LID_RATE = 9.0                 # how fast the lids/pupils ease to a new shape
SPEEDS = {"snappy": (24.0, 0.55),  # gaze spring (stiffness, damping): bouncy darts
          "slow": (5.0, 0.95)}     # lazy glides

AUDIO_EXTS = (".wav", ".ogg", ".mp3", ".flac")


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def bump(t, at, width=0.18):
    """A smooth 0->1->0 bump centred on `at`."""
    return math.exp(-((t - at) / width) ** 2)


# --------------------------------------------------------------------------
# Moods. Each gets (t = seconds since it started, d = its duration, st = scratch dict)
# and returns overrides for NEUTRAL plus optional:
#   gaze=(x, y) in -1..1 (otherwise the eyes keep wandering), speed="snappy"/"slow",
#   eyes=[left_overrides, right_overrides], offsets=[(dx,dy), (dx,dy)] per eye,
#   blinks=False to stop random blinks, lid_rate to change how fast lids move.
# --------------------------------------------------------------------------
def mood_angry(t, d, st):
    gx = st.setdefault("gx", random.uniform(-0.15, 0.15))
    return dict(u=0.46, l=0.30, tilt=1.0, archU=0.25, archL=0.3, pupil=0.6,
                tremble=2.5, gaze=(gx, 0.05), speed="snappy", blinks=False)


def mood_sly(t, d, st):
    side = st["side"]
    # side-eye on one side, slow glide across, hold, glide back
    k = smooth((t - 1.5) / 2.5) - smooth((t - 5.0) / 2.0)
    gx = side * 0.85 * math.cos(math.pi * k)
    return dict(u=0.52, l=0.32, tilt=0.35, archU=0.6, archL=-0.6, pupil=1.05,
                gaze=(gx, 0.18), speed="slow", blinks=False)


def mood_surprised(t, d, st):
    look = [(-0.75, -0.1), (0.75, -0.1), (-0.45, 0.2), (0.6, 0.0)]
    gaze = (0.0, 0.0) if t < 1.0 else look[int((t - 1.0) / 0.55) % len(look)]
    pop = 0.06 * math.exp(-t * 5) * math.cos(t * 28)  # little boing when it starts
    return dict(u=0.0, l=0.0, iris=0.82 + pop, pupil=0.32, sparkle=0.8,
                tremble=1.5 if t < 0.6 else 0.0, gaze=gaze, speed="snappy",
                blinks=False, lid_rate=20)


def mood_sleepy(t, d, st):
    phase = (t % 4.0) / 4.0
    u = 0.5 + 0.45 * smooth(phase / 0.85) if phase < 0.85 else 0.12  # droop... jolt awake
    return dict(u=u, l=0.12, tilt=-0.3, archU=1.2, pupil=1.1,
                gaze=(0.12 * math.sin(t * 0.5), 0.35), speed="slow", blinks=False,
                lid_rate=6 if phase < 0.85 else 25)


def mood_suspicious(t, d, st):
    sq = st.setdefault("squint", random.choice((0, 1)))
    eyes = [None, None]
    eyes[sq] = dict(u=0.5, l=0.36, tilt=0.55, archL=-0.3)       # one eye squints
    eyes[1 - sq] = dict(u=0.1, l=0.0, tilt=-0.5, archU=1.3)     # the other goes "hmm?"
    gx = 0.65 * st["side"] * (1 if int(t / 1.3) % 2 == 0 else -1)
    return dict(pupil=0.85, eyes=eyes, gaze=(gx, 0.05), speed="snappy", blinks=False)


def mood_puppy(t, d, st):
    if t < d - 1.4:  # fake-innocent puppy eyes while asking to come in...
        return dict(u=0.2, l=0.0, tilt=-0.9, archU=1.5, pupil=1.65, iris=1.05,
                    sparkle=1.7, gaze=(0.0, -0.15), speed="slow", blinks=False)
    # ...then the evil reveal
    return dict(u=0.48, l=0.30, tilt=1.0, archU=0.2, archL=-0.4, pupil=0.55,
                tremble=1.0, gaze=(0.0, 0.05), speed="snappy", blinks=False, lid_rate=18)


def mood_huff(t, d, st):
    # timed to the "Then I'll huff... and I'll puff... and I'll blow your house in!" line
    if t < 4.4:
        squeeze = bump(t, 0.65) + bump(t, 1.75)
        wide = smooth((t - 2.6) / 0.3) * (1 - smooth((t - 4.0) / 0.3))
        return dict(u=max(0.0, 0.35 + 0.45 * squeeze - 0.35 * wide),
                    l=max(0.0, 0.15 + 0.40 * squeeze - 0.15 * wide),
                    tilt=0.7 * (1 - wide), pupil=0.7 - 0.3 * wide, iris=1 + 0.1 * wide,
                    gaze=(0.0, 0.0), speed="snappy", blinks=False, lid_rate=22)
    # out of breath: dizzy spinning eyes, going opposite ways
    k = t - 4.4
    a = 2 * math.pi * 1.4 * k * max(0.35, 1 - k / 6)
    rad = 0.45 * smooth(k * 2)
    return dict(u=0.25, l=0.1, tilt=-0.4, pupil=0.75, gaze=(0.0, 0.0),
                offsets=[(rad * math.cos(a), rad * math.sin(a)),
                         (rad * math.cos(-a + math.pi), rad * math.sin(-a + math.pi))],
                blinks=False)


def mood_howl(t, d, st):
    return dict(u=0.25 + 0.2 * smooth(t / 3), l=0.15, tilt=-0.45, archU=1.4, archL=-0.3,
                gaze=(st["side"] * 0.2, -0.7), speed="slow", blinks=False)


def mood_stare(t, d, st):
    grow = smooth(t / 2.5)
    return dict(pupil=1.0 + 0.55 * grow, iris=1.0 + 0.1 * grow, sparkle=1.2,
                gaze=(0.0, 0.0), speed="slow", blinks=False)


# name: (function, duration range, [(delay, sound pattern)]). Negative delay = before the end.
# Sound patterns are globs inside sounds/, "|" means "any of these".
MOODS = {
    "angry":      (mood_angry,      (5, 7),     [(0.1, "growl/*")]),
    "sly":        (mood_sly,        (7, 8),     [(0.0, "sniff/sniff*"), (2.4, "voice/bacon*|voice/hungry*|voice/come_closer*")]),
    "surprised":  (mood_surprised,  (3.5, 4.5), [(0.0, "voice/whos_there*")]),
    "sleepy":     (mood_sleepy,     (8, 10),    [(0.0, "snore/*")]),
    "suspicious": (mood_suspicious, (5, 7),     [(0.3, "sniff/*")]),
    "puppy":      (mood_puppy,      (5.6, 6.0), [(0.2, "voice/little_pig*"), (-1.3, "growl/growl_hellhound*|growl/growl_agitated*")]),
    "huff":       (mood_huff,       (8, 9),     [(0.0, "voice/huff_puff*")]),
    "howl":       (mood_howl,       (6, 8),     [(0.3, "howl/*")]),
    "stare":      (mood_stare,      (5, 6),     [(0.2, "voice/big_eyes*|voice/come_closer*|voice/big_bad_wolf*")]),
}
MOOD_KEYS = list(MOODS)  # keys 1-9 in this order
MOOD_WEIGHTS = {"angry": 3, "sly": 3, "surprised": 2, "sleepy": 1.5, "suspicious": 2,
                "puppy": 2, "huff": 2, "howl": 2, "stare": 2}


# --------------------------------------------------------------------------
# Sound
# --------------------------------------------------------------------------
class Sounds:
    def __init__(self, enabled=True):
        self.ok = False
        self.muted = False
        self.cache = {}
        self.last = {}
        if not enabled:
            return
        try:
            pygame.mixer.init(44100, -16, 2, 1024)
            pygame.mixer.set_num_channels(4)
            self.main = pygame.mixer.Channel(0)
            self.ambient = pygame.mixer.Channel(1)
            self.ok = True
        except pygame.error as e:
            print(f"No audio output ({e}). Running silent.")
            return
        for cat in sorted(os.listdir(SOUND_DIR)) if os.path.isdir(SOUND_DIR) else []:
            n = len(self.files(cat + "/*"))
            print(f"  sounds/{cat}: {n} file{'s' if n != 1 else ''}")

    def files(self, pattern):
        found = []
        for alt in pattern.split("|"):
            found += [f for f in glob.glob(os.path.join(SOUND_DIR, alt))
                      if f.lower().endswith(AUDIO_EXTS)]
        return sorted(set(found))

    def load(self, path):
        if path not in self.cache:
            try:
                snd = pygame.mixer.Sound(path)
                snd.set_volume(VOLUME)
                self.cache[path] = snd
            except pygame.error as e:
                print(f"Can't play {path}: {e}")
                self.cache[path] = None
        return self.cache[path]

    def play(self, pattern, ambient=False):
        if not self.ok or self.muted:
            return
        if ambient and (self.main.get_busy() or self.ambient.get_busy()):
            return
        files = self.files(pattern)
        if not files:
            print(f"(no sound files for {pattern})")
            return
        if len(files) > 1 and self.last.get(pattern) in files:
            files.remove(self.last[pattern])  # don't repeat the same clip twice in a row
        path = random.choice(files)
        self.last[pattern] = path
        snd = self.load(path)
        if snd:
            (self.ambient if ambient else self.main).play(snd)
            print(f"  sound: {os.path.relpath(path, SOUND_DIR)}")

    def toggle_mute(self):
        self.muted = not self.muted
        if self.ok and self.muted:
            pygame.mixer.stop()
        print("Muted" if self.muted else "Unmuted")


# --------------------------------------------------------------------------
# Drawing one eye
# --------------------------------------------------------------------------
def make_iris(r):
    pad = 3
    size = 2 * (r + pad)
    c = r + pad
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    ring = max(3, int(r * 0.07))
    inner = r - ring
    pygame.draw.circle(s, IRIS_RING, (c, c), r)
    for rr in range(inner, 0, -1):  # radial gradient: bright yellow centre to deep amber edge
        pygame.draw.circle(s, lerp_color(IRIS_INNER, IRIS_OUTER, (rr / inner) ** 1.8), (c, c), rr)
    streaks = pygame.Surface((size, size), pygame.SRCALPHA)
    rnd = random.Random(3)
    for i in range(56):
        a = 2 * math.pi * i / 56 + rnd.uniform(-0.04, 0.04)
        r0, r1 = inner * rnd.uniform(0.38, 0.5), inner * rnd.uniform(0.72, 0.93)
        pygame.draw.line(streaks, (*IRIS_STREAK, 80),
                         (c + r0 * math.cos(a), c + r0 * math.sin(a)),
                         (c + r1 * math.cos(a), c + r1 * math.sin(a)), max(2, r // 70))
    s.blit(streaks, (0, 0))
    pygame.gfxdraw.aacircle(s, c, c, r, IRIS_RING)
    return s


def circle(surf, color, x, y, r):
    x, y, r = int(round(x)), int(round(y)), max(1, int(round(r)))
    pygame.gfxdraw.filled_circle(surf, x, y, r, color)
    pygame.gfxdraw.aacircle(surf, x, y, r, color)


def polygon(surf, color, pts):
    pts = [(int(round(x)), int(round(y))) for x, y in pts]
    pygame.gfxdraw.filled_polygon(surf, pts, color)
    pygame.gfxdraw.aapolygon(surf, pts, color)


class Eye:
    def __init__(self, side, size):
        self.side = side  # 0 = left screen (inner corner on its right), 1 = right screen
        self.w, self.h = size
        self.r = int(self.h * IRIS_SIZE)
        self.iris = make_iris(self.r)
        try:
            self.iris = self.iris.convert_alpha()
        except pygame.error:
            pass  # no display surface (two-window mode); unconverted is fine
        self.cache = {}
        self.p = dict(NEUTRAL)

    def update(self, target, dt, rate):
        k = 1 - math.exp(-rate * dt)
        for key, v in target.items():
            self.p[key] += (v - self.p[key]) * k

    def iris_sprite(self, sx, sy):
        key = (round(sx, 2), round(sy, 2))
        spr = self.cache.get(key)
        if spr is None:
            if len(self.cache) > 400:
                self.cache.clear()
            w, h = self.iris.get_size()
            spr = pygame.transform.smoothscale(self.iris, (max(2, int(w * sx)), max(2, int(h * sy))))
            self.cache[key] = spr
        return spr

    def draw(self, surf, gaze, blink):
        p, W, H, r = self.p, self.w, self.h, self.r
        surf.fill(WHITE)
        shake = p["tremble"] * H / 600
        gx, gy = gaze
        cx = W / 2 + gx * (W / 2 - r * 0.95) + random.uniform(-shake, shake)
        cy = H / 2 + gy * (H / 2 - r * 0.62) + random.uniform(-shake, shake)
        sx = p["iris"] * (1 - FORESHORTEN * min(1, abs(gx)))
        sy = p["iris"] * (1 - FORESHORTEN * min(1, abs(gy)))

        spr = self.iris_sprite(sx, sy)
        surf.blit(spr, (cx - spr.get_width() / 2, cy - spr.get_height() / 2))

        pr = r * PUPIL_SIZE * min(p["pupil"], 1.9)
        prx, pry = max(2, int(pr * sx)), max(2, int(pr * sy))
        pygame.gfxdraw.filled_ellipse(surf, int(cx), int(cy), prx, pry, PUPIL)
        pygame.gfxdraw.aaellipse(surf, int(cx), int(cy), prx, pry, PUPIL)

        sp = p["sparkle"]
        circle(surf, WHITE, cx - 0.36 * r * sx, cy - 0.38 * r * sy, 0.15 * r * p["iris"] * sp)
        circle(surf, WHITE, cx + 0.30 * r * sx, cy + 0.30 * r * sy, 0.06 * r * p["iris"] * sp)

        self.draw_lids(surf, blink)

    def draw_lids(self, surf, blink):
        p, W, H = self.p, self.w, self.h
        u = p["u"] + (1 - p["u"]) * blink
        l = p["l"] + (1 - p["l"]) * blink
        meet = H * MEET_Y
        top = lerp(-H * 0.08, meet, u)
        bot = lerp(H * 1.08, meet, l)
        tilt_u = p["tilt"] * H * 0.32 * min(1.0, u * 3)
        tilt_l = p["tilt"] * H * 0.06 * min(1.0, l * 3)
        ups, lows = [], []
        n = 32
        for i in range(n + 1):
            t = i / n
            inner = t if self.side == 0 else 1 - t  # 1 at the corner nearest the other eye
            s = math.sin(math.pi * t)
            yu = top - p["archU"] * H * 0.11 * s * (1 - u) + tilt_u * (inner - 0.5)
            yl = bot + p["archL"] * H * 0.09 * s * (1 - l) - tilt_l * (inner - 0.5)
            if yu > yl:
                yu = yl = (yu + yl) / 2
            ups.append((t * W, yu))
            lows.append((t * W, yl))

        edge = max(3, H * LID_EDGE_WIDTH)
        if max(y for _, y in ups) > -edge:
            polygon(surf, LID_EDGE, [(0, -20), (W, -20)] + [(x, y + edge) for x, y in reversed(ups)])
            polygon(surf, LID, [(0, -20), (W, -20)] + list(reversed(ups)))
        if min(y for _, y in lows) < H + edge:
            polygon(surf, LID_EDGE, [(0, H + 20), (W, H + 20)] + [(x, y - edge) for x, y in reversed(lows)])
            polygon(surf, LID, [(0, H + 20), (W, H + 20)] + list(reversed(lows)))


# --------------------------------------------------------------------------
# The wolf's "brain": wandering, blinking, moods and sound timing
# --------------------------------------------------------------------------
class Spring2D:
    def __init__(self):
        self.x = [0.0, 0.0]
        self.v = [0.0, 0.0]

    def update(self, target, dt, omega, zeta):
        steps = int(dt * omega / 0.25) + 1
        h = dt / steps
        for _ in range(steps):
            for i in (0, 1):
                a = omega * omega * (target[i] - self.x[i]) - 2 * zeta * omega * self.v[i]
                self.v[i] += a * h
                self.x[i] += self.v[i] * h


class Brain:
    def __init__(self, sounds, now, auto_moods=True):
        self.sounds = sounds
        self.auto_moods = auto_moods
        self.mood = None
        self.last_mood = None
        self.t0 = self.dur = 0.0
        self.st = {}
        self.pending = []
        self.next_mood = now + random.uniform(*FIRST_MOOD_AFTER)
        self.gaze_target = (0.0, 0.0)
        self.next_saccade = now + 1.0
        self.next_blink = now + 1.5
        self.blink_t = None
        self.blinks_queued = 0
        self.next_ambient = now + random.uniform(*AMBIENT_SOUND_EVERY)
        self.spring = Spring2D()

    def start_mood(self, name, now):
        fn, dur, sounds = MOODS[name]
        self.mood, self.t0 = name, now
        self.dur = random.uniform(*dur)
        self.st = {"side": random.choice((-1, 1))}
        self.pending = sorted((now + (dl if dl >= 0 else self.dur + dl), pat) for dl, pat in sounds)
        self.blink_t = None
        print(f"Mood: {name} ({self.dur:.1f}s)")

    def end_mood(self, now):
        self.last_mood, self.mood = self.mood, None
        self.pending = []
        self.next_mood = now + random.uniform(*IDLE_SECONDS)
        self.next_blink = now + 0.4  # a blink "resets" the face nicely
        self.next_ambient = max(self.next_ambient, now + 8)
        print("Mood: normal")

    def pick_mood(self):
        names = [n for n in MOODS if n != self.last_mood]
        return random.choices(names, [MOOD_WEIGHTS.get(n, 1) for n in names])[0]

    def blink(self, now):
        self.blink_t = now
        self.blinks_queued = 1 if random.random() < DOUBLE_BLINK_CHANCE else 0
        self.next_blink = now + random.uniform(*BLINK_EVERY)

    def blink_amount(self, now):
        if self.blink_t is None:
            return 0.0
        close, hold, open_ = 0.07, 0.05, 0.13
        e = now - self.blink_t
        if e < 0:
            return 0.0
        if e < close:
            return smooth(e / close)
        if e < close + hold:
            return 1.0
        if e < close + hold + open_:
            return 1 - smooth((e - close - hold) / open_)
        if self.blinks_queued:
            self.blinks_queued -= 1
            self.blink_t = now + 0.06
        else:
            self.blink_t = None
        return 0.0

    def new_saccade(self, now):
        if random.random() < 0.55:  # mostly glance around the middle (at people)
            self.gaze_target = (random.uniform(-0.35, 0.35), random.uniform(-0.25, 0.25))
        else:
            self.gaze_target = (random.uniform(-1, 1), random.uniform(-0.8, 0.8))
        self.next_saccade = now + random.uniform(0.6, 2.8)

    def update(self, now, dt):
        if self.mood is None and self.auto_moods and now >= self.next_mood:
            self.start_mood(self.pick_mood(), now)
        if self.mood and now - self.t0 >= self.dur:
            self.end_mood(now)
        while self.pending and self.pending[0][0] <= now:
            self.sounds.play(self.pending.pop(0)[1])

        r = {}
        if self.mood:
            r = MOODS[self.mood][0](now - self.t0, self.dur, self.st)
        elif now >= self.next_ambient:
            self.sounds.play(AMBIENT_SOUNDS, ambient=True)
            self.next_ambient = now + random.uniform(*AMBIENT_SOUND_EVERY)

        base = dict(NEUTRAL)
        base.update({k: v for k, v in r.items() if k in NEUTRAL})
        targets = []
        for over in r.get("eyes") or (None, None):
            t = dict(base)
            if over:
                t.update(over)
            targets.append(t)

        if "gaze" in r:
            self.gaze_target = r["gaze"]
            self.next_saccade = now + random.uniform(0.3, 1.0)
        elif now >= self.next_saccade:
            self.new_saccade(now)
        self.spring.update(self.gaze_target, dt, *SPEEDS[r.get("speed", "snappy")])
        gaze = [(self.spring.x[0] + dx, self.spring.x[1] + dy)
                for dx, dy in r.get("offsets", ((0, 0), (0, 0)))]

        if r.get("blinks", True) and self.blink_t is None and now >= self.next_blink:
            self.blink(now)
        return targets, gaze, self.blink_amount(now), r.get("lid_rate", LID_RATE)

    def force_mood(self, name, now):
        if self.mood:
            self.end_mood(now)
        if name:
            self.start_mood(name, now)


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------
class PreviewOutput:
    """Both eyes side by side in one window, for testing on a laptop."""
    def __init__(self, eye_size, scale):
        w, h = int(eye_size[0] * scale), int(eye_size[1] * scale)
        gap = max(8, int(40 * scale))
        self.screen = pygame.display.set_mode((2 * w + gap, h))
        pygame.display.set_caption("Big Bad Wolf eyes (preview)")
        self.screen.fill((25, 25, 30))
        self.surfaces = [self.screen.subsurface((0, 0, w, h)),
                         self.screen.subsurface((w + gap, 0, w, h))]
        self.sizes = [(w, h), (w, h)]

    def present(self):
        pygame.display.flip()


class SpanOutput:
    """One borderless window stretched across both screens (X11 desktops)."""
    def __init__(self, sizes, swap):
        os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
        (w0, h0), (w1, h1) = sizes
        self.screen = pygame.display.set_mode((w0 + w1, max(h0, h1)), pygame.NOFRAME)
        rects = [pygame.Rect(0, 0, w0, h0), pygame.Rect(w0, 0, w1, h1)]
        if swap:
            rects = [pygame.Rect(w1, 0, w0, h0), pygame.Rect(0, 0, w1, h1)]
        self.surfaces = [self.screen.subsurface(r) for r in rects]
        self.sizes = [r.size for r in rects]

    def present(self):
        pygame.display.flip()


class DualOutput:
    """A fullscreen window on each screen (works on the Pi 5's desktop)."""
    def __init__(self, displays):
        from pygame._sdl2.video import Renderer, Texture, Window
        desk = pygame.display.get_desktop_sizes()
        self.views = []
        self.surfaces, self.sizes = [], []
        for eye, disp in enumerate(displays):
            pos = 0x2FFF0000 | disp  # SDL_WINDOWPOS_CENTERED_DISPLAY(disp)
            win = Window(f"Wolf {'left' if eye == 0 else 'right'} eye", size=desk[disp],
                         position=(pos, pos), fullscreen_desktop=True)
            ren = Renderer(win)
            size = tuple(win.size)
            tex = Texture(ren, size, streaming=True)
            surf = pygame.Surface(size, 0, 32)
            self.views.append((win, ren, tex, surf))
            self.surfaces.append(surf)
            self.sizes.append(size)
            print(f"  {'Left' if eye == 0 else 'Right'} eye -> display {disp} at {size[0]}x{size[1]}")

    def present(self):
        for _, ren, tex, surf in self.views:
            tex.update(surf)
            ren.clear()
            tex.draw()
            ren.present()


def make_output(args):
    n = pygame.display.get_num_displays()
    mode = args.mode
    if mode == "auto":
        mode = "dual" if n >= 2 else "preview"
    print(f"Displays found: {n}   mode: {mode}")
    if mode == "preview":
        return PreviewOutput(args.size, args.scale)
    if n < 2 and not args.displays:
        print("Need two screens for this mode, but only found", n, "- check the HDMI cables/power.")
        sys.exit(3)  # run_wolf.sh waits and tries again
    displays = args.displays or ((1, 0) if args.swap else (0, 1))
    if any(d >= n for d in displays):
        print(f"Display {max(displays)} doesn't exist (found {n}).")
        sys.exit(3)
    if mode == "span":
        desk = pygame.display.get_desktop_sizes()
        return SpanOutput(desk[:2], swap=displays[0] > displays[1])
    return DualOutput(displays)


# --------------------------------------------------------------------------
def snapshot(out_dir, size=(1024, 600)):
    """Save a picture of every mood (left+right eye) for checking the look without screens."""
    os.makedirs(out_dir, exist_ok=True)
    random.seed(1)
    eyes = [Eye(0, size), Eye(1, size)]
    W, H = size
    gap = 40
    sheet = pygame.Surface((2 * W + gap, H))
    shots = [("normal", None, 0.0, (0.3, -0.1)), ("blink", None, 0.0, (0.0, 0.0))]
    for name, (_, dur, _) in MOODS.items():
        d = sum(dur) / 2
        times = {"puppy": [1.5, d - 0.5], "huff": [0.65, 3.0, 5.2], "sleepy": [3.0, 3.6],
                 "sly": [1.0, 3.5]}.get(name, [2.0])
        shots += [(name, name, t, None) for t in times]
    for i, (label, name, t, gaze) in enumerate(shots):
        r = MOODS[name][0](t, sum(MOODS[name][1]) / 2, {"side": 1}) if name else {}
        base = dict(NEUTRAL)
        base.update({k: v for k, v in r.items() if k in NEUTRAL})
        g = r.get("gaze", gaze or (0, 0))
        offs = r.get("offsets", ((0, 0), (0, 0)))
        sheet.fill((25, 25, 30))
        for e, eye in enumerate(eyes):
            eye.p = dict(base)
            eye.p.update(((r.get("eyes") or (None, None))[e]) or {})
            eye.p["tremble"] = 0
            surf = pygame.Surface(size)
            eye.draw(surf, (g[0] + offs[e][0], g[1] + offs[e][1]), 0.9 if label == "blink" else 0.0)
            sheet.blit(surf, (e * (W + gap), 0))
        path = os.path.join(out_dir, f"{i:02d}_{label}_{t:.1f}s.png")
        pygame.image.save(sheet, path)
        print(path)


def main():
    ap = argparse.ArgumentParser(description="Big Bad Wolf eyes")
    ap.add_argument("--mode", choices=["auto", "dual", "span", "preview"], default="auto",
                    help="dual = fullscreen on each screen (Pi), span = one window across both, "
                         "preview = side-by-side window")
    ap.add_argument("--swap", action="store_true", help="swap which screen gets which eye")
    ap.add_argument("--displays", type=lambda s: tuple(int(x) for x in s.split(",")),
                    help="display numbers for left,right eye, e.g. 1,0")
    ap.add_argument("--size", type=lambda s: tuple(int(x) for x in s.lower().split("x")),
                    default=(1024, 600), help="eye size for preview mode (default 1024x600)")
    ap.add_argument("--scale", type=float, default=0.6, help="preview window scale")
    ap.add_argument("--mute", action="store_true")
    ap.add_argument("--no-moods", action="store_true", help="only wander and blink")
    ap.add_argument("--seconds", type=float, default=0, help="quit after this long (testing)")
    ap.add_argument("--snapshot", metavar="DIR", help="save pictures of every mood and exit")
    args = ap.parse_args()

    pygame.display.init()
    if args.snapshot:
        snapshot(args.snapshot)
        return

    out = make_output(args)
    pygame.mouse.set_visible(False)
    eyes = [Eye(i, out.sizes[i]) for i in (0, 1)]
    sounds = Sounds(enabled=not args.mute)
    now = time.monotonic()
    brain = Brain(sounds, now, auto_moods=not args.no_moods)
    clock = pygame.time.Clock()
    started = now
    window_close = getattr(pygame, "WINDOWCLOSE", None)
    print(__doc__.split("Keys:")[1].strip() if "Keys:" in __doc__ else "")

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (window_close and ev.type == window_close):
                running = False
            elif ev.type == pygame.KEYDOWN:
                k = ev.unicode
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif k and k in "123456789" and int(k) <= len(MOOD_KEYS):
                    brain.force_mood(MOOD_KEYS[int(k) - 1], time.monotonic())
                elif k == "0":
                    brain.force_mood(None, time.monotonic())
                elif k == "b":
                    brain.blink(time.monotonic())
                elif k == "s":
                    sounds.play("*/*")
                elif k == "m":
                    sounds.toggle_mute()

        dt = min(clock.tick(FPS) / 1000.0, 0.1)
        now = time.monotonic()
        targets, gaze, blink, rate = brain.update(now, dt)
        for i, eye in enumerate(eyes):
            eye.update(targets[i], dt, rate)
            eye.draw(out.surfaces[i], gaze[i], blink)
        out.present()
        if args.seconds and now - started > args.seconds:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
