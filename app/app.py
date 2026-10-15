import os
import socket
from datetime import datetime, timezone

from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "dev")
BUILD_NUMBER = os.getenv("BUILD_NUMBER", "local")

tasks = []
_next_id = 1


def reset_store():
    global tasks, _next_id
    tasks = []
    _next_id = 1


@app.route("/")
def index():
    return render_template(
        "index.html",
        version=APP_VERSION,
        build=BUILD_NUMBER,
        hostname=socket.gethostname(),
    )


@app.route("/health")
def health():
    return jsonify(status="UP"), 200


@app.route("/ready")
def ready():
    return jsonify(status="READY"), 200


@app.route("/api/info")
def info():
    return jsonify(
        app="task-manager",
        version=APP_VERSION,
        build=BUILD_NUMBER,
        pod=socket.gethostname(),
        time=datetime.now(timezone.utc).isoformat(),
    )


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    global _next_id
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400
    task = {"id": _next_id, "title": title, "done": False}
    _next_id += 1
    tasks.append(task)
    return jsonify(task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def toggle_task(task_id):
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = not t["done"]
            return jsonify(t)
    return jsonify(error="task not found"), 404


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    for i, t in enumerate(tasks):
        if t["id"] == task_id:
            tasks.pop(i)
            return "", 204
    return jsonify(error="task not found"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
