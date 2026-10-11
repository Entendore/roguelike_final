# status.py
import config
import random

class StatusEffect:
    def __init__(self, name, duration, color):
        self.name = name
        self.duration = duration
        self.color = color

    def apply(self, entity, game):
        self.duration -= 1
        if self.duration <= 0:
            game.log(f"{entity.name} is no longer {self.name}.", "info")
            if self in entity.status_effects:
                entity.status_effects.remove(self)
            return

class PoisonEffect(StatusEffect):
    def __init__(self, duration):
        super().__init__("Poisoned", duration, (46, 204, 113))

    def apply(self, entity, game):
        super().apply(entity, game)
        if self.duration > 0:
            dmg = 2
            entity.hp -= dmg
            game.log(f"{entity.name} takes {dmg} poison damage.", "danger")
            if hasattr(game, 'particles'):
                from player import FloatingText
                game.particles.append(FloatingText(entity.x, entity.y, f"{dmg} Poison", self.color))
            if entity.hp <= 0:
                entity.hp = 0
                entity.dead = True
                game.sound_manager.play('die')
                game.log(f"{entity.name} died of poison!", "danger")

class BurnEffect(StatusEffect):
    def __init__(self, duration):
        super().__init__("Burning", duration, (231, 76, 60))

    def apply(self, entity, game):
        super().apply(entity, game)
        if self.duration > 0:
            dmg = 3
            entity.hp -= dmg
            game.log(f"{entity.name} burns for {dmg} damage.", "danger")
            if hasattr(game, 'particles'):
                from player import FloatingText
                game.particles.append(FloatingText(entity.x, entity.y, f"{dmg} Burn", self.color))
            if entity.hp <= 0:
                entity.hp = 0
                entity.dead = True
                game.sound_manager.play('die')
                game.log(f"{entity.name} burned to ash!", "danger")

class HealingPotion:
    def __init__(self, healing_amount=20):
        self.healing_amount = healing_amount
        self.name = "Healing Potion"
        self.color = config.COLOR_POTION

    def use(self, target, game):
        heal = self.healing_amount
        target.hp = min(target.max_hp, target.hp + heal)
        game.sound_manager.play('potion')
        game.log(f"Used {self.name}. Healed for {heal} HP.", "gain")
        if hasattr(game, 'particles'):
            from player import FloatingText
            game.particles.append(FloatingText(target.x, target.y, f"+{heal} HP", self.color))
        return True
