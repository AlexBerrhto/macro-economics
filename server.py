import random
import socketio
import uvicorn

# Initialize Socket.IO server with CORS enabled for cross-origin mobile access
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio)

# Server-Side Game State
game_state = {
    "started": False,
    "players": [],  # List of player dicts
    "activeIdx": 0,
    "sectorPrices": {
        "Agriculture": 50,
        "Fisheries": 25,
        "Mining": 25,
        "Manufacturing": 45,
        "Construction": 35,
        "Energy": 20,
        "Healthcare": 40,
        "Education": 35,
        "Logistics": 25,
        "R_and_D": 45,
        "IT_AI": 35,
        "Aerospace": 20,
        "Defense": 40,
        "Welfare": 35,
        "Climate": 25,
    },
    "sectorLeaders": {},
}


@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")


@sio.event
async def join_room(sid, data):
    player_name = data.get("name", f"Player {len(game_state['players']) + 1}")

    # Prevent duplicate joins if match already started
    if game_state["started"]:
        await sio.emit(
            "error_msg",
            {"message": "Game already in progress!"},
            to=sid,
        )
        return

    # Add new player
    new_player = {
        "sid": sid,
        "id": len(game_state["players"]),
        "name": player_name,
        "cash": 1500,
        "pts": 0,
        "pos": 0,
        "cards": {sec: 0 for sec in game_state["sectorPrices"]},
        "sectorPts": {sec: 0 for sec in game_state["sectorPrices"]},
        "active": True,
    }
    game_state["players"].append(new_player)

    print(f"{player_name} joined. Total players: {len(game_state['players'])}")

    # Broadcast updated room state to all clients
    await sio.emit("room_update", game_state)


@sio.event
async def start_online_game(sid, data):
    if len(game_state["players"]) < 2:
        await sio.emit(
            "error_msg",
            {"message": "Need at least 2 players to start!"},
            to=sid,
        )
        return

    game_state["started"] = True
    game_state["activeIdx"] = 0
    await sio.emit("game_started", game_state)


@sio.event
async def execute_turn(sid, data):
    active_player = game_state["players"][game_state["activeIdx"]]

    # Validate turn ownership
    if active_player["sid"] != sid:
        await sio.emit("error_msg", {"message": "Not your turn!"}, to=sid)
        return

    nudge = data.get("nudge", 0)
    if nudge != 0:
        active_player["cash"] -= 100

    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    total_steps = d1 + d2 + nudge

    # Move player
    active_player["pos"] = (active_player["pos"] + total_steps) % 40
    active_player["cash"] += 150  # Turn stipend

    # Rotate active player
    game_state["activeIdx"] = (game_state["activeIdx"] + 1) % len(
        game_state["players"]
    )

    # Broadcast updated state & roll details
    await sio.emit(
        "turn_executed",
        {"dice_result": f"{d1}+{d2} + ({nudge}) = {total_steps}", "state": game_state},
    )


@sio.event
async def buy_card(sid, data):
    sec = data.get("sector")
    player = next((p for p in game_state["players"] if p["sid"] == sid), None)

    if player and player["cash"] >= game_state["sectorPrices"][sec]:
        player["cash"] -= game_state["sectorPrices"][sec]
        player["cards"][sec] += 1
        await sio.emit("state_sync", game_state)


@sio.event
async def disconnect(sid):
    game_state["players"] = [
        p for p in game_state["players"] if p["sid"] != sid
    ]
    await sio.emit("room_update", game_state)


if __name__ == "__main__":
    # Run server on all interfaces at port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)