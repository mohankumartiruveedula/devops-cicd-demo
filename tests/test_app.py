import pytest

import app as app_module


@pytest.fixture
def client():
    app_module.reset_store()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "UP"


def test_ready(client):
    assert client.get("/ready").status_code == 200


def test_index_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Task Manager" in r.data


def test_info(client):
    data = client.get("/api/info").get_json()
    assert data["app"] == "task-manager"
    assert "version" in data and "pod" in data


def test_create_and_list_task(client):
    r = client.post("/api/tasks", json={"title": "Learn Jenkins"})
    assert r.status_code == 201
    assert r.get_json()["title"] == "Learn Jenkins"
    tasks = client.get("/api/tasks").get_json()
    assert len(tasks) == 1


def test_create_task_requires_title(client):
    r = client.post("/api/tasks", json={"title": "  "})
    assert r.status_code == 400


def test_toggle_task(client):
    tid = client.post("/api/tasks", json={"title": "Write Dockerfile"}).get_json()["id"]
    r = client.put(f"/api/tasks/{tid}")
    assert r.get_json()["done"] is True


def test_delete_task(client):
    tid = client.post("/api/tasks", json={"title": "Deploy to K8s"}).get_json()["id"]
    assert client.delete(f"/api/tasks/{tid}").status_code == 204
    assert client.get("/api/tasks").get_json() == []


def test_missing_task_returns_404(client):
    assert client.put("/api/tasks/999").status_code == 404
    assert client.delete("/api/tasks/999").status_code == 404
