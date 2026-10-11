# projectiles.py
import pygame
import math

class Projectile:
    def __init__(self, start_x, start_y, target_x, target_y, color, on_hit_callback):
        self.x = start_x
        self.y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.color = color
        self.on_hit = on_hit_callback
        self.speed = 0.2 

        dist = math.sqrt((target_x - start_x)**2 + (target_y - start_y)**2)
        if dist == 0: dist = 1
        self.dx = (target_x - start_x) / dist * self.speed
        self.dy = (target_y - start_y) / dist * self.speed

        self.active = True
        self.current_x = start_x
        self.current_y = start_y

    def update(self):
        self.current_x += self.dx
        self.current_y += self.dy

        dist_to_target = math.sqrt((self.current_x - self.target_x)**2 + (self.current_y - self.target_y)**2)

        if dist_to_target < self.speed:
            self.active = False
            if self.on_hit:
                self.on_hit()

    def draw(self, surface, camera_x, camera_y, tile_size):
        screen_x = int(self.current_x * tile_size - camera_x)
        screen_y = int(self.current_y * tile_size - camera_y)

        pygame.draw.circle(surface, (255, 200, 50), (screen_x, screen_y), 6)
        pygame.draw.circle(surface, self.color, (screen_x, screen_y), 4)
