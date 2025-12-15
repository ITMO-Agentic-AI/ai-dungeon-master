"""
Asset Service for AI Dungeon Master.

Manages audio files (background music, sound effects) and images
(character portraits, maps, items) for the Chainlit interface.
"""

import chainlit as cl


class AssetService:
    """Service for managing game assets (audio, images)."""

    # Asset paths configuration
    # Note: Paths are relative to the Chainlit app root
    MUSIC_PATHS = {
        "tavern": "public/audio/music/tavern.mp3",
        "battle": "public/audio/music/battle.mp3",
        "dungeon": "public/audio/music/dungeon.mp3",
        "exploration": "public/audio/music/exploration.mp3",
        "victory": "public/audio/music/victory.mp3",
        "town": "public/audio/music/town.mp3",
        "forest": "public/audio/music/forest.mp3",
    }

    SFX_PATHS = {
        "attack": "public/audio/sfx/attack.mp3",
        "magic": "public/audio/sfx/magic.mp3",
        "investigate": "public/audio/sfx/investigate.mp3",
        "door": "public/audio/sfx/door.mp3",
        "dice": "public/audio/sfx/dice.mp3",
        "move": "public/audio/sfx/move.mp3",
        "social": "public/audio/sfx/social.mp3",
        "interact": "public/audio/sfx/interact.mp3",
    }

    CHARACTER_IMAGE_PATHS = {
        "warrior": "public/images/characters/warrior.jpeg",
        "fighter": "public/images/characters/warrior.jpeg",
        "wizard": "public/images/characters/wizard.jpeg",
        "mage": "public/images/characters/wizard.jpeg",
        "rogue": "public/images/characters/rogue.jpeg",
        "thief": "public/images/characters/rogue.jpeg",
        "cleric": "public/images/characters/cleric.jpeg",
        "paladin": "public/images/characters/paladin.jpeg",
        "ranger": "public/images/characters/ranger.jpeg",
        "bard": "public/images/characters/bard.jpeg",
    }

    MAP_IMAGE_PATHS = {
        "tavern": "public/images/maps/tavern.jpeg",
        "dungeon": "public/images/maps/dungeon.jpeg",
        "forest": "public/images/maps/forest.jpeg",
        "town": "public/images/maps/town.jpeg",
        "castle": "public/images/maps/castle.jpeg",
    }

    @staticmethod
    def get_scene_music(
        scene_type: str, combat: bool = False, auto_play: bool = True
    ) -> cl.Audio | None:
        """
        Get appropriate background music for a scene.

        Args:
            scene_type: Type of scene (tavern, dungeon, forest, etc.)
            combat: Whether scene is in combat mode
            auto_play: Whether to auto-play the music

        Returns:
            cl.Audio element or None if path not found
        """
        if combat:
            music_path = AssetService.MUSIC_PATHS.get("battle")
            name = "Battle Music"
        else:
            scene_lower = scene_type.lower()
            music_path = AssetService.MUSIC_PATHS.get(
                scene_lower, AssetService.MUSIC_PATHS.get("exploration")
            )
            name = f"{scene_type.title()} Music"

        if music_path:
            return cl.Audio(name=name, path=music_path, display="inline", auto_play=auto_play)
        return None

    @staticmethod
    def get_sound_effect(action_type: str) -> cl.Audio | None:
        """
        Get sound effect for an action type.

        Args:
            action_type: Type of action (attack, magic, investigate, etc.)

        Returns:
            cl.Audio element or None if path not found
        """
        action_lower = action_type.lower()
        sfx_path = AssetService.SFX_PATHS.get(action_lower)

        if sfx_path:
            return cl.Audio(
                name=f"{action_type}_sfx", path=sfx_path, display="inline", auto_play=True
            )
        return None

    @staticmethod
    def get_character_portrait(
        character_class: str, size: str = "medium", display: str = "side"
    ) -> cl.Image | None:
        """
        Get character portrait image by class.

        Args:
            character_class: Character class (wizard, warrior, etc.)
            size: Image size (small, medium, large)
            display: Display mode (inline, side, page)

        Returns:
            cl.Image element or None if path not found
        """
        class_lower = character_class.lower()
        image_path = AssetService.CHARACTER_IMAGE_PATHS.get(class_lower)

        if image_path:
            print(f"✅ Character portrait found: {character_class} -> {image_path}")
            return cl.Image(
                name=f"{character_class.title()} Portrait",
                path=image_path,
                display=display,
                size=size,
            )
        else:
            print(f"❌ Character portrait NOT found for: '{character_class}' (tried: '{class_lower}')")
        return None

    @staticmethod
    def get_location_image(
        location_type: str, size: str = "large", display: str = "inline"
    ) -> cl.Image | None:
        """
        Get location/map image.

        Args:
            location_type: Type of location (tavern, dungeon, forest, etc.)
            size: Image size (small, medium, large)
            display: Display mode (inline, side, page)

        Returns:
            cl.Image element or None if path not found
        """
        location_lower = location_type.lower()
        image_path = AssetService.MAP_IMAGE_PATHS.get(location_lower)

        # Fallback mappings for scene types without specific images
        if not image_path:
            fallback_map = {
                "battle": "dungeon",
                "exploration": "forest",
            }
            fallback = fallback_map.get(location_lower)
            if fallback:
                print(f"🔄 Using fallback for '{location_type}': {fallback}")
                image_path = AssetService.MAP_IMAGE_PATHS.get(fallback)
                location_type = fallback  # Update name for display

        if image_path:
            print(f"✅ Location image found: {location_type} -> {image_path}")
            return cl.Image(
                name=f"{location_type.title()} Map",
                path=image_path,
                display=display,
                size=size,
            )
        else:
            print(f"❌ Location image NOT found for: '{location_type}' (tried: '{location_lower}')")
        return None

    @staticmethod
    def detect_scene_type(scene_description: str) -> str:
        """
        Detect scene type from description text.

        Args:
            scene_description: Description of the scene

        Returns:
            Scene type (tavern, dungeon, forest, etc.)
        """
        scene_lower = scene_description.lower()

        scene_keywords = {
            "tavern": ["tavern", "inn", "bar", "alehouse"],
            "dungeon": ["dungeon", "crypt", "tomb", "cave", "underground"],
            "forest": ["forest", "woods", "trees", "wilderness"],
            "town": ["town", "city", "village", "street"],
            "battle": ["battle", "combat", "fight", "arena"],
            "castle": ["castle", "fortress", "keep", "palace"],
        }

        for scene_type, keywords in scene_keywords.items():
            if any(keyword in scene_lower for keyword in keywords):
                print(f"🎬 Detected scene type: '{scene_type}' from: '{scene_description[:50]}...'")
                return scene_type

        print(f"🎬 Using default scene type: 'exploration' for: '{scene_description[:50]}...'")
        return "exploration"  # Default


# Singleton instance
asset_service = AssetService()
