"""추천의 데이터 근거·권한·삭제·실제 GLB 연결을 검증한다."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_garments import account, create, payload
from test_generation import queue

from app.core.config import Settings
from app.main import create_app
from app.models import Garment, Recommendation, StylePreference
from app.schemas.recommendations import StylePreferences
from app.services import auth
from app.services.generation import run_once
from app.services.recommendation_rules import (
    WEIGHTS,
    item_context,
    measured,
    rank_combinations,
    signature,
)


@pytest.fixture
def client():
    auth._attempts.clear()
    with TestClient(
        create_app(Settings(_env_file=None, database_url="sqlite:///:memory:"))
    ) as instance:
        yield instance


def wardrobe(client, headers, tops=2, bottoms=2, outer=True):
    result = []
    for part, count, kind in (
        ("top", tops, "티셔츠"),
        ("bottom", bottoms, "청바지"),
        ("outer", int(outer), "재킷"),
    ):
        for index in range(count):
            body = payload()
            body["info"].update(
                name=f"{kind} {index}",
                category=part,
                garment_type=kind,
                color="검정" if index else "흰색",
            )
            response = create(client, headers, body)
            assert response.status_code == 201, response.text
            result.append(response.json())
    return result


def generate(client, headers, **body):
    response = client.post("/api/v1/recommendations", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()["items"]


def test_preferences_revision_validation_and_isolation(client):
    alice, bob = account(client, "pref_owner"), account(client, "pref_other")
    uri = "/api/v1/style-preferences"
    assert client.get(uri).status_code == 401
    defaults = client.get(uri, headers=alice).json()
    assert defaults["revision"] == 0 and defaults["styles"] == []
    saved = client.put(
        uri,
        headers=alice,
        json={**defaults, "styles": ["minimal", "casual"], "preferred_colors": ["흰색"]},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1
    assert client.put(uri, headers=alice, json=defaults).status_code == 409
    updated = client.put(uri, headers=alice, json={**saved.json(), "fit": "regular"})
    assert updated.json()["revision"] == 2
    assert client.get(uri, headers=bob).json()["styles"] == []
    assert (
        client.put(uri, headers=alice, json={**defaults, "styles": ["invented"]}).status_code == 400
    )
    assert client.put(uri, headers=alice, json={**defaults, "user_id": "forged"}).status_code == 400


@pytest.mark.parametrize(
    "tops,bottoms,outer,expected",
    [(0, 0, False, 0), (1, 0, True, 0), (1, 1, False, 1), (1, 1, True, 2), (2, 2, True, 5)],
)
def test_only_real_wardrobe_combinations_and_shortage(client, tops, bottoms, outer, expected):
    headers = account(client, "combinations")
    clothes = wardrobe(client, headers, tops, bottoms, outer)
    rows = generate(client, headers, count=5)
    assert len(rows) == expected
    keys = {signature(row["slots"]) for row in rows}
    assert len(keys) == expected
    own_ids = {item["id"] for item in clothes}
    for row in rows:
        assert set(row["slots"].values()) <= own_ids
        assert {"top", "bottom"} <= set(row["slots"])
        assert not row["fitting_available"]
        assert not row["body_used"]
        assert "internal_score" not in row
        for item in row["items"]:
            assert any(item["name"] in reason for reason in row["reasons"])
    assert len({row["slots"]["top"] for row in rows}) == min(tops, expected) if expected else True


def test_feedback_save_history_private_preview_and_delete(client):
    alice, bob = account(client, "rec_owner"), account(client, "rec_other")
    wardrobe(client, alice)
    row = generate(client, alice)[0]
    uri = f"/api/v1/recommendations/{row['id']}"
    for method, path, body in [
        ("get", uri, None),
        ("post", uri + "/save", None),
        ("post", uri + "/feedback", {"feedback": "like"}),
        ("post", uri + "/apply", {}),
        ("get", uri + "/preview/top", None),
        ("delete", uri, None),
    ]:
        assert (
            getattr(client, method)(
                path, headers=bob, **({"json": body} if body is not None else {})
            ).status_code
            == 404
        )
    assert client.get(uri).status_code == 401
    assert client.get("/api/v1/recommendations", headers=bob).json() == []
    image = client.get(uri + "/preview/top", headers=alice)
    assert image.status_code == 200 and image.content.startswith(b"\x89PNG")
    assert image.headers["cache-control"] == "no-store"
    assert client.post(uri + "/apply", headers=alice, json={}).status_code == 409
    assert client.post(uri + "/save", headers=alice).json()["saved_at"]
    assert len(client.get("/api/v1/recommendations?saved_only=true", headers=alice).json()) == 1
    assert (
        client.post(uri + "/feedback", headers=alice, json={"feedback": "exclude"}).status_code
        == 200
    )
    assert signature(row["slots"]) not in {
        signature(item["slots"]) for item in generate(client, alice, count=5)
    }
    assert (
        client.post(uri + "/feedback", headers=alice, json={"feedback": "none"}).status_code == 200
    )
    assert signature(row["slots"]) in {
        signature(item["slots"]) for item in generate(client, alice, count=5)
    }
    assert client.delete(uri, headers=alice).status_code == 204
    assert client.get(uri, headers=alice).status_code == 404


@pytest.mark.parametrize("change", ["rights", "delete", "edit"])
def test_current_rights_deletion_and_edit_invalidate_cached_recommendation(client, change):
    headers = account(client, "stale_rec")
    wardrobe(client, headers, 1, 1, False)
    row = generate(client, headers)[0]
    garment_id = row["slots"]["top"]
    if change == "delete":
        assert client.delete(f"/api/v1/garments/{garment_id}", headers=headers).status_code == 204
    elif change == "rights":
        assert (
            client.post(
                f"/api/v1/garments/{garment_id}/rights-withdraw", headers=headers, json={}
            ).status_code
            == 204
        )
    else:
        with client.app.state.session_factory() as db:
            garment = db.get(Garment, garment_id)
            garment.data = {**garment.data, "color": "빨강"}
            garment.revision += 1
            db.commit()
    uri = f"/api/v1/recommendations/{row['id']}"
    state = client.get(uri, headers=headers).json()
    assert not state["available"] and state["reasons"] == []
    assert client.post(uri + "/save", headers=headers).status_code == 409
    assert client.post(uri + "/apply", headers=headers, json={}).status_code == 409
    assert client.get(uri + "/preview/top", headers=headers).status_code == 404
    if change != "edit":
        assert generate(client, headers) == []


def test_real_glb_apply_pins_model_change_and_owned_mannequin(client):
    alice, bob = account(client, "apply_owner"), account(client, "apply_other")
    clothes = wardrobe(client, alice, 1, 1, True)
    for item in clothes:
        assert queue(client, alice, item).status_code == 202
        assert run_once(client.app.state.session_factory)
    rows = generate(client, alice)
    row = next(row for row in rows if "outer" in row["slots"])
    assert row["fitting_available"]
    uri = f"/api/v1/recommendations/{row['id']}/apply"
    applied = client.post(uri, headers=alice, json={}).json()
    assert applied["slots"] == row["slots"] and len(applied["pins"]) == 3
    fitting = client.post(
        "/api/v1/fittings",
        headers=alice,
        json={
            "body_storage_consent": True,
            "mannequin": {"mode": "manual", "values": {"height": 175}},
            "slots": applied["slots"],
        },
    ).json()
    mannequin_id = fitting["mannequin_id"]
    assert (
        client.post(uri, headers=alice, json={"mannequin_id": mannequin_id}).json()["mannequin"][
            "values"
        ]["height"]
        == 175
    )
    assert (
        client.post(
            "/api/v1/recommendations",
            headers=bob,
            json={"mannequin_id": mannequin_id, "body_processing_consent": True},
        ).status_code
        == 404
    )
    assert queue(client, alice, clothes[0]).status_code == 202
    assert run_once(client.app.state.session_factory)
    assert client.post(uri, headers=alice, json={}).status_code == 409


def test_body_consent_units_unknowns_sources_and_account_cascade(client):
    headers = account(client, "body_rec")
    clothes = wardrobe(client, headers, 1, 1, False)
    with client.app.state.session_factory() as db:
        garment = db.get(Garment, clothes[0]["id"])
        garment.data = {
            **garment.data,
            "measurements": [
                {
                    "label": "가슴단면",
                    "value": 500,
                    "unit": "mm",
                    "kind": "flat",
                    "target": "garment",
                    "source": "user_entered",
                }
            ],
        }
        db.commit()
    body = {"mode": "photo", "values": {"chest": 90}, "origins": {"chest": "estimated"}}
    assert (
        client.post("/api/v1/recommendations", headers=headers, json={"body": body}).status_code
        == 400
    )
    row = generate(client, headers, body=body, body_processing_consent=True)[0]
    assert row["body_used"] and any("+10.0cm" in note and "추정값" in note for note in row["notes"])
    with client.app.state.session_factory() as db:
        details = db.get(Recommendation, row["id"]).details
        assert "values" not in details and "body" not in details
    assert client.put("/api/v1/style-preferences", headers=headers, json={}).status_code == 200
    assert (
        client.request(
            "DELETE",
            "/api/v1/auth/account",
            headers=headers,
            json={"username": "body_rec", "password": "correct-horse-battery"},
        ).status_code
        == 204
    )
    with client.app.state.session_factory() as db:
        for model in (Recommendation, StylePreference):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_score_evidence_feedback_diversity_and_avoid_colors():
    prefs = StylePreferences(styles=["minimal"], fit="regular").model_dump()
    items = []
    for part, ids in (("top", ("a", "b")), ("bottom", ("c", "d"))):
        for garment_id in ids:
            info = {
                "garment_type": "티셔츠" if part == "top" else "슬랙스",
                "color": "흰색",
                "fit": "레귤러",
            }
            context, notes, palette = item_context(info, prefs, None)
            items.append(
                {
                    "id": garment_id,
                    "category": part,
                    "info": info,
                    "context": context,
                    "notes": notes,
                    "palette": palette,
                }
            )
    rows, _ = rank_combinations(items, prefs, None, {}, 4)
    assert sum(WEIGHTS.values()) == pytest.approx(1)
    assert rows[0]["score"] == pytest.approx(
        sum(WEIGHTS[k] * v for k, v in rows[0]["components"].items())
    )
    assert rows[0]["slots"]["top"] != rows[1]["slots"]["top"]
    last = signature(rows[-1]["slots"])
    liked, _ = rank_combinations(items, prefs, None, {last: "like"}, 4)
    assert signature(liked[0]["slots"]) == last
    disliked, _ = rank_combinations(items, prefs, None, {last: "dislike"}, 4)
    assert signature(disliked[0]["slots"]) != last
    assert rank_combinations(items, {**prefs, "avoided_colors": ["화이트"]}, None, {}, 4)[0] == []
    assert (
        measured(
            {
                "measurements": [
                    {
                        "label": "가슴단면",
                        "value": 50,
                        "kind": "flat",
                        "unit": "cm",
                        "target": "body",
                    }
                ]
            },
            {"가슴단면"},
            "flat",
        )
        is None
    )
    assert (
        measured(
            {
                "size": "M",
                "measurements": [
                    {
                        "label": "가슴단면",
                        "size": "L",
                        "value": 50,
                        "kind": "flat",
                        "unit": "cm",
                        "target": "garment",
                    }
                ],
            },
            {"가슴단면"},
            "flat",
        )
        is None
    )
