def test_create_list_delete(client):
    created = client.post("/api/notes", json={"title": "First", "body": "hello"})
    assert created.status_code == 201
    note = created.json()
    assert [n["title"] for n in client.get("/api/notes").json()] == ["First"]

    assert client.delete(f"/api/notes/{note['id']}").status_code == 204
    assert client.get("/api/notes").json() == []


def test_missing_note_is_a_404_with_the_error_shape(client):
    res = client.delete("/api/notes/999")
    assert res.status_code == 404
    assert res.json() == {"error": {"code": "not_found", "message": "Note 999 not found"}}


def test_title_is_required(client):
    assert client.post("/api/notes", json={"title": ""}).status_code == 422
