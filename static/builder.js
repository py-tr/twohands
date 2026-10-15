/* Two Hands schema builder: draw boxes on a blank form, write identities, save as the engine's YAML, test live. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const root = $("bd");
  if (!root) return;
  const SAMPLES = JSON.parse(root.dataset.samples || "[]");
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const r4 = (v) => Math.round(v * 10000) / 10000;

  let S = blankState();
  let sampleId = null;
  let tool = "select";
  let sel = null;            // {kind: field|words|mask|marker|tile, i}
  let validateTimer = null;

  function blankState() {
    return { form: "", title: "", size: null, whole_image: true, markers: [], mask: [], tiles: [], fields: [], identities: [], keep: {} };
  }

  // ------------------------------------------------------------------ loading
  async function loadSample(id) {
    const r = await fetch("/api/builder/sample/" + id);
    if (!r.ok) return hint("Could not load the sample.", true);
    const d = await r.json();
    sampleId = id;
    S = d.state;
    setImage(d.blank);
    $("bd-samplenote").textContent = (d.tag === "synthetic sample" ? "Synthetic sample: a generated timesheet, not a real document. " : "") + (d.note || "");
    renderTestPicks(d.filled || []);
    $("bd-stored").hidden = id !== "ine";
    document.querySelectorAll("[data-sample]").forEach((b) => b.classList.toggle("on", b.dataset.sample === id));
    clearResults();
    syncInputs();
    renderAll();
    hint(id === "ine" ? "Our real schema: 23 fields, the privacy mask, four corner markers and six tiles. Select any box, or edit and save." :
      "A complete example: 8 fields with words boxes, the signature line as the mask. Edit it, or save and test it.");
  }

  function setImage(src) {
    const img = $("bd-img");
    img.src = src;
    $("bd-empty").hidden = true;
    $("bd-stage").classList.add("has");
  }

  $("bd-blank").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const url = URL.createObjectURL(f);
    const probe = new Image();
    probe.onload = () => {
      const k = Math.min(1, 2400 / Math.max(probe.naturalWidth, probe.naturalHeight));
      S = blankState();
      S.size = [Math.round(probe.naturalWidth * k), Math.round(probe.naturalHeight * k)];
      const stem = f.name.replace(/\.[^.]+$/, "");
      S.form = stem.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 40) || "my_form";
      S.title = stem;
      sampleId = null;
      setImage(url);
      $("bd-samplenote").textContent = "Your blank form stays in this browser; only the schema (boxes and identities) is saved.";
      renderTestPicks([]);
      $("bd-stored").hidden = true;
      document.querySelectorAll("[data-sample]").forEach((b) => b.classList.remove("on"));
      clearResults();
      syncInputs();
      renderAll();
      setTool("field");
      hint("Drag over the first digits box. Then name the field in the list.");
    };
    probe.src = url;
  });
  document.querySelectorAll("[data-sample]").forEach((b) => b.addEventListener("click", () => loadSample(b.dataset.sample)));

  // ------------------------------------------------------------------ tools
  function setTool(t) {
    tool = t;
    document.querySelectorAll(".bd-tool[data-tool]").forEach((b) => b.classList.toggle("on", b.dataset.tool === t));
    $("bd-stage").dataset.tool = t;
    const msg = {
      select: "Select a box to highlight it; Delete removes it.",
      field: "Drag over a field's digit boxes. A new field is added at the end of the list.",
      words: "Drag over the words for the selected field.",
      mask: "Drag over names, signatures or any personal data: it is blacked out before the page is stored or read.",
      marker: "Drag over each of the four black corner markers.",
      tile: "Drag a strip that the model should also see zoomed in.",
    }[t];
    hint(msg);
  }
  document.querySelectorAll(".bd-tool[data-tool]").forEach((b) => b.addEventListener("click", () => setTool(b.dataset.tool)));
  $("bd-del").addEventListener("click", deleteSel);
  document.addEventListener("keydown", (e) => {
    if ((e.key === "Delete" || e.key === "Backspace") && sel && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
      e.preventDefault();
      deleteSel();
    }
  });

  function hint(msg, bad) {
    const h = $("bd-hint");
    h.textContent = msg || "";
    h.classList.toggle("bad", !!bad);
  }

  // ------------------------------------------------------------------ drawing
  const stage = $("bd-stage");
  let drag = null;
  function frac(e) {
    const r = $("bd-img").getBoundingClientRect();
    return [Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))];
  }
  stage.addEventListener("pointerdown", (e) => {
    if (!S.size || tool === "select" || e.button > 0) return;
    if (tool === "words" && (!sel || sel.kind !== "field")) return hint("Select a field first (click it in the list), then draw its words.", true);
    if (tool === "marker" && S.markers.length >= 4) return hint("Four corner markers are drawn; delete one first.", true);
    e.preventDefault();
    stage.setPointerCapture(e.pointerId);
    const p = frac(e);
    const el = document.createElement("div");
    el.className = "bx k-" + (tool === "field" ? "field" : tool) + " drawing";
    $("bd-layer").appendChild(el);
    drag = { p0: p, p1: p, el };
    place(el, [p[0], p[1], p[0], p[1]]);
  });
  stage.addEventListener("pointermove", (e) => {
    if (!drag) return;
    drag.p1 = frac(e);
    place(drag.el, norm(drag.p0, drag.p1));
  });
  const endDrag = () => {
    if (!drag) return;
    const b = norm(drag.p0, drag.p1).map(r4);
    drag.el.remove();
    drag = null;
    if (b[2] - b[0] < 0.004 || b[3] - b[1] < 0.004) return hint("That box is too small; drag a rectangle.", true);
    addBox(b);
  };
  stage.addEventListener("pointerup", endDrag);
  stage.addEventListener("pointercancel", () => { if (drag) { drag.el.remove(); drag = null; } });

  function norm(a, b) { return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])]; }
  function place(el, b) {
    el.style.left = b[0] * 100 + "%"; el.style.top = b[1] * 100 + "%";
    el.style.width = (b[2] - b[0]) * 100 + "%"; el.style.height = (b[3] - b[1]) * 100 + "%";
  }

  function addBox(b) {
    if (tool === "field") {
      let n = S.fields.length + 1;
      const keys = new Set(S.fields.map((f) => f.key));
      while (keys.has("FIELD_" + n)) n++;
      S.fields.push({ key: "FIELD_" + n, type: "integer", label: { keywords: [] }, box: b });
      sel = { kind: "field", i: S.fields.length - 1 };
      renderAll();
      const inp = document.querySelector(`#bd-fields li[data-i="${sel.i}"] .f-key`);
      if (inp) { inp.focus(); inp.select(); }
      hint("Name the field (e.g. MON or TOTAL). Draw its words with the Words tool, or the next field.");
    } else if (tool === "words") {
      S.fields[sel.i].words_box = b;
      renderAll();
      hint(`Words box set for ${S.fields[sel.i].key}.`);
    } else if (tool === "mask") {
      S.mask.push(b); sel = { kind: "mask", i: S.mask.length - 1 }; renderAll();
    } else if (tool === "marker") {
      S.markers.push(b); sel = { kind: "marker", i: S.markers.length - 1 };
      if (S.markers.length === 4) { S.whole_image = false; syncInputs(); }
      renderAll();
      hint(S.markers.length < 4 ? `${S.markers.length} of 4 corner markers.` : "All four corner markers drawn: photos are registered from them.");
    } else if (tool === "tile") {
      S.tiles.push({ name: "tile_" + (S.tiles.length + 1), box: b, says: "" });
      sel = { kind: "tile", i: S.tiles.length - 1 }; renderAll();
      const inp = document.querySelector(`.bd-tile[data-i="${sel.i}"] .t-says`);
      if (inp) inp.focus();
    }
    changed();
  }

  function deleteSel() {
    if (!sel) return;
    const { kind, i } = sel;
    if (kind === "field") S.fields.splice(i, 1);
    else if (kind === "words") delete S.fields[i].words_box;
    else if (kind === "mask") S.mask.splice(i, 1);
    else if (kind === "marker") S.markers.splice(i, 1);
    else if (kind === "tile") S.tiles.splice(i, 1);
    sel = null;
    renderAll();
    changed();
  }

  function select(kind, i) {
    sel = { kind, i };
    renderAll();
  }

  // ------------------------------------------------------------------ rendering
  function renderAll() {
    renderLayer();
    renderFields();
    renderTiles();
    renderCounts();
    $("bd-del").disabled = !sel;
  }

  function renderLayer() {
    const L = $("bd-layer");
    L.innerHTML = "";
    const add = (kind, b, label, i, extra) => {
      const el = document.createElement("div");
      el.className = "bx k-" + kind + (sel && sel.kind === kind && sel.i === i ? " sel" : "") + (extra || "");
      place(el, b);
      if (label) { const s = document.createElement("span"); s.textContent = label; el.appendChild(s); }
      el.addEventListener("pointerdown", (e) => { if (tool === "select") { e.stopPropagation(); select(kind, i); scrollToItem(kind, i); } });
      L.appendChild(el);
    };
    S.tiles.forEach((t, i) => add("tile", t.box, t.name, i));
    S.mask.forEach((m, i) => add("mask", m, "mask", i));
    S.fields.forEach((f, i) => {
      const on = sel && (sel.kind === "field" || sel.kind === "words") && sel.i === i;
      if (f.box) add("field", f.box, f.key, i, on ? " sel" : "");
      if (f.words_box) add("words", f.words_box, "", i, on ? " sel" : "");
    });
    if (!S.whole_image) S.markers.forEach((m, i) => add("marker", m, "", i));
  }

  function scrollToItem(kind, i) {
    if (kind !== "field" && kind !== "words") return;
    const li = document.querySelector(`#bd-fields li[data-i="${i}"]`);
    if (li && window.innerWidth > 980) li.scrollIntoView({ block: "nearest" });
  }

  function labelText(f) {
    const l = f.label || {};
    if (l.parties) return null;
    return (l.keywords || []).join(" ");
  }

  function renderFields() {
    const ol = $("bd-fields");
    $("bd-nfields").textContent = S.fields.length ? `(${S.fields.length})` : "";
    if (!S.fields.length) { ol.innerHTML = `<li class="bd-none">No fields yet. Choose <b>Field</b> and drag over a digits box.</li>`; return; }
    ol.innerHTML = S.fields.map((f, i) => {
      const lt = labelText(f);
      const on = sel && (sel.kind === "field" || sel.kind === "words") && sel.i === i;
      return `<li data-i="${i}" class="${on ? "on" : ""}">
        <span class="f-i num">${i + 1}</span>
        <input class="f-key mono" value="${esc(f.key)}" aria-label="Field name" spellcheck="false">
        ${lt === null ? `<span class="f-logos small muted" title="Expected logos">logos: ${esc(f.label.parties.join(" + "))}</span>`
          : `<input class="f-lab" value="${esc(lt)}" placeholder="printed label" aria-label="Printed label keywords">`}
        <span class="f-chips">${f.box ? `<span class="chip ok">digits</span>` : `<span class="chip ghost" title="No digits box drawn">no box</span>`}${f.words_box ? `<span class="chip accent">words</span>` : ""}${f.vote ? `<span class="chip ghost" title="Counted in @vote">vote</span>` : ""}</span>
        <button class="f-x" aria-label="Delete ${esc(f.key)}" title="Delete">&times;</button>
      </li>`;
    }).join("");
    ol.querySelectorAll("li[data-i]").forEach((li) => {
      const i = +li.dataset.i;
      li.addEventListener("click", (e) => { if (!e.target.closest("input,button")) select("field", i); });
      li.querySelector(".f-key").addEventListener("focus", () => { if (!sel || sel.i !== i || sel.kind !== "field") { sel = { kind: "field", i }; renderLayer(); markRow(i); $("bd-del").disabled = false; } });
      li.querySelector(".f-key").addEventListener("input", (e) => {
        const v = e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, "_");
        if (v !== e.target.value) { const p = e.target.selectionStart; e.target.value = v; e.target.setSelectionRange(p, p); }
        S.fields[i].key = v; renderLayer(); changed();
      });
      const lab = li.querySelector(".f-lab");
      if (lab) lab.addEventListener("input", (e) => {
        const l = Object.assign({}, S.fields[i].label || {});
        l.keywords = e.target.value.toUpperCase().split(/[\s,]+/).filter(Boolean);
        S.fields[i].label = l; changed(true);
      });
      li.querySelector(".f-x").addEventListener("click", () => { sel = { kind: "field", i }; deleteSel(); });
    });
  }
  function markRow(i) { document.querySelectorAll("#bd-fields li").forEach((li) => li.classList.toggle("on", +li.dataset.i === i)); }

  function renderTiles() {
    const box = $("bd-tiles");
    if (!S.tiles.length) { box.innerHTML = ""; return; }
    box.innerHTML = `<h4 class="bd-sub">Tiles <span class="muted small">sent zoomed, after the page</span></h4>` + S.tiles.map((t, i) =>
      `<div class="bd-tile ${sel && sel.kind === "tile" && sel.i === i ? "on" : ""}" data-i="${i}">
        <input class="t-name mono" value="${esc(t.name)}" aria-label="Tile name" spellcheck="false">
        <input class="t-says" value="${esc(t.says)}" placeholder="what it shows, e.g. the weekend rows" aria-label="What the tile shows">
        <button class="f-x" aria-label="Delete tile" title="Delete">&times;</button></div>`).join("");
    box.querySelectorAll(".bd-tile").forEach((d) => {
      const i = +d.dataset.i;
      d.querySelector(".t-name").addEventListener("input", (e) => { S.tiles[i].name = e.target.value; renderLayer(); changed(true); });
      d.querySelector(".t-says").addEventListener("input", (e) => { S.tiles[i].says = e.target.value; changed(true); });
      d.querySelector(".f-x").addEventListener("click", () => { sel = { kind: "tile", i }; deleteSel(); });
    });
  }

  function renderCounts() {
    const c = [];
    c.push(S.size ? `<span class="chip ghost num">${S.size[0]} × ${S.size[1]} px page</span>` : "");
    c.push(S.whole_image ? `<span class="chip ghost">whole image</span>` :
      `<span class="chip ${S.markers.length === 4 ? "ok" : "warn"}">${S.markers.length}/4 corner markers</span>`);
    c.push(`<span class="chip ${S.mask.length ? "ok" : "warn"}">${S.mask.length} mask ${S.mask.length === 1 ? "box" : "boxes"}</span>`);
    c.push(`<span class="chip ghost">${S.tiles.length} ${S.tiles.length === 1 ? "tile" : "tiles"}</span>`);
    $("bd-counts").innerHTML = c.join("");
  }

  // ------------------------------------------------------------------ form inputs
  function syncInputs() {
    $("bd-form").value = S.form || "";
    $("bd-title").value = S.title || "";
    $("bd-whole").checked = !!S.whole_image;
    $("bd-ids").value = (S.identities || []).join("\n");
    validate();
  }
  $("bd-form").addEventListener("input", (e) => { S.form = e.target.value; changed(true); });
  $("bd-title").addEventListener("input", (e) => { S.title = e.target.value; changed(true); });
  $("bd-whole").addEventListener("change", (e) => { S.whole_image = e.target.checked; renderAll(); changed(true); });
  $("bd-ids").addEventListener("input", (e) => { S.identities = e.target.value.split("\n"); changed(); });

  let dirty = false;
  function changed(noValidate) {
    dirty = true;
    $("bd-saveres").innerHTML = $("bd-saveres").innerHTML && !$("bd-saveres").querySelector(".stale") ?
      `<p class="small muted stale">Changed since the last save.</p>` : $("bd-saveres").innerHTML;
    if (!noValidate) { clearTimeout(validateTimer); validateTimer = setTimeout(validate, 220); }
  }

  async function validate() {
    const lines = S.identities || [];
    const ul = $("bd-idres");
    if (!lines.some((l) => l.trim())) { ul.innerHTML = `<li class="muted">No identities yet. Example: <span class="mono">sum(MON..SUN) == TOTAL</span></li>`; return; }
    const r = await fetch("/api/builder/validate", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields: S.fields.map((f) => ({ key: f.key, vote: !!f.vote, words_box: !!f.words_box })), identities: lines }) });
    if (!r.ok) return;
    const d = await r.json();
    ul.innerHTML = d.lines.map((x, n) => {
      if (x.blank) return "";
      const src = lines[n];
      if (!x.ok) {
        const col = x.col == null ? null : Math.min(x.col, src.length);
        const caret = col == null ? "" : `<span class="mono bd-caret">${esc(src.slice(0, col))}<b>${esc(src.slice(col, col + 1) || " ")}</b>${esc(src.slice(col + 1))}</span>`;
        return `<li class="bad"><span class="dot"></span><div><b>Line ${n + 1}:</b> ${esc(x.error)}${caret}</div></li>`;
      }
      if (x.kind === "words") return `<li class="${x.warn ? "warn" : "ok"}"><span class="dot"></span><div><b>words == digits</b>: ${esc(x.note)}</div></li>`;
      return `<li class="ok"><span class="dot"></span><div><b>${esc(x.name)}</b><span class="mono small bd-expand">${esc(x.text)}</span></div></li>`;
    }).join("");
  }

  // ------------------------------------------------------------------ save
  async function save() {
    if (!S.size) { hint("Load a blank form first.", true); return null; }
    const btn = $("bd-save");
    btn.disabled = true;
    try {
      const r = await fetch("/api/builder/save", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(S) });
      const d = await r.json();
      const out = $("bd-saveres");
      if (!d.ok) {
        out.innerHTML = `<div class="banner">${"<div class='grow'><b>Not saved.</b><ul class='bd-errs'>" + d.errors.map((e) => `<li>${esc(e)}</li>`).join("") + "</ul></div>"}</div>`;
        $("bd-dl").hidden = true; $("bd-yamlbox").hidden = true;
        return null;
      }
      out.innerHTML = `<div class="banner ok"><div class="grow">Saved as <span class="mono">${esc(d.path)}</span>${d.warnings.length ? "<ul class='bd-errs'>" + d.warnings.map((w) => `<li>${esc(w)}</li>`).join("") + "</ul>" : ""}</div></div>`;
      $("bd-dl").href = d.download; $("bd-dl").hidden = false; $("bd-dl").setAttribute("download", d.slug + ".yaml");
      $("bd-yaml").textContent = d.yaml; $("bd-yamlbox").hidden = false;
      dirty = false;
      return d.slug;
    } catch (e) {
      $("bd-saveres").innerHTML = `<div class="banner"><div class="grow">Save failed: ${esc(e.message)}</div></div>`;
      return null;
    } finally { btn.disabled = false; }
  }
  $("bd-save").addEventListener("click", save);

  // ------------------------------------------------------------------ test
  function renderTestPicks(list) {
    $("bd-testpicks").innerHTML = list.map((f) => `<button class="btn sm" data-filled="${esc(f.name)}">${esc(f.label)}</button>`).join("");
    $("bd-testpicks").querySelectorAll("[data-filled]").forEach((b) => b.addEventListener("click", () => runTest({ sample: b.dataset.filled })));
  }
  function clearResults() { $("bd-test").innerHTML = ""; $("bd-saveres").innerHTML = ""; $("bd-dl").hidden = true; $("bd-yamlbox").hidden = true; }

  $("bd-photo").addEventListener("change", (e) => { const f = e.target.files[0]; if (f) runTest({ file: f }); e.target.value = ""; });
  $("bd-stored").addEventListener("click", async () => {
    const slug = await save();
    if (!slug) return;
    const box = $("bd-test");
    box.innerHTML = `<p class="small muted">Gating the stored read…</p>`;
    const r = await fetch(`/api/builder/gate/${slug}`, { method: "POST" });
    const d = await r.json();
    box.innerHTML = `<p class="small muted">The recorded ${esc(d.model)} read of page ${esc(d.clave)} (no model call), checked with your saved schema. Recorded verdict with our original schema: <b>${d.recorded_accepted ? "accepted" : "routed to a person"}</b>.</p>` + verdictHtml(d);
  });

  async function runTest(src) {
    const slug = await save();
    if (!slug) { $("bd-test").innerHTML = `<div class="banner"><div class="grow">Fix the schema before testing (see Save).</div></div>`; return; }
    const box = $("bd-test");
    box.innerHTML = `<p class="small muted">Registering and masking the photo…</p>`;
    let r;
    if (src.sample) r = await fetch(`/api/builder/test/${slug}/sample/${src.sample}`, { method: "POST" });
    else r = await fetch(`/api/builder/test/${slug}`, { method: "POST", headers: { "Content-Type": src.file.type || "application/octet-stream" }, body: src.file });
    const d = await r.json();
    if (!d.ok) { box.innerHTML = `<div class="banner"><div class="grow"><b>Not registered.</b> ${esc(d.message)} Nothing was stored.</div></div>`; return; }
    box.innerHTML = `<figure class="bd-masked"><img src="${esc(d.masked_url)}" alt="The masked page as stored"><figcaption class="small muted">Stored: the registered page (${esc(d.info.locator)}) with the mask blacked out. The original photo was not written to disk.</figcaption></figure><div id="bd-job"></div>`;
    if (d.refused) { $("bd-job").innerHTML = honest(d.message); return; }
    poll(d.status_url);
  }

  function honest(msg) {
    return `<div class="banner"><div class="grow"><b>No live read.</b> ${esc(msg)} The schema and the masked page are saved; the verdict appears once a read comes back.</div></div>`;
  }

  async function poll(url) {
    const box = $("bd-job");
    for (let n = 0; n < 600; n++) {
      let d;
      try { d = await (await fetch(url)).json(); } catch (e) { await sleep(1500); continue; }
      const ev = d.events || [];
      const err = ev.find((e) => e.type === "error");
      const ver = ev.find((e) => e.type === "verdict");
      const notice = ev.filter((e) => e.type === "notice").map((e) => `<div class="banner"><div class="grow">${esc(e.msg)}</div></div>`).join("");
      const stages = ev.filter((e) => e.type === "stage").map((e) => `<li>${esc(e.msg)}</li>`).join("");
      const head = d.state === "queued" ? `<p class="small muted">Queued${d.position ? `, ${d.position} ahead` : ""} · ${d.elapsed_s} s</p>` :
        (!d.done ? `<p class="small muted"><span class="live-dot"></span> Reading on AMD · ${d.elapsed_s} s</p>` : "");
      box.innerHTML = notice + head + (stages ? `<ol class="bd-stages small">${stages}</ol>` : "") +
        (err ? (err.code === "endpoint_busy" || err.code === "budget" ? honest(err.msg) : `<div class="banner"><div class="grow">${esc(err.msg)}</div></div>`) : "") +
        (ver ? `<p class="small muted">${esc(ver.model)} · ${ver.secs} s</p>` + verdictHtml(ver) : "");
      if (d.done) return;
      await sleep(1000);
    }
  }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function verdictHtml(v) {
    const ok = v.accepted;
    const head = `<div class="verdict ${ok ? "ok" : "bad"} bd-verdict"><div class="icon">${ok ? "&#10003;" : "!"}</div><div><div class="t">${ok ? "Accepted: the paper agrees with the read" : "Routed to a person"}</div>${!ok ? `<div class="sub">${esc((v.reasons || []).slice(0, 3).join("; "))}${(v.reasons || []).length > 3 ? "; …" : ""}</div>` : ""}</div></div>`;
    const ids = (v.identities || []).map((i) => `<li class="${i.ok === true ? "ok" : i.ok === false ? "bad" : "warn"}"><span class="dot"></span><div><b>${esc(i.name)}</b> <span class="mono small">${i.ok == null ? "not computable" : `${i.lhs} ${i.ok ? "=" : "≠"} ${i.rhs}`}</span></div></li>`).join("");
    const rows = (v.fields || []).map((f) => `<tr class="${f.ok ? "" : "bad"}"><td class="mono">${esc(f.key)}</td><td class="num">${f.n == null ? "–" : f.n}</td><td class="num">${f.w == null ? "–" : f.w}</td><td class="small muted">${esc(f.label == null ? "" : f.label)}</td></tr>`).join("");
    return head + (ids ? `<ul class="bd-idres bd-gids">${ids}</ul>` : "") +
      `<div class="bd-tablewrap"><table class="bd-vt"><thead><tr><th>Field</th><th>Digits</th><th>Words</th><th>Label read</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  // ------------------------------------------------------------------ start
  const want = new URLSearchParams(location.search).get("sample");
  loadSample(SAMPLES.some((s) => s.id === want) ? want : (SAMPLES[0] && SAMPLES[0].id));
})();
