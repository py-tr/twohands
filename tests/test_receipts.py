"""Receipts (PROTOCOL_CORD.md): amount parsing, the identities on CORD's own labels, the gate, the frozen prompt.
No model call: the reader is exercised with a fake chat.

The three label examples are CORD v2 test receipts (naver-clova-ix/cord-v2, CC BY 4.0, Park et al. 2019),
gt_parse copied verbatim: test index 2 and 6 (consistent) and 71 (its labels violate paid - total = change)."""
import json

from PIL import Image

from twohands import receipts as R

CORD_2 = json.loads('{"menu": {"nm": "JASMINE MT ( L )", "cnt": "1", "price": "24,000", "sub": {"nm": "COCONUT JELLY ( L )", "price": "4,000"}}, "sub_total": {"subtotal_price": "28,000"}, "total": {"total_price": "28,000", "cashprice": "100,000", "changeprice": "72,000", "menuqty_cnt": "1"}}')
CORD_6 = json.loads('{"menu": [{"nm": "EGG TART", "cnt": "1", "price": "13,000"}, {"nm": "CHOCO CUS ARD PASTRY", "cnt": "2", "price": "24,000"}, {"nm": "REDBEAN BREAD", "cnt": "1", "price": "9,000"}], "total": {"total_price": "46,000", "cashprice": "50,000", "changeprice": "4,000"}}')
CORD_71 = json.loads('{"menu": {"nm": "Cuka Apel Tetes", "unitprice": "198000", "cnt": "1", "price": "198000"}, "total": {"total_price": "198000", "cashprice": "200200", "changeprice": "22000"}}')

FROZEN_PROMPT_SHA = "ff17bd8bb31bd5acee84da2f8182201440daa775407d8661b1368b35ef415e1c"


def by_name(ids):
    return {(r["name"], r.get("item")): r for r in ids}


def test_num_formats():
    cases = {"60.000": 60000, "24,000": 24000, "45,000.00": 45000, "9.500,00": 9500, "Rp. 111,000": 111000,
             "-2 600": -2600, "(0)": 0, "x2": 2, "2X": 2, "1.00xITEMs": 1, "[145,900]": 145900, "*46000": 46000,
             "@ 12.000": 12000, "1,944,000": 1944000, "5.455": 5455, "-": None, "": None, None: None, 300: 300}
    for s, want in cases.items():
        assert R.num(s) == want, s
    assert R.amount("-60.000") == 60000 and R.amount(["6,818", "0"]) == 6818 and R.amount(["100,000", "100,000"]) == 100000


def test_cord_2_identities_hold_with_addon_line():
    rec = R.from_cord(CORD_2)
    assert rec["items"][0]["subs"][0]["price"] == 4000 and rec["subtotal"] == 28000
    ids = by_name(R.identities(rec))
    assert ids[("line prices sum to subtotal", None)]["ok"] is True          # 24,000 + add-on 4,000
    assert ids[("subtotal + tax + service - discount = total", None)]["ok"] is True
    assert ids[("paid - total = change", None)]["ok"] is True               # 100,000 - 28,000 = 72,000
    assert not R.violations(rec, tol=None)


def test_cord_6_no_subtotal_so_line_sum_not_checkable():
    rec = R.from_cord(CORD_6)
    ids = by_name(R.identities(rec))
    assert ids[("line prices sum to subtotal", None)]["ok"] is None          # subtotal not printed
    assert ids[("paid - total = change", None)]["ok"] is True
    assert not R.violations(rec)


def test_cord_71_label_violates_change():
    rec = R.from_cord(CORD_71)
    v = R.violations(rec)
    assert [x["name"] for x in v] == ["paid - total = change"]
    assert (v[0]["lhs"], v[0]["rhs"]) == (2200, 22000)                      # a free finding, for the image to decide
    assert by_name(R.identities(rec))[("count x unit price = price", 0)]["ok"] is True


def test_tolerance_is_stated_and_used():
    rec = {"items": [], "subtotal": 26818, "tax": 2681, "total": 29500}      # rounding to the nearest 100
    assert R.violations(rec, tol=None) and not R.violations(rec)
    rec["total"] = 30500
    assert R.violations(rec)


