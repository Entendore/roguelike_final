# main.py
import pygame
import random
import math
import config
import sound_manager
import ai
import threading
import json
import time
import os
from collections import deque

from player import Player, Entity, Item, FloatingText, Weapon, Armor
from status import PoisonEffect, BurnEffect
from map_system import DungeonMap
import renderer
from projectiles import Projectile

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("Depths of Doom: Final Edition")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(config.FONT_MAIN, 14, bold=True)
        self.ui_font = pygame.font.SysFont(config.FONT_MAIN, 12)

        self.sound_manager = sound_manager.SoundManager()
        self.map_system = DungeonMap()

        self.state = "MENU" 
        self.floor = 1
        self.player = None
        self.entities = []
        self.items = []
        self.particles = []
        self.projectiles = []
        self.messages = deque(maxlen=6)
        self.blood_splatters = []
        self.show_inventory = False
        self.screen_shake = 0
        self.save_file = "savegame.json"

    def save_game(self):
        def save_thread():
            if not self.player: return
            save_data = {
                "floor": self.floor,
                "player": {
                    "hp": self.player.hp, "xp": self.player.xp, "level": self.player.level,
                    "potions": self.player.potions,
                    "weapon": self.player.weapon.name if self.player.weapon else None,
                    "weapon_atk": self.player.weapon.atk if self.player.weapon else 0,
                    "armor": self.player.armor.name if self.player.armor else None,
                    "armor_def": self.player.armor.defense if self.player.armor else 0,
                }
            }
            try:
                with open(self.save_file, "w") as f:
                    json.dump(save_data, f)
                print("Game Saved.")
                self.log("Game Saved.", "info")
            except Exception as e:
                print(f"Save failed: {e}")

        t = threading.Thread(target=save_thread)
        t.start()

    def load_game(self):
        if not os.path.exists(self.save_file):
            self.log("No save file found!", "danger")
            return
        try:
            with open(self.save_file, "r") as f:
                data = json.load(f)
            p_data = data['player']
            self.player = Player(0, 0)
            self.player.hp = p_data['hp']
            self.player.xp = p_data['xp']
            self.player.level = p_data['level']
            self.player.potions = p_data['potions']
            if p_data['weapon']: self.player.weapon = Weapon(0, 0, p_data['weapon'], p_data['weapon_atk'])
            if p_data['armor']: self.player.armor = Armor(0, 0, p_data['armor'], p_data['armor_def'])
            self.floor = data['floor']
            self.particles = []
            self.messages.clear()
            self.blood_splatters = []
            self.projectiles = []
            self.state = "PLAYING"
            self.generate_level()
            self.log(f"Game Loaded. Floor {self.floor}", "gain")
        except Exception as e:
            print(f"Load failed: {e}")
            self.log("Corrupt save file!", "danger")

    def log(self, msg, type="neutral"):
        color = config.COLOR_TEXT
        if type == "gain": color = config.COLOR_XP
        elif type == "danger": color = (255, 85, 85)
        elif type == "info": color = (100, 200, 255)
        self.messages.appendleft({"text": msg, "color": color})

    def generate_level(self):
        rooms = self.map_system.generate()
        if self.player is None:
            self.player = Player(rooms[0].centerx, rooms[0].centery)
        else:
            self.player.x = rooms[0].centerx
            self.player.y = rooms[0].centery
            self.player.max_hp = 30 + (self.player.level - 1) * 10 

        self.entities = [self.player]
        self.items = []
        for row in self.map_system.tiles:
            for t in row:
                t.entity = None
                t.item = None
        self.map_system.tiles[self.player.y][self.player.x].entity = self.player

        for i in range(1, len(rooms)):
            r = rooms[i]
            for _ in range(random.randint(1, 2)):
                ex, ey = random.randint(r.left+1, r.right-1), random.randint(r.top+1, r.bottom-1)
                roll = random.random()
                is_smart = False
                if roll < 0.6: enemy = Entity(ex, ey, "Slime", config.COLOR_ENEMY_SLIME, 12 + self.floor*2, 3 + self.floor//2, 0)
                elif roll < 0.9: enemy = Entity(ex, ey, "Goblin", config.COLOR_ENEMY_GOBLIN, 18 + self.floor*3, 5 + self.floor//2, 1)
                else:
                    enemy = Entity(ex, ey, "Ogre", config.COLOR_ENEMY_BOSS, 30 + self.floor*5, 8 + self.floor, 2)
                    is_smart = True
                enemy.use_smart_ai = is_smart
                self.entities.append(enemy)
                self.map_system.tiles[ey][ex].entity = enemy

            num_items = random.randint(0, 2)
            for _ in range(num_items):
                ix, iy = random.randint(r.left+1, r.right-1), random.randint(r.top+1, r.bottom-1)
                item_roll = random.random()
                if item_roll < 0.4: item = Item(ix, iy, "Health Potion", config.COLOR_POTION, "heal")
                elif item_roll < 0.7:
                    w_name = random.choice(["Rusty Sword", "Iron Axe", "Dagger"])
                    w_atk = random.randint(2, 4) + self.floor
                    item = Weapon(ix, iy, w_name, w_atk)
                else:
                    a_name = random.choice(["Leather Vest", "Iron Shield", "Chainmail"])
                    a_def = random.randint(1, 3)
                    item = Armor(ix, iy, a_name, a_def)
                self.items.append(item)
                self.map_system.tiles[iy][ix].item = item

        self.map_system.calculate_fov(self.player.x, self.player.y)

    def cast_fireball(self, tx, ty):
        if not hasattr(self, 'fireball_cooldown'): self.fireball_cooldown = 0
        if self.fireball_cooldown > 0:
            self.log("Fireball recharging...", "danger")
            return
        if not self.map_system.has_line_of_sight(self.player.x, self.player.y, tx, ty):
            self.log("Can't see target!", "danger")
            return

        self.fireball_cooldown = 5
        self.sound_manager.play('level_up')
        def on_hit():
            self.log("Fireball explodes!", "gain")
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    cx, cy = tx + dx, ty + dy
                    if 0 <= cx < config.MAP_WIDTH and 0 <= cy < config.MAP_HEIGHT:
                        tile = self.map_system.tiles[cy][cx]
                        if tile.entity:
                            dmg = 10 + (self.player.level * 2)
                            tile.entity.take_damage(dmg, self)
                            tile.entity.add_status(BurnEffect, 3, self)
                            self.particles.append(FloatingText(cx, cy, "BURN!", config.COLOR_HP))
            for _ in range(10):
                self.particles.append(FloatingText(tx, ty, "*", (255, 100, 0)))
        proj = Projectile(self.player.x, self.player.y, tx, ty, (255, 69, 0), on_hit)
        self.projectiles.append(proj)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN:
                if self.state == "MENU":
                    if event.key == pygame.K_RETURN:
                        self.floor = 1
                        self.player = None
                        self.particles = []
                        self.messages.clear()
                        self.state = "PLAYING"
                        self.generate_level()
                        self.log("Depths of Doom: Final Build", "info")
                    elif event.key == pygame.K_l:
                        self.load_game()
                elif self.state == "GAMEOVER":
                    if event.key == pygame.K_RETURN:
                        self.floor = 1
                        self.player = None
                        self.particles = []
                        self.messages.clear()
                        self.state = "PLAYING"
                        self.generate_level()
                        self.log("Depths of Doom: Final Build", "info")
                elif self.state == "PLAYING":
                    if event.key == pygame.K_i:
                        self.show_inventory = not self.show_inventory
                        return True
                    if event.key == pygame.K_s:
                        self.save_game()
                        return True
                    dx, dy = 0, 0
                    if event.key == pygame.K_w or event.key == pygame.K_UP: dy = -1
                    elif event.key == pygame.K_s or event.key == pygame.K_DOWN: dy = 1
                    elif event.key == pygame.K_a or event.key == pygame.K_LEFT: dx = -1
                    elif event.key == pygame.K_d or event.key == pygame.K_RIGHT: dx = 1

                    if dx != 0 or dy != 0:
                        mods = pygame.key.get_mods()
                        if mods & pygame.KMOD_SHIFT:
                            self.cast_fireball(self.player.x + dx*5, self.player.y + dy*5)
                        else:
                            self.player_turn(dx, dy)
                    elif event.key == pygame.K_SPACE: self.end_turn()
                    elif event.key == pygame.K_e or event.key == pygame.K_RETURN: self.use_potion()

            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "PLAYING":
                if event.button == 1:
                    mx, my = pygame.mouse.get_pos()
                    cam_x = self.player.x * config.TILE_SIZE - config.SCREEN_WIDTH // 2 + config.TILE_SIZE // 2
                    cam_y = self.player.y * config.TILE_SIZE - config.SCREEN_HEIGHT // 2 + config.TILE_SIZE // 2
                    tx = int((mx + cam_x) / config.TILE_SIZE)
                    ty = int((my + cam_y) / config.TILE_SIZE)
                    self.cast_fireball(tx, ty)
        return True

    def player_turn(self, dx, dy):
        tx, ty = self.player.x + dx, self.player.y + dy
        tile = self.map_system.tiles[ty][tx]
        target = tile.entity
        if target:
            self.attack(self.player, target)
        else:
            if self.player.move(dx, dy, self.map_system):
                self.sound_manager.play('step')
                if tile.trap_type and not tile.triggered:
                    tile.triggered = True
                    dmg = 5
                    self.player.take_damage(dmg, self)
                    self.log(f"Triggered {tile.trap_type} trap! Took {dmg} dmg.", "danger")
                    self.screen_shake = 5
                    self.blood_splatters.append((tx, ty))
                item = tile.item
                if item:
                    if isinstance(item, (Weapon, Armor)):
                        self.player.equip(item, self)
                    elif item.type == "heal":
                        self.player.potions += 1
                        self.log("Picked up a Health Potion!", "gain")
                        self.particles.append(FloatingText(self.player.x, self.player.y, "Potion!", config.COLOR_POTION))
                        self.map_system.tiles[item.y][item.x].item = None
                        if item in self.items: self.items.remove(item)
                if (tx, ty) == self.map_system.stairs_pos:
                    self.floor += 1
                    self.log(f"Descending to Floor {self.floor}...", "info")
                    self.save_game()
                    self.generate_level()
                    return
            else:
                return 
        self.end_turn()

    def use_potion(self):
        if self.player.potions > 0:
            heal = 20
            self.player.hp = min(self.player.max_hp, self.player.hp + heal)
            self.player.potions -= 1
            self.sound_manager.play('potion')
            self.log(f"Used potion. Healed {heal} HP.", "gain")
            self.particles.append(FloatingText(self.player.x, self.player.y, "+20 HP", config.COLOR_POTION))
            self.end_turn()
        else:
            self.log("No potions left!", "danger")

    def attack(self, attacker, defender):
        base_dmg = attacker.total_atk if hasattr(attacker, 'total_atk') else attacker.atk
        dmg = max(1, int(random.random() * base_dmg) + 1)
        attacker_level =  getattr(attacker, 'level', 1)
        if random.random() < 0.1 + (attacker_level * 0.01):
            dmg = int(dmg * 1.5)
            self.log("Critical Hit!", "info")
        if defender.name == "Slime" and random.random() < 0.2:
             defender.add_status(PoisonEffect, 5, self)
        self.log(f"{attacker.name} hits {defender.name} for {dmg}.")
        died = False
        if hasattr(defender, 'take_damage'):
            died = defender.take_damage(dmg, self)
        else:
            defender.hp -= max(1, dmg - defender.defense)
            if defender.hp <= 0: died = True
        if died:
            self.blood_splatters.append((defender.x, defender.y))
            self.log(f"{defender.name} dies!", "gain")
            if attacker == self.player:
                attacker.gain_xp(12 + self.floor * 2, self)

    def end_turn(self):
        if hasattr(self, 'fireball_cooldown') and self.fireball_cooldown > 0:
            self.fireball_cooldown -= 1
        for e in self.entities + [self.player]:
            if e.dead: continue
            for status in list(e.status_effects.values()):
                status.apply(e, self)
        for e in self.entities:
            if e == self.player or e.dead: continue
            dist = math.sqrt((e.x - self.player.x)**2 + (e.y - self.player.y)**2)
            if dist < 7 and self.map_system.tiles[e.y][e.x].visible:
                dx, dy = 0, 0
                if e.use_smart_ai:
                    dx, dy = ai.SmartEnemyAI.get_best_move(e, self.player, self.map_system)
                else:
                    if e.x < self.player.x: dx = 1
                    elif e.x > self.player.x: dx = -1
                    if e.y < self.player.y: dy = 1
                    elif e.y > self.player.y: dy = -1
                tx, ty = e.x + dx, e.y + dy
                if self.map_system.tiles[ty][tx].entity == self.player:
                    self.attack(e, self.player)
                else:
                    if not e.move(dx, dy, self.map_system):
                        if dx != 0 and dy != 0:
                            if e.move(dx, 0, self.map_system): pass
                            elif e.move(0, dy, self.map_system): pass
        for e in self.entities:
            if e.dead:
                self.map_system.tiles[e.y][e.x].entity = None
        self.entities = [e for e in self.entities if not e.dead]
        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.projectiles: p.update()
        self.projectiles = [p for p in self.projectiles if p.active]
        flicker = math.sin(time.time() * 10) * 0.5
        current_fov = config.FOV_RADIUS + flicker
        self.map_system.calculate_fov(self.player.x, self.player.y, current_fov)
        if self.screen_shake > 0: self.screen_shake -= 1
        if self.player.dead: self.state = "GAMEOVER"

    def run(self):
        running = True
        while running:
            running = self.handle_input()
            self.screen.fill(config.COLOR_BG)
            if self.state == "PLAYING":
                cam_x = self.player.x * config.TILE_SIZE - config.SCREEN_WIDTH // 2 + config.TILE_SIZE // 2
                cam_y = self.player.y * config.TILE_SIZE - config.SCREEN_HEIGHT // 2 + config.TILE_SIZE // 2
                if self.screen_shake > 0:
                    cam_x += random.randint(-4, 4)
                    cam_y += random.randint(-4, 4)
                renderer.draw_map(self.screen, self.map_system, cam_x, cam_y, self.blood_splatters)
                renderer.draw_stairs(self.screen, self.map_system, cam_x, cam_y)
                for item in self.items:
                    if self.map_system.tiles[item.y][item.x].visible:
                        item.draw(self.screen, cam_x, cam_y)
                self.entities.sort(key=lambda e: e.y)
                for e in self.entities:
                    if self.map_system.tiles[e.y][e.x].visible:
                        e.draw(self.screen, cam_x, cam_y)
                for p in self.projectiles:
                    p.draw(self.screen, cam_x, cam_y, config.TILE_SIZE)
                for p in self.particles: p.draw(self.screen, self.font, cam_x, cam_y)
                renderer.draw_ui(self.screen, self.player, self.floor, self.messages, self.font, self.ui_font)
                if self.show_inventory:
                    renderer.draw_inventory(self.screen, self.player, self.font)
            elif self.state == "MENU":
                renderer.draw_centered_text(self.screen, "DEPTHS OF DOOM", -50, config.COLOR_STAIRS, 32)
                if os.path.exists(self.save_file):
                    renderer.draw_centered_text(self.screen, "[ENTER] New Game  [L] Load Game", 10, (150, 150, 150), 16)
                else:
                    renderer.draw_centered_text(self.screen, "Press ENTER to Start", 10, (150, 150, 150), 16)
            elif self.state == "GAMEOVER":
                renderer.draw_centered_text(self.screen, "YOU DIED", -50, (255, 50, 50), 40)
                renderer.draw_centered_text(self.screen, "Press ENTER to Restart", 60, (150, 150, 150), 16)
            pygame.display.flip()
            self.clock.tick(config.FPS)
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
