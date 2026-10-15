"""Data for the Overview hero loop and the receipt it ends on. Everything is real: the loop replays the stored read of
one form (fields filling in, identities turning green, the routed field turning red), then ends on a red card: the crop
of a field the model read right and the first capture mis-keyed, confirmed by the certified count."""
from __future__ import annotations

from app import store as storemod
from app.crops import field_boxes

HERO_FORM = "211294C0100"   # phone photo; every value right, but TOTAL digits 262 vs words 162 -> routed
FRAME_X = 0.66               # the frame shows the page left of the privacy mask (mask starts at x = 0.657)


def loop_data(st: storemod.Store) -> dict | None:
    r = st.default_read(HERO_FORM)
    if r is None or st.masked_image(HERO_FORM) is None:
        return None
    ev = storemod.evaluate(r)
    boxes = field_boxes(storemod.schema())
    fields = []
    for f in ev["fields"]:
        b = boxes.get(f["key"])
        if b is None:
            continue
        x0, y0, x1, y1 = b
        fields.append({"code": f["code"], "name": f["name"], "n": f["n"], "w": f["w"], "ok": f["status"] == "ok",
                       "msg": f["msg"] if f["status"] != "ok" else "",
                       "box": [round(100 * x0 / FRAME_X, 2), round(100 * y0, 2),
                               round(100 * (min(x1, FRAME_X) - x0) / FRAME_X, 2), round(100 * (y1 - y0), 2)]})
    # the order a reader's eye takes: the vote rows top to bottom, TOTAL, then the left-hand sections
    order = {c: i for i, c in enumerate([f"OPT{i:02d}" for i in range(1, 16)] + ["NO_REGISTRADAS", "NULOS", "TOTAL",
                                         "SACADOS", "SOBRANTES", "VOTARON", "REPRESENTANTES", "PERSONAS_Y_REP"])}
    fields.sort(key=lambda f: order.get(f["code"], 99))
    wd = [f for f in ev["fields"] if f["status"] == "words"]
    idents = [{"name": i["name"], "ok": i["ok"], "lhs": i["lhs"], "rhs": i["rhs"]} for i in ev["identities"]]
    idents.append({"name": "words = digits on every field", "ok": not wd,
                   "lhs": len(ev["fields"]) - len(wd), "rhs": len(ev["fields"]), "count": True})
    return storemod.public({"clave": HERO_FORM, "fields": fields, "identities": idents, "accepted": ev["accepted"],
                            "line": ev["line"], "img": f"/masked/{HERO_FORM}.jpg",
                            "secs": r.secs, "model": st.runs[r.run_id].get("model")})


def receipt(st: storemod.Store, H: dict) -> dict | None:
    """The red card the hero ends on: one capture error from the pre-registered run, with its crop and its proof."""
    rc = (H or {}).get("receipt")
    if not rc:
        return None
    code = storemod.code_of(rc["field"])
    has = st.masked_image(rc["clave"]) is not None
    return {"clave": rc["clave"], "code": code, "name": storemod.name_of(rc["field"]), "paper": rc["paper"],
            "prep": rc["prep"], "certified": rc["certified"], "mode": rc["cert_mode"], "model": rc["model"],
            "img": f"/crop/{rc['clave']}/{code}.jpg?pad=0.012&label=0" if has else None}