def test_tax_included_alternative():
    rec = {"items": [{"name": "A", "price": 25000}], "subtotal": 25000, "tax": 2272, "total": 25000}
    assert by_name(R.identities(rec))[("subtotal + tax + service - discount = total", None)]["ok"] is True


def test_gate_accepts_consistent_read_and_lists_fields():
    read = {"items": [{"name": "JASMINE MT ( L )", "count": 1, "unit_price": None, "price": 24000, "discount": None,
                       "subs": [{"name": "COCONUT JELLY ( L )", "count": None, "price": 4000}]}],
            "subtotal": 28000, "tax": None, "service": None, "discount": None, "total": 28000, "cash": 100000,
            "card": None, "emoney": None, "change": 72000}
    g = R.gate(read)
    assert set(g["accepted_fields"]) >= {"items[0].price", "items[0].subs[0].price", "subtotal", "total", "cash", "change"}
    assert g["unverified_fields"] == ["items[0].count"]                      # count with no unit price: no identity
    assert not g["accepted"] and g["reasons"] == ["1 amount(s) in no identity that held"]
    read["items"][0]["count"] = None
    assert R.gate(read)["accepted"]


def test_gate_routes_on_failed_identity_and_unparsed():
    read = R.from_cord(CORD_71)
    g = R.gate(read)
    assert g["routed"] and g["accepted_fields"] == [] and "paid - total = change" in g["reasons"][0]
    assert R.gate(None)["reasons"] == ["no parseable read"]
    assert R.gate({"values": []})["routed"]


def test_scoring_stub():
    lab = R.from_cord(CORD_71)
    read = json.loads(json.dumps(lab))
    read["change"] = 2200                                                    # the model reads what the paper says
    g = R.gate(read)
    pairs = R.field_pairs(read, lab)
    d = R.disagreements(read, lab)
    assert [p["field"] for p in d] == ["change"]
    s = R.score([{"gate": g, "pairs": pairs, "verdicts": {"change": "model_right"}}])
    assert s["label_errors_found"] == 1 and s["accepted_field_errors"] == 0


def test_align_items_by_name_when_counts_differ():
    a = [{"name": "EGG TART"}, {"name": "REDBEAN BREAD"}]
    b = [{"name": "EGG TART"}, {"name": "CHOCO"}, {"name": "REDBEAN BREAD"}]
    assert R.align_items(a, b) == [(0, 0), (None, 1), (1, 2)]


def test_crop_box_scales_from_meta():
    gt = {"meta": {"image_size": {"width": 100, "height": 200}},
          "valid_line": [{"category": "total.total_price", "words": [
              {"quad": {"x1": 10, "y1": 20, "x2": 30, "y2": 20, "x3": 30, "y3": 40, "x4": 10, "y4": 40}}]}]}
    assert R.crop_box(gt, "total.total_price", image_size=(200, 400), pad=0) == (20, 40, 60, 80)
    assert R.crop_box(gt, "total.cashprice") is None


def test_prompt_frozen_and_body_without_model_call():
    assert R.prompt_sha256() == FROZEN_PROMPT_SHA
    img = Image.new("RGB", (400, 1400), "white")
    assert len(R.tiles(img)) == 3 and R.tiles(Image.new("RGB", (400, 500))) == []
    seen = {}

    def fake_chat(body):
        seen["body"] = body
        return {"choices": [{"message": {"content": json.dumps(R.from_cord(CORD_2))}, "finish_reason": "stop"}],
                "usage": {}}, 1
    row = R.read("gemma", img, chat=fake_chat)
    b = seen["body"]
    assert b["temperature"] == 0 and "response_format" not in b and b["model"] == "Gemma-4-31B-IT"
    assert len(b["messages"][1]["content"]) == 1 + 3 + 1
    assert R.coerce(row["parsed"])["total"] == 28000 and row["prompt_sha256"] == FROZEN_PROMPT_SHA
