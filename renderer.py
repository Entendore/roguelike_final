# renderer.py
import pygame
import config

def draw_map(surface, game_map, camera_x, camera_y, blood_list):
    for y in range(game_map.height):
        for x in range(game_map.width):
            tile = game_map.tiles[y][x]
            rect = (x * config.TILE_SIZE - camera_x, y * config.TILE_SIZE - camera_y, config.TILE_SIZE, config.TILE_SIZE)
            if not (-config.TILE_SIZE < rect[0] < config.SCREEN_WIDTH and -config.TILE_SIZE < rect[1] < config.SCREEN_HEIGHT): continue
            if tile.visible:
                color = config.COLOR_WALL if tile.blocked else config.COLOR_FLOOR
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, (40,40,40), rect, 1)
            elif tile.explored:
                color = config.COLOR_WALL_DARK if tile.blocked else config.COLOR_FLOOR_DARK
                pygame.draw.rect(surface, color, rect)
                s = pygame.Surface((config.TILE_SIZE, config.TILE_SIZE))
                s.set_alpha(100)
                s.fill((0,0,0))
                surface.blit(s, (rect[0], rect[1]))
            if tile.visible:
                for bx, by in blood_list:
                    if bx == x and by == y:
                        pygame.draw.circle(surface, (139, 0, 0), (rect[0]+16, rect[1]+16), 8)
            if tile.visible and tile.triggered and tile.trap_type:
                c = (100, 0, 0) if tile.trap_type == 'spikes' else (200, 50, 0)
                pygame.draw.line(surface, c, (rect[0]+8, rect[1]+8), (rect[0]+24, rect[1]+24), 3)
                pygame.draw.line(surface, c, (rect[0]+24, rect[1]+8), (rect[0]+8, rect[1]+24), 3)

def draw_stairs(surface, game_map, camera_x, camera_y):
    sx, sy = game_map.stairs_pos
    if game_map.tiles[sy][sx].visible:
        s_rect = (sx * config.TILE_SIZE - camera_x, sy * config.TILE_SIZE - camera_y, config.TILE_SIZE, config.TILE_SIZE)
        pygame.draw.polygon(surface, config.COLOR_STAIRS, [
            (s_rect[0] + 16, s_rect[1] + 4),
            (s_rect[0] + 4, s_rect[1] + 28),
            (s_rect[0] + 28, s_rect[1] + 28)
        ])

def draw_ui(surface, player, floor, messages, font, ui_font):
    s = pygame.Surface((config.SCREEN_WIDTH, 70))
    s.set_alpha(220)
    s.fill((30, 30, 35))
    surface.blit(s, (0,0))

    cd_text = ""
    if hasattr(player, 'fireball_cooldown'):
        if player.fireball_cooldown > 0: cd_text = f" [FIREBALL: {player.fireball_cooldown}]"
        else: cd_text = " [FIREBALL: READY]"

    stats = [f"LVL: {player.level}", f"FLR: {floor}", f"ATK: {player.total_atk}", f"DEF: {player.total_def}{cd_text}"]
    for i, text in enumerate(stats):
        surf = ui_font.render(text, True, config.COLOR_TEXT)
        surface.blit(surf, (10 + i*110, 10))

    hp_surf = ui_font.render(f"HP: {player.hp}/{player.max_hp}", True, config.COLOR_HP)
    surface.blit(hp_surf, (10, 30))

    equip_text = f"Wpn: {player.weapon.name if player.weapon else 'None'} | "
    equip_text += f"Amr: {player.armor.name if player.armor else 'None'}"
    equip_surf = ui_font.render(equip_text, True, (200, 200, 200))
    surface.blit(equip_surf, (10, 45))

    pot_surf = ui_font.render(f"Potions: {player.potions} [E]", True, config.COLOR_POTION)
    surface.blit(pot_surf, (config.SCREEN_WIDTH - 150, 10))

    bar_w, bar_h = 150, 10
    bar_x = config.SCREEN_WIDTH // 2 - bar_w // 2
    pygame.draw.rect(surface, (50, 50, 50), (bar_x, 30, bar_w, bar_h))
    hp_pct = max(0, player.hp / player.max_hp)
    pygame.draw.rect(surface, config.COLOR_HP, (bar_x, 30, int(bar_w * hp_pct), bar_h))
    pygame.draw.rect(surface, (50, 50, 50), (bar_x, 45, bar_w, bar_h))
    xp_pct = min(1, player.xp / player.xp_to_next)
    pygame.draw.rect(surface, config.COLOR_XP, (bar_x, 45, int(bar_w * xp_pct), bar_h))

    log_bg = pygame.Surface((config.SCREEN_WIDTH, 100))
    log_bg.set_alpha(180)
    log_bg.fill((0,0,0))
    surface.blit(log_bg, (0, config.SCREEN_HEIGHT - 100))
    y_off = config.SCREEN_HEIGHT - 90
    for msg in messages:
        txt = ui_font.render(f"> {msg['text']}", True, msg['color'])
        surface.blit(txt, (10, y_off))
        y_off += 16

def draw_inventory(surface, player, font):
    overlay = pygame.Surface((400, 300))
    overlay.set_alpha(240)
    overlay.fill((0, 0, 0))
    ox = (config.SCREEN_WIDTH - 400) // 2
    oy = (config.SCREEN_HEIGHT - 300) // 2
    surface.blit(overlay, (ox, oy))
    pygame.draw.rect(surface, (255, 255, 255), (ox, oy, 400, 300), 2)

    title = font.render(f"INVENTORY - Lvl {player.level}", True, config.COLOR_TEXT)
    surface.blit(title, (ox + 20, oy + 20))

    stats = [f"HP: {player.hp}/{player.max_hp}", f"ATK: {player.total_atk} (Base: {player.atk})", f"DEF: {player.total_def} (Base: {player.defense})", f"XP: {player.xp}/{player.xp_to_next}"]
    y_off = oy + 60
    for stat in stats:
        s_surf = font.render(stat, True, (200, 200, 200))
        surface.blit(s_surf, (ox + 20, y_off))
        y_off += 30

    w_name = player.weapon.name if player.weapon else "None"
    a_name = player.armor.name if player.armor else "None"
    w_surf = font.render(f"Weapon: {w_name}", True, config.COLOR_WEAPON)
    a_surf = font.render(f"Armor:  {a_name}", True, config.COLOR_ARMOR)
    surface.blit(w_surf, (ox + 20, y_off + 10))
    surface.blit(a_surf, (ox + 20, y_off + 40))

    if player.status_effects:
        status_surf = font.render("Status:", True, (255, 100, 100))
        surface.blit(status_surf, (ox + 20, y_off + 80))
        for i, status in enumerate(player.status_effects):
            s_text = font.render(f"- {status.name} ({status.duration} turns)", True, status.color)
            surface.blit(s_text, (ox + 30, y_off + 100 + (i*20)))

    help_surf = font.render("Press 'I' to Close", True, (150, 150, 150))
    surface.blit(help_surf, (ox + 120, oy + 260))

def draw_centered_text(surface, text, y_offset, color, size):
    f = pygame.font.SysFont(config.FONT_MAIN, size, bold=True)
    surf = f.render(text, True, color)
    rect = surf.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + y_offset))
    surface.blit(surf, rect)
