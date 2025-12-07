from langchain.tools import tool
import random


@tool
def roll_dice(dice_type: str, count: int = 1, modifier: int = 0) -> dict:
    """Roll dice with optional modifiers (e.g., 2d6+3)."""
    dice_map = {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12, "d20": 20, "d100": 100}

    sides = dice_map.get(dice_type.lower(), 20)
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    return {
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "formula": f"{count}{dice_type}+{modifier}" if modifier else f"{count}{dice_type}",
    }


@tool
def calculate_initiative(dexterity_modifier: int) -> int:
    """Roll initiative for combat (d20 + DEX modifier)."""
    return random.randint(1, 20) + dexterity_modifier


@tool
def calculate_attack(attack_bonus: int, target_ac: int) -> dict:
    """Calculate attack roll against target AC."""
    roll = random.randint(1, 20)
    total = roll + attack_bonus
    hit = total >= target_ac or roll == 20
    critical = roll == 20

    return {"roll": roll, "bonus": attack_bonus, "total": total, "hit": hit, "critical": critical}


@tool
def calculate_damage(
    dice_type: str, dice_count: int, modifier: int = 0, critical: bool = False
) -> dict:
    """Calculate damage with optional critical hit (doubles dice)."""
    damage_roll = roll_dice(dice_type, dice_count * 2 if critical else dice_count, modifier)
    return {**damage_roll, "critical": critical}


@tool
def check_saving_throw(save_bonus: int, dc: int) -> dict:
    """Make a saving throw against a DC."""
    roll = random.randint(1, 20)
    total = roll + save_bonus
    success = total >= dc or roll == 20

    return {
        "roll": roll,
        "bonus": save_bonus,
        "dc": dc,
        "total": total,
        "success": success,
        "critical_success": roll == 20,
        "critical_failure": roll == 1,
    }
