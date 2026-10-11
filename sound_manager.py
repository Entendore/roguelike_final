# sound_manager.py
import pygame
import random
import math
import array
import threading

class SoundManager:
    def __init__(self):
        try:
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.mixer.init()
            self.enabled = True
        except:
            print("Audio device not found. Disabling sound.")
            self.enabled = False
            return
        self.sounds = {}
        self.ready = False

        self.sound_thread = threading.Thread(target=self.generate_sounds)
        self.sound_thread.daemon = True
        self.sound_thread.start()

    def generate_wave(self, freq, duration, wave_type='square', decay=True):
        if not self.enabled: return None
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buf = array.array('h')
        for i in range(n_samples):
            t = float(i) / sample_rate
            val = 0
            if wave_type == 'square':
                val = 1.0 if int(t * freq * 2) % 2 == 0 else -1.0
            elif wave_type == 'saw':
                val = 2.0 * (t * freq - math.floor(0.5 + t * freq))
            elif wave_type == 'noise':
                val = random.uniform(-1, 1)
            vol = 32000
            if decay:
                if i < 500: vol = int(32000 * (i / 500))
                else: vol = int(32000 * math.exp(-(i - 500) / 1000.0))
            buf.append(int(val * vol))
        return pygame.mixer.Sound(buffer=buf)

    def generate_sounds(self):
        if not self.enabled: return
        self.sounds['step'] = self.generate_wave(100, 0.05, 'noise')
        self.sounds['hit'] = self.generate_wave(150, 0.1, 'saw')
        self.sounds['player_hit'] = self.generate_wave(100, 0.2, 'square')
        self.sounds['potion'] = self.generate_wave(600, 0.3, 'square')
        self.sounds['level_up'] = self.generate_wave(440, 0.6, 'square')
        self.sounds['die'] = self.generate_wave(50, 0.4, 'noise')
        self.sounds['equip'] = self.generate_wave(800, 0.1, 'square')
        self.ready = True

    def play(self, name):
        if self.enabled and self.ready and name in self.sounds:
            self.sounds[name].play()
