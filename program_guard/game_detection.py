"""Detección heurística de videojuegos."""

from __future__ import annotations

KNOWN_GAME_EXES = {
    "steam.exe",
    "steamwebhelper.exe",
    "epicgameslauncher.exe",
    "robloxplayerbeta.exe",
    "roblox.exe",
    "minecraftlauncher.exe",
    "javaw.exe",
    "fortniteclient-win64-shipping.exe",
    "valorant-win64-shipping.exe",
    "valorant.exe",
    "r5apex.exe",
    "cs2.exe",
    "csgo.exe",
    "dota2.exe",
    "league of legends.exe",
    "leagueclient.exe",
    "gta5.exe",
    "rdr2.exe",
    "overwatch.exe",
    "battle.net.exe",
    "origin.exe",
    "eadesktop.exe",
    "ubisoftconnect.exe",
    "goggalaxy.exe",
    "playnite.exe",
    "rpcs3.exe",
    "yuzu.exe",
    "ryujinx.exe",
    "fivem.exe",
    "rocketleague.exe",
}

GAME_PATH_HINTS = (
    "steam",
    "epic games",
    "riot games",
    "battle.net",
    "ubisoft",
    "origin games",
    "electronic arts",
    "xboxgames",
    "minecraft",
    "roblox",
    "valorant",
    "fortnite",
)


def is_likely_game(exe_name: str, exe_path: str = "", tagged: set[str] | None = None) -> bool:
    exe = exe_name.lower()
    if tagged and exe in tagged:
        return True
    if exe in KNOWN_GAME_EXES:
        return True
    path = (exe_path or "").lower()
    return any(hint in path for hint in GAME_PATH_HINTS)
