"""Spot-check that B/C-resolved receiver calls point to the correct class file."""
from collections import defaultdict
from validate_calls import build

PROJECT = r"C:\Users\lenov\projects\Tcheck-Games"
files, resolver, graph = build(PROJECT)

# receiver prefix -> expected callee file fragment
EXPECT = {
    "card.": "models/card.py",
    "deck.": "models/deck.py",
    "game_state.": "models/game_state.py",
    "hand.": "models/player_hand.py",
    "player_hand.": "models/player_hand.py",
    "room.": "models/game_room.py",
    "player.": "models/player.py",
}

ok = bad = 0
bad_rows = []
for caller_id, edges in graph._by_caller.items():
    for edge in edges:
        if edge.resolution not in ("LOCAL", "IMPORTED") or not edge.callee_node_id:
            continue
        site = resolver._node_index.get(edge.call_site_node_id)
        callee = resolver._node_index.get(edge.callee_node_id)
        if not site or not callee:
            continue
        name = (site.name or "").strip()
        for prefix, expect_file in EXPECT.items():
            if name.startswith(prefix):
                callee_file = callee.file_rel_path.replace("\\", "/")
                if callee_file == expect_file:
                    ok += 1
                else:
                    bad += 1
                    bad_rows.append(f"  {name}  ->  {callee_file}  (expected {expect_file})  @ {site.file_rel_path}:{site.start_line}")
                break

print(f"receiver-typed calls correct: {ok}")
print(f"receiver-typed calls WRONG  : {bad}")
for r in bad_rows[:40]:
    print(r)
