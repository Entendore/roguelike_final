# map_system.py
import random
import math
import pygame
import config

class Tile:
    def __init__(self, x, y, blocked):
        self.x = x
        self.y = y
        self.blocked = blocked
        self.explored = False
        self.visible = False
        self.trap_type = None
        self.triggered = False
        self.entity = None 
        self.item = None

class DungeonMap:
    def __init__(self):
        self.tiles = []
        self.rooms = []
        self.stairs_pos = None
        self.width = config.MAP_WIDTH
        self.height = config.MAP_HEIGHT

    def generate(self):
        self.tiles = [[Tile(x, y, True) for x in range(self.width)] for y in range(self.height)]
        self.rooms = []
        for _ in range(9):
            w = random.randint(4, 8)
            h = random.randint(4, 8)
            x = random.randint(1, self.width - w - 1)
            y = random.randint(1, self.height - h - 1)
            new_room = pygame.Rect(x, y, w, h)
            if not any(new_room.colliderect(r) for r in self.rooms):
                self.create_room(new_room)
                if self.rooms:
                    self.create_tunnel(self.rooms[-1].centerx, self.rooms[-1].centery, new_room.centerx, new_room.centery)
                self.rooms.append(new_room)

        self.stairs_pos = (self.rooms[-1].centerx, self.rooms[-1].centery)
        return self.rooms

    def create_room(self, rect):
        for y in range(rect.top, rect.bottom):
            for x in range(rect.left, rect.right):
                self.tiles[y][x].blocked = False

    def create_tunnel(self, x1, y1, x2, y2):
        if random.random() < 0.5:
            self.create_h_tunnel(x1, x2, y1)
            self.create_v_tunnel(y1, y2, x2)
        else:
            self.create_v_tunnel(y1, y2, x1)
            self.create_h_tunnel(x1, x2, y2)

    def create_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[y][x].blocked = False

    def create_v_tunnel(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[y][x].blocked = False

    def calculate_fov(self, player_x, player_y, radius=None):
        if radius is None: radius = config.FOV_RADIUS
        for row in self.tiles:
            for tile in row: tile.visible = False
        for y in range(player_y - int(radius), player_y + int(radius) + 1):
            for x in range(player_x - int(radius), player_x + int(radius) + 1):
                if 0 <= x < self.width and 0 <= y < self.height:
                    dist = math.sqrt((x - player_x)**2 + (y - player_y)**2)
                    if dist < radius and self.has_line_of_sight(player_x, player_y, x, y):
                        self.tiles[y][x].visible = True
                        self.tiles[y][x].explored = True

    def has_line_of_sight(self, x0, y0, x1, y1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx - dy
        while True:
            if x0 == x1 and y0 == y1: return True
            if self.tiles[y0][x0].blocked: return False
            e2 = 2 * err
            if e2 > -dy: err -= dy; x0 += sx
            if e2 < dx: err += dx; y0 += sy
