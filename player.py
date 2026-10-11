# player.py
import pygame
import random
import config
from dataclasses import dataclass
from status import StatusEffect, PoisonEffect, BurnEffect
from typing import Optional, Dict, Type

@dataclass
class Weapon:
    x: int
    y: int
    name: str
    atk: int
    color: tuple = config.COLOR_WEAPON
    type: str = "weapon"

    def draw(self, surface, camera_x, camera_y):
        screen_x = self.x * config.TILE_SIZE - camera_x
        screen_y = self.y * config.TILE_SIZE - camera_y
        cx = screen_x + config.TILE_SIZE // 2
        cy = screen_y + config.TILE_SIZE // 2
        pygame.draw.rect(surface, (200,200,200), (cx-1, cy-8, 2, 16))
        pygame.draw.rect(surface, self.color, (cx-4, cy-8, 8, 6))

@dataclass
class Armor:
    x: int
    y: int
    name: str
    defense: int
    color: tuple = config.COLOR_ARMOR
    type: str = "armor"

    def draw(self, surface, camera_x, camera_y):
        screen_x = self.x * config.TILE_SIZE - camera_x
        screen_y = self.y * config.TILE_SIZE - camera_y
        cx = screen_x + config.TILE_SIZE // 2
        cy = screen_y + config.TILE_SIZE // 2
        pygame.draw.circle(surface, self.color, (cx, cy), 8)
        pygame.draw.circle(surface, (200,200,200), (cx, cy), 8, 1)

