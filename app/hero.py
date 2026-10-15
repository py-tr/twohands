"""Data for the Overview hero loop and the "300 pending" card. Everything is a real, measured read: the loop
replays the stored read of one form (fields filling in, identities turning green, the routed field turning red)."""
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


def pending_run(st: storemod.Store) -> dict | None:
    """The pre-registered 300-form run while it is not yet the headline: progress, not results."""
    hid = st.headline_run()
    if hid.startswith("calls_"):
        return None
    rid = next((k for k in st.runs if k.startswith("calls_") and "gemma" in k), None) or \
        next((k for k in st.runs if k.startswith("calls_")), None)
    target = 300
    if rid is None:
        return {"read": 0, "target": target, "pct": 0, "phase": "starting"}
    reads = st.runs[rid]["reads"].values()
    done = sum(1 for r in reads if r.error is None)
    phase = "eye-check" if done >= target else "reading"
    return {"read": done, "target": target, "pct": round(100 * min(done, target) / target), "phase": phase}
