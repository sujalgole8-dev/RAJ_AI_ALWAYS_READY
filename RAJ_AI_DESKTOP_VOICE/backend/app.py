"""Local Flask server for the RAJ AI Windows assistant."""
from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS

from commands import execute_command
from voice import voice_engine

app = Flask(__name__)
CORS(app)


@app.get("/health")
def health():
    return jsonify({"healthy": True, "assistant": "RAJ"})


@app.get("/status")
def status():
    return jsonify({"online": True, "assistant": "RAJ", "voice": voice_engine.status()})


@app.get("/voice/status")
def voice_status():
    return jsonify(voice_engine.status())


@app.post("/voice/start")
def voice_start():
    payload = request.get_json(silent=True) or {}
    always = bool(payload.get("always", False))
    voice_engine.start(always=always)
    return jsonify({"success": True, **voice_engine.status()})


@app.post("/voice/stop")
def voice_stop():
    voice_engine.stop()
    return jsonify({"success": True, **voice_engine.status()})


@app.post("/command")
def command():
    payload = request.get_json(silent=True) or {}
    raw_command = payload.get("command", "")
    if not isinstance(raw_command, str):
        return jsonify({"success": False, "message": "Command must be text.", "action": "invalid"}), 400
    try:
        return jsonify(execute_command(raw_command))
    except Exception:
        app.logger.exception("Unhandled command error")
        return jsonify({"success": False, "message": "RAJ encountered a problem.", "action": "error"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