class Entity:
    def __init__(self, x, y, name, color, hp, atk, defense):
        self.x = x
        self.y = y
        self.name = name
        self.color = color
        self.max_hp = hp
        self.hp = hp
        self.atk = atk
        self.defense = defense
        self.dead = False
        self.flash_timer = 0
        self.use_smart_ai = False
        self.status_effects: Dict[Type[StatusEffect], StatusEffect] = {}

    def add_status(self, effect_class: Type[StatusEffect], duration, game):
        if effect_class in self.status_effects:
            self.status_effects[effect_class].duration += duration
        else:
            self.status_effects[effect_class] = effect_class(duration)
            game.log(f"{self.name} is {self.status_effects[effect_class].name}!", "danger")

    def move(self, dx, dy, game_map):
        target_x = self.x + dx
        target_y = self.y + dy
        if 0 <= target_x < config.MAP_WIDTH and 0 <= target_y < config.MAP_HEIGHT and not game_map.tiles[target_y][target_x].blocked:
            game_map.tiles[self.y][self.x].entity = None
            self.x = target_x
            self.y = target_y
            game_map.tiles[self.y][self.x].entity = self
            return True
        return False

    def take_damage(self, amount, game):
        actual_damage = max(1, amount - self.defense)
        self.hp -= actual_damage
        self.flash_timer = 10
        if self == game.player:
            game.sound_manager.play('player_hit')
            game.screen_shake = 5
        else:
            game.sound_manager.play('hit')
            if hasattr(game, 'particles'):
                from player import FloatingText
                game.particles.append(FloatingText(self.x, self.y, str(actual_damage), (255, 50, 50)))
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            game.sound_manager.play('die')
            return True
        return False

    def draw(self, surface, camera_x, camera_y):
        screen_x = self.x * config.TILE_SIZE - camera_x
        screen_y = self.y * config.TILE_SIZE - camera_y
        if not (-config.TILE_SIZE < screen_x < config.SCREEN_WIDTH and -config.TILE_SIZE < screen_y < config.SCREEN_HEIGHT): return
        draw_color = config.COLOR_FLASH if self.flash_timer > 0 else self.color
        if self.flash_timer > 0: self.flash_timer -= 1
        pygame.draw.ellipse(surface, (0,0,0,100), (screen_x + 4, screen_y + config.TILE_SIZE - 8, config.TILE_SIZE - 8, config.TILE_SIZE // 4))
        cx, cy = screen_x + config.TILE_SIZE // 2, screen_y + config.TILE_SIZE // 2
        size = config.TILE_SIZE // 2 - 2
        if self.name == "Hero": pygame.draw.circle(surface, draw_color, (cx, cy), size)
        elif self.name == "Slime": pygame.draw.rect(surface, draw_color, (cx - size, cy - size + 4, size*2, size*2 - 4), border_radius=8)
        else:
            points = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
            pygame.draw.polygon(surface, draw_color, points)
        pygame.draw.circle(surface, (255,255,255), (cx - 4, cy - 2), 2)
        pygame.draw.circle(surface, (255,255,255), (cx + 4, cy - 2), 2)

class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, "Hero", config.COLOR_PLAYER, 30, 4, 1)
        self.xp = 0
        self.xp_to_next = 20
        self.level = 1
        self.potions = 1
        self.weapon: Optional[Weapon] = None
        self.armor: Optional[Armor] = None

    @property
    def total_atk(self): return self.atk + (self.weapon.atk if self.weapon else 0)
    @property
    def total_def(self): return self.defense + (self.armor.defense if self.armor else 0)

    def equip(self, item, game):
        old_item = None
        if isinstance(item, Weapon):
            old_item = self.weapon
            self.weapon = item
            game.log(f"Equipped {item.name}. ATK increased by {item.atk}.", "gain")
        elif isinstance(item, Armor):
            old_item = self.armor
            self.armor = item
            game.log(f"Equipped {item.name}. DEF increased by {item.defense}.", "gain")

        if game.map_system.tiles[item.y][item.x].item == item:
            game.map_system.tiles[item.y][item.x].item = None
        if item in game.items: game.items.remove(item)
        game.sound_manager.play('equip')

    def gain_xp(self, amount, game):
        self.xp += amount
        game.log(f"Gained {amount} XP.", "info")
        if self.xp >= self.xp_to_next:
            self.level_up(game)

    def level_up(self, game):
        self.level += 1
        self.xp -= self.xp_to_next
        self.xp_to_next = int(self.xp_to_next * 1.5)
        self.max_hp += 10
        self.hp = self.max_hp
        self.atk += 2
        self.defense += 1
        game.log(f"LEVEL UP! Lvl {self.level}.", "gain")
        if hasattr(game, 'particles'):
            from player import FloatingText
            game.particles.append(FloatingText(self.x, self.y, "LEVEL UP!", (255, 255, 0)))
        game.sound_manager.play('level_up')

class FloatingText:
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = str(text)
        self.color = color
        self.life = 45 
        self.y_offset = 0
    def update(self):
        self.life -= 1
        self.y_offset -= 0.8
    def draw(self, surface, font, camera_x, camera_y):
        if self.life > 0:
            screen_x = self.x * config.TILE_SIZE - camera_x + config.TILE_SIZE // 2
            screen_y = self.y * config.TILE_SIZE - camera_y + self.y_offset
            alpha = min(255, self.life * 8)
            text_surf = font.render(self.text, True, self.color)
            text_surf.set_alpha(alpha)
            rect = text_surf.get_rect(center=(screen_x, screen_y))
            surface.blit(text_surf, rect)

@dataclass
class Item:
    x: int
    y: int
    name: str
    color: tuple
    type: str
    def draw(self, surface, camera_x, camera_y):
        screen_x = self.x * config.TILE_SIZE - camera_x
        screen_y = self.y * config.TILE_SIZE - camera_y
        is_on_screen_x = -config.TILE_SIZE < screen_x < config.SCREEN_WIDTH
        is_on_screen_y = -config.TILE_SIZE < screen_y < config.SCREEN_HEIGHT
        if is_on_screen_x and is_on_screen_y:
            cx = screen_x + config.TILE_SIZE // 2
            cy = screen_y + config.TILE_SIZE // 2
            pygame.draw.circle(surface, self.color, (cx, cy), 6)
            pygame.draw.rect(surface, (200, 200, 200), (cx - 2, cy - 10, 4, 6))
