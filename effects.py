# Voice effects database with Voicemod API effects [citation:9]

VOICE_EFFECTS = {
    "robot": {
        "name": "🤖 Robot",
        "description": "Metallic, mechanical voice",
        "api_name": "robot"
    },
    "alien": {
        "name": "👽 Alien",
        "description": "Extraterrestrial, otherworldly voice",
        "api_name": "alien"
    },
    "helium": {
        "name": "🎈 Helium",
        "description": "High-pitched, squeaky voice",
        "api_name": "helium"
    },
    "demon": {
        "name": "😈 Demon",
        "description": "Deep, evil-sounding voice",
        "api_name": "demon"
    },
    "baby": {
        "name": "🍼 Baby",
        "description": "Child-like, cute voice",
        "api_name": "baby"
    },
    "monster": {
        "name": "👹 Monster",
        "description": "Growling, beast-like voice",
        "api_name": "monster"
    },
    "ghost": {
        "name": "👻 Ghost",
        "description": "Ethereal, spooky voice",
        "api_name": "ghost"
    },
    "zombie": {
        "name": "🧟 Zombie",
        "description": "Undead, groaning voice",
        "api_name": "zombie"
    },
    "cathedral": {
        "name": "⛪ Cathedral",
        "description": "Reverberant, echoing voice",
        "api_name": "cathedral"
    },
    "telephone": {
        "name": "📞 Telephone",
        "description": "Vintage phone sound",
        "api_name": "telephone"
    },
    "radio": {
        "name": "📻 Radio",
        "description": "AM radio broadcast effect",
        "api_name": "radio"
    },
    "megaphone": {
        "name": "📢 Megaphone",
        "description": "Loudspeaker announcement",
        "api_name": "megaphone"
    },
    "underwater": {
        "name": "💧 Underwater",
        "description": "Muffled, submerged voice",
        "api_name": "underwater"
    },
    "chipmunk": {
        "name": "🐿️ Chipmunk",
        "description": "Fast, high-pitched voice",
        "api_name": "chipmunk"
    },
    "slow": {
        "name": "🐢 Slow",
        "description": "Slowed down speech",
        "api_name": "slow"
    },
    "fast": {
        "name": "⚡ Fast",
        "description": "Sped up speech",
        "api_name": "fast"
    },
    "echo": {
        "name": "🔄 Echo",
        "description": "Repeating, fading effect",
        "api_name": "echo"
    },
    "vibrato": {
        "name": "🎵 Vibrato",
        "description": "Wavering pitch effect",
        "api_name": "vibrato"
    },
    "tremolo": {
        "name": "🌊 Tremolo",
        "description": "Volume oscillation effect",
        "api_name": "tremolo"
    },
    "reverse": {
        "name": "⏪ Reverse",
        "description": "Backwards speech",
        "api_name": "reverse"
    }
}

# Default effect when none is selected
DEFAULT_EFFECT = "magic-chords"

# User preferences storage (in-memory, resets on restart)
# For production, use a database like SQLite or Redis
user_preferences = {}

def get_all_effects():
    """Return list of all available effects"""
    return list(VOICE_EFFECTS.keys())

def get_effect(effect_name):
    """Get effect details by name"""
    return VOICE_EFFECTS.get(effect_name)

def get_user_effect(user_id):
    """Get user's preferred effect"""
    return user_preferences.get(str(user_id), DEFAULT_EFFECT)

def set_user_effect(user_id, effect_name):
    """Set user's preferred effect"""
    if effect_name in VOICE_EFFECTS or effect_name == DEFAULT_EFFECT:
        user_preferences[str(user_id)] = effect_name
        return True
    return False
