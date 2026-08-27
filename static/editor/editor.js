/* QR Menu Studio — admin behaviour. Vanilla JS on top of HTMX + SortableJS. No build step. */
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* ---------------- HTMX configuration ---------------- */
  function configureHtmx() {
    if (!window.htmx) return;
    // 422 = validation problem: swap the returned message (via HX-Retarget) instead of dropping it.
    htmx.config.responseHandling = [
      { code: "204", swap: false },
      { code: "[23]..", swap: true },
      { code: "422", swap: true, error: false },
      { code: "[45]..", swap: false, error: true }
    ];
    htmx.config.defaultSettleDelay = 0;
    htmx.config.scrollBehavior = "auto";
  }

  /* ---------------- helpers ---------------- */
  function csrfToken() {
    try { return JSON.parse(document.body.getAttribute("hx-headers"))["X-CSRFToken"]; } catch (e) { return ""; }
  }

  var toastTimer = null;
  function armToast() {
    var toast = $("#toast");
    clearTimeout(toastTimer);
    if (toast && toast.classList.contains("is-visible")) {
      toastTimer = setTimeout(function () { toast.classList.remove("is-visible"); }, 8000);
    }
  }
  function flash(message, ms) {
    var toast = $("#toast");
    if (!toast) return;
    toast.className = "toast toast--plain is-visible";
    toast.textContent = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove("is-visible"); }, ms || 3500);
  }

  /* ---------------- global save status ---------------- */
  var status = { inflight: 0, warn: "", failed: null, timer: null };
  function setStatus(state, text) {
    var el = $("#save-status");
    if (!el) return;
    el.dataset.state = state;
    $(".save-status__text", el).textContent = text || "";
    clearTimeout(status.timer);
    if (state === "saved") status.timer = setTimeout(function () { el.dataset.state = "idle"; }, 2200);
    if (state === "warn") status.timer = setTimeout(function () { el.dataset.state = "idle"; }, 6000);
  }

  document.addEventListener("htmx:beforeRequest", function (e) {
    status.inflight++;
    status.warn = "";
    setStatus("saving", "Saving…");
  });
  document.addEventListener("htmx:afterRequest", function (e) {
    status.inflight = Math.max(0, status.inflight - 1);
    var xhr = e.detail.xhr;
    var code = xhr ? xhr.status : 0;
    if (code === 422 || (e.detail.successful && status.warn)) {
      status.inflight === 0 && setStatus("warn", status.warn || "Check the highlighted field");
    } else if (!e.detail.successful && code !== 401) {
      status.failed = { elt: e.detail.elt, type: (e.detail.requestConfig.triggeringEvent || {}).type };
      setStatus("error", "Error — tap to retry");
    } else if (status.inflight === 0 && $("#save-status").dataset.state === "saving") {
      setStatus("saved", "Saved");
    }
    if (e.detail.successful && e.detail.requestConfig.verb === "post") schedulePreviewReload();
  });
  document.addEventListener("click", function (e) {
    var st = e.target.closest("#save-status");
    if (st && st.dataset.state === "error" && status.failed && document.contains(status.failed.elt)) {
      var f = status.failed;
      htmx.trigger(f.elt, f.type && f.type !== "input" ? f.type : "change");
    }
  });

  document.addEventListener("htmx:afterSettle", armToast);
  document.addEventListener("htmx:oobAfterSwap", armToast);

  /* Server messages carried in HX-Trigger */
  document.addEventListener("validation", function (e) { status.warn = (e.detail && e.detail.message) || "Check the highlighted field"; });

  /* ---------------- autosave parameter filtering ---------------- */
  // Forms with data-single-field only send the field the user just changed.
  document.addEventListener("htmx:configRequest", function (e) {
    var elt = e.detail.elt;
    if (!elt || !elt.matches || !elt.matches("form[data-single-field]")) return;
    var ev = e.detail.triggeringEvent;
    var t = ev && ev.target;
    if (!t || !t.name || t.type === "file") { e.preventDefault(); return; }
    var value;
    if (t.type === "checkbox") value = t.checked ? "1" : "0";
    else if (t.type === "radio") { if (!t.checked) { e.preventDefault(); return; } value = t.value; }
    else value = t.value;
    var fd = e.detail.formData;
    Array.from(fd.keys()).forEach(function (k) { fd.delete(k); });
    fd.append(t.name, value);
  });
  document.addEventListener("submit", function (e) {
    if (e.target.matches("[data-autosave], [data-single-field]")) e.preventDefault();
  });

  /* ---------------- open / collapse ---------------- */
  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-toggle-open]");
    if (t) {
      var item = t.closest(".item");
      var open = item.classList.toggle("is-open");
      t.setAttribute("aria-expanded", open ? "true" : "false");
      return;
    }
    var c = e.target.closest("[data-collapse]");
    if (c) { c.closest(".cat").classList.toggle("is-collapsed"); return; }
    var all = e.target.closest("[data-collapse-all]");
    if (all) {
      var cats = $$(".cat");
      var collapse = !cats.every(function (x) { return x.classList.contains("is-collapsed"); });
      cats.forEach(function (x) { x.classList.toggle("is-collapsed", collapse); });
      all.textContent = collapse ? "Expand all" : "Collapse all";
      return;
    }
    var d = e.target.closest("[data-cat-desc-toggle]");
    if (d) {
      var cat = d.closest(".cat");
      var box = $(".cat__desc", cat);
      box.classList.add("is-open");
      var det = d.closest("details");
      if (det) det.open = false;
      var inp = $("input:not([style*='display: none'])", box);
      var vis = $$("input", box).filter(function (i) { return i.offsetParent !== null; })[0];
      (vis || inp) && (vis || inp).focus();
      return;
    }
    // close popover menus on outside click
    $$("details.menu[open]").forEach(function (m) { if (!m.contains(e.target)) m.open = false; });
  });

  /* ---------------- optimistic toggles ---------------- */
  document.addEventListener("click", function (e) {
    var b = e.target.closest(".tgl[data-tgl]");
    if (!b) return;
    var on = !b.classList.contains("is-on");
    b.classList.toggle("is-on", on);
    b.setAttribute("aria-pressed", on ? "true" : "false");
    var kind = b.dataset.tgl;
    var box = b.closest(".item, .cat");
    if (!box) return;
    if (kind === "soldout") box.classList.toggle("is-soldout", on);
    else if (kind === "item_visible" || kind === "cat_visible") box.classList.toggle("is-hidden", !on);
    else if (kind === "special_active") box.classList.toggle("is-inactive", !on);
  }, true);

  /* ---------------- language switch (menu editor) ---------------- */
  function setLang(lang) {
    var ed = $("#editor");
    if (!ed) return;
    if (ed.dataset.english !== "1") lang = "fr";
    ed.dataset.lang = lang;
    $$("[data-set-lang]").forEach(function (b) {
      var on = b.dataset.setLang === lang;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    try { localStorage.setItem("editor-lang", lang); } catch (e) { /* ignore */ }
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-set-lang]");
    if (b) setLang(b.dataset.setLang);
  });

  /* ---------------- prices editor ---------------- */
  function refreshPrices(box) {
    var rows = $$(".price-row", box);
    var labelled = rows.some(function (r) { return $$(".price-row__label input", r).some(function (i) { return i.value.trim(); }); });
    box.classList.toggle("is-multi", rows.length > 1 || labelled);
  }
  document.addEventListener("click", function (e) {
    var add = e.target.closest("[data-price-add]");
    if (add) {
      var box = add.closest("[data-prices]");
      var tpl = $("#tpl-price-row");
      if (!tpl) return;
      var row = tpl.content.querySelector(".price-row").cloneNode(true);
      $(".prices__rows", box).appendChild(row);
      box.classList.add("is-multi");
      var first = $$("input", row).filter(function (i) { return i.offsetParent !== null; })[0];
      if (first) first.focus();
      return;
    }
    var rm = e.target.closest("[data-price-remove]");
    if (rm) {
      var b2 = rm.closest("[data-prices]");
      var form = rm.closest("form");
      rm.closest(".price-row").remove();
      if (!$(".price-row", b2)) {
        var tpl2 = $("#tpl-price-row");
        if (tpl2) $(".prices__rows", b2).appendChild(tpl2.content.querySelector(".price-row").cloneNode(true));
      }
      refreshPrices(b2);
      if (form) form.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });
  document.addEventListener("input", function (e) {
    var t = e.target;
    if (t.closest && t.closest(".price-row__label")) refreshPrices(t.closest("[data-prices]"));
    if (t.classList && t.classList.contains("input")) t.classList.remove("is-invalid");
    if (t.classList && t.classList.contains("is-missing") && t.value.trim()) t.classList.remove("is-missing");
  });

  function clearPriceErrors(form) {
    $$(".price-row .is-invalid", form).forEach(function (i) { i.classList.remove("is-invalid"); });
    $$(".price-error", form).forEach(function (s) { s.textContent = ""; });
  }
  document.addEventListener("pricesFormatted", function (e) {
    var form = e.target.closest && e.target.closest("form");
    if (!form) return;
    clearPriceErrors(form);
    var values = (e.detail && e.detail.values) || [];
    $$("[name=price_amount]", form).forEach(function (input, i) {
      var v = values[i];
      if (v != null && input !== document.activeElement && input.value !== v) input.value = v;
    });
  });
  document.addEventListener("priceError", function (e) {
    var form = e.target.closest && e.target.closest("form");
    if (!form) return;
    var rows = (e.detail && e.detail.rows) || [];
    var inputs = $$("[name=price_amount]", form);
    rows.forEach(function (i) { inputs[i] && inputs[i].classList.add("is-invalid"); });
    var msg = $(".price-error", form);
    if (msg) msg.textContent = (e.detail && e.detail.message) || "Invalid price";
  });

  /* ---------------- items: moves, quick add ---------------- */
  document.addEventListener("itemMoved", function (e) {
    var d = e.detail || {};
    var item = document.getElementById("item-" + d.item);
    var list = document.getElementById("items-" + d.category);
    if (item && list) {
      list.appendChild(item);
      list.closest(".cat").classList.remove("is-collapsed");
      item.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  });
  document.addEventListener("focusin", function (e) {
    var sel = e.target;
    if (!sel.matches || !sel.matches("select[data-move]")) return;
    var current = sel.value;
    sel.innerHTML = "";
    $$(".cat").forEach(function (cat) {
      var name = $("input[name=name_fr]", cat);
      var o = document.createElement("option");
      o.value = cat.dataset.id;
      o.textContent = (name && name.value.trim()) || "Untitled category";
      if (o.value === current) o.selected = true;
      sel.appendChild(o);
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" || e.isComposing) return;
    var form = e.target.closest && e.target.closest("[data-quick-add]");
    if (!form) return;
    e.preventDefault();
    if (e.target.name === "name_fr") {
      if (e.target.value.trim()) $("[name=price_amount]", form).focus();
    } else {
      form.requestSubmit();
    }
  });
  document.addEventListener("htmx:afterRequest", function (e) {
    var elt = e.detail.elt;
    if (!elt || !elt.matches) return;
    if (elt.matches("[data-quick-add], [data-cat-add]") && e.detail.successful) {
      elt.reset();
      var first = $("input", elt);
      first && first.focus({ preventScroll: false });
    }
    if (elt.id === "translate-missing") {
      if (e.detail.successful) window.location.reload();
      else flash("Translation is unavailable right now.");
    }
  });
  document.addEventListener("htmx:afterSwap", function (e) {
    initSortables();
    var t = e.target;
    if (t && t.id === "specials") {
      var last = $$(".special", t).pop();
      var f = last && $$("input[name^=title_]", last).filter(function (i) { return i.offsetParent !== null; })[0];
      f && f.focus();
    }
  });

  /* ---------------- drag & drop ---------------- */
  function post(url, values, source) {
    htmx.ajax("POST", url, { source: source, values: values, swap: "none" });
  }
  function ids(list, sel) {
    return $$(":scope > " + sel, list).map(function (x) { return x.dataset.id; }).join(",");
  }
  function initSortables() {
    if (!window.Sortable) return;
    var ed = $("#editor");
    if (!ed) return;
    var common = { animation: 150, delay: 120, delayOnTouchOnly: true, touchStartThreshold: 6, scroll: true, scrollSensitivity: 90, scrollSpeed: 14, forceFallback: false };
    $$("[data-sortable='categories']").forEach(function (el) {
      if (el._sortable) return;
      el._sortable = new Sortable(el, Object.assign({}, common, {
        handle: ".cat-handle", draggable: ".cat", ghostClass: "sortable-ghost", chosenClass: "sortable-chosen",
        onEnd: function () { post(ed.dataset.reorderCategories, { order: ids(el, ".cat") }, el); }
      }));
    });
    $$("[data-sortable='specials']").forEach(function (el) {
      if (el._sortable) return;
      el._sortable = new Sortable(el, Object.assign({}, common, {
        handle: ".drag-handle", draggable: ".special", ghostClass: "sortable-ghost", chosenClass: "sortable-chosen",
        onEnd: function () { post(ed.dataset.reorderSpecials, { order: ids(el, ".special") }, el); }
      }));
    });
    $$(".items").forEach(function (el) {
      if (el._sortable) return;
      el._sortable = new Sortable(el, Object.assign({}, common, {
        group: "items", handle: ".drag-handle", draggable: ".item", ghostClass: "sortable-ghost", chosenClass: "sortable-chosen",
        emptyInsertThreshold: 28,
        onEnd: function (evt) {
          var to = evt.to;
          var moved = evt.item;
          var select = $("select[data-move]", moved);
          if (select) select.value = to.dataset.category;
          post(ed.dataset.reorderItems, { category: to.dataset.category, order: ids(to, ".item") }, to);
        }
      }));
    });
  }

  /* ---------------- colour fields (settings) ---------------- */
  function syncColorfield(box) {
    var text = $("input[type=text]", box);
    var pick = $("input[type=color]", box);
    var v = (text.value || "").toLowerCase();
    if (/^#[0-9a-f]{6}$/.test(v)) pick.value = v;
    $$(".swatch", box).forEach(function (s) { s.classList.toggle("is-active", (s.dataset.color || "") === v); });
  }
  document.addEventListener("click", function (e) {
    var s = e.target.closest(".swatch");
    if (!s) return;
    var box = s.closest("[data-colorfield]");
    var text = $("input[type=text]", box);
    text.value = s.dataset.color;
    syncColorfield(box);
    text.dispatchEvent(new Event("change", { bubbles: true }));
  });
  document.addEventListener("input", function (e) {
    var box = e.target.closest && e.target.closest("[data-colorfield]");
    if (!box) return;
    var text = $("input[type=text]", box);
    if (e.target.type === "color") {
      text.value = e.target.value;
      text.dispatchEvent(new Event("input", { bubbles: true }));
    }
    syncColorfield(box);
  });

  /* ---------------- per-field AI translate ---------------- */
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-translate]");
    if (!btn) return;
    var field = btn.closest(".tfield");
    var fr = $("[data-lang=fr]", field);
    var en = $("[data-lang=en]", field);
    var root = btn.closest("[data-translate-url]");
    if (!fr || !en || !root) return;
    var text = fr.value.trim();
    if (!text) { flash("Type the French text first."); return; }
    var key = field.dataset.tkey || "text";
    var texts = {};
    texts[key] = text;
    btn.disabled = true;
    fetch(root.dataset.translateUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      credentials: "same-origin",
      body: JSON.stringify({ source: "fr", target: "en", texts: texts })
    }).then(function (r) {
      return r.json().then(function (data) { return { ok: r.ok, data: data }; });
    }).then(function (res) {
      if (res.ok && res.data.translations && res.data.translations[key] != null) {
        en.value = res.data.translations[key];
        en.classList.remove("is-missing");
        en.dispatchEvent(new Event("input", { bubbles: true }));
        en.dispatchEvent(new Event("change", { bubbles: true }));
      } else {
        flash((res.data && res.data.error) || "Translation is unavailable right now.");
      }
    }).catch(function () {
      flash("Translation is unavailable right now.");
    }).then(function () { btn.disabled = false; });
  });

  /* ---------------- copy to clipboard ---------------- */
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-copy]");
    if (!b) return;
    var text = b.dataset.copy;
    var done = function () {
      var label = $("span", b);
      if (label) {
        var old = label.textContent;
        label.textContent = "Copied";
        setTimeout(function () { label.textContent = old; }, 1500);
      }
      flash("Link copied");
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else { fallbackCopy(text); done(); }
  });
  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch (e) { /* ignore */ }
    ta.remove();
  }

  /* ---------------- live preview ---------------- */
  var pv = null;
  var desktop = window.matchMedia("(min-width: 1024px)");

  function initPreview() {
    var el = $("#preview");
    if (!el) return;
    pv = {
      el: el,
      frame: $("[data-frame]", el),
      base: el.dataset.base,
      theme: el.dataset.theme,
      mode: el.dataset.mode === "auto" ? null : el.dataset.mode,
      photos: true,
      saved: { theme: el.dataset.theme, mode: el.dataset.mode },
      loaded: false,
      timer: null
    };
    desktop.addEventListener("change", function () { if (desktop.matches) ensureLoaded(); });
    if (desktop.matches) ensureLoaded();

    document.addEventListener("click", function (e) {
      if (e.target.closest("[data-preview-open]")) openPreview();
      else if (e.target.closest("[data-preview-close]")) closePreview();
      var chip = e.target.closest("#preview [data-theme]");
      if (chip) chooseTheme(chip.dataset.theme);
      var seg = e.target.closest("#preview [data-mode]");
      if (seg) chooseMode(pv.mode === seg.dataset.mode ? null : seg.dataset.mode);
      if (e.target.closest("[data-use-theme]")) useTheme();
    });
    $("[data-photos]", el).addEventListener("change", function (e) { pv.photos = e.target.checked; load(); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closePreview(); });

    // settings page: keep the preview in step with the theme / mode controls
    document.addEventListener("change", function (e) {
      var t = e.target;
      if (t.name === "theme" && t.form && t.form.id === "settings-form") chooseTheme(t.value, true);
      if (t.name === "color_mode" && t.form && t.form.id === "settings-form") chooseMode(t.value === "auto" ? null : t.value, true);
    });
    document.addEventListener("settingsSaved", function (e) {
      var d = e.detail || {};
      if (d.publicPath) pv.base = d.publicPath + "?preview=1";
      if (d.theme) { pv.saved.theme = d.theme; }
      if (d.colorMode) { pv.saved.mode = d.colorMode; }
      refreshUseTheme();
    });
  }

  function url() {
    var u = pv.base + "&theme=" + encodeURIComponent(pv.theme);
    if (pv.mode) u += "&mode=" + pv.mode;
    if (!pv.photos) u += "&photos=0";
    return u;
  }
  function isVisible() { return desktop.matches || pv.el.classList.contains("is-open"); }
  function ensureLoaded() { if (!pv.loaded) load(); }
  function load() {
    if (!isVisible()) { pv.loaded = false; return; }
    pv.loaded = true;
    pv.frame.src = url();
  }
  function reload() {
    if (!isVisible() || !pv.loaded) { pv.loaded = false; return; }
    var y = 0;
    try { y = pv.frame.contentWindow.scrollY || 0; } catch (e) { /* cross-origin */ }
    var restore = function () {
      pv.frame.removeEventListener("load", restore);
      try { pv.frame.contentWindow.scrollTo(0, y); setTimeout(function () { pv.frame.contentWindow.scrollTo(0, y); }, 60); } catch (e) { /* ignore */ }
    };
    pv.frame.addEventListener("load", restore);
    try { pv.frame.contentWindow.location.replace(url()); } catch (e) { pv.frame.src = url(); }
  }
  function schedulePreviewReload() {
    if (!pv) return;
    clearTimeout(pv.timer);
    pv.timer = setTimeout(reload, 450);
  }
  function openPreview() {
    pv.el.classList.add("is-open");
    document.body.style.overflow = "hidden";
    if (!pv.loaded) load(); else reload();
  }
  function closePreview() {
    if (!pv || !pv.el.classList.contains("is-open")) return;
    pv.el.classList.remove("is-open");
    document.body.style.overflow = "";
  }
  function chooseTheme(theme, fromForm) {
    pv.theme = theme;
    $$("#preview [data-theme]").forEach(function (c) {
      var on = c.dataset.theme === theme;
      c.classList.toggle("is-active", on);
      c.setAttribute("aria-pressed", on ? "true" : "false");
    });
    refreshUseTheme();
    load();
  }
  function chooseMode(mode, fromForm) {
    pv.mode = mode;
    $$("#preview [data-mode]").forEach(function (c) {
      var on = c.dataset.mode === mode;
      c.classList.toggle("is-active", on);
      c.setAttribute("aria-pressed", on ? "true" : "false");
    });
    refreshUseTheme();
    load();
  }
  function refreshUseTheme() {
    var btn = $("[data-use-theme]", pv.el);
    var savedMode = pv.saved.mode === "auto" ? null : pv.saved.mode;
    var differs = pv.theme !== pv.saved.theme || pv.mode !== savedMode;
    // On the settings page the theme cards already save on tap, so the button is redundant.
    btn.hidden = !differs || !!$("#settings-form");
  }
  function useTheme() {
    var values = { theme: pv.theme };
    values.color_mode = pv.mode || "auto";
    htmx.ajax("POST", pv.el.dataset.settingsUrl, { source: pv.el, values: values, swap: "none" });
  }

  /* ---------------- boot ---------------- */
  function boot() {
    configureHtmx();
    var ed = $("#editor");
    if (ed) {
      var lang = "fr";
      try { lang = localStorage.getItem("editor-lang") || "fr"; } catch (e) { /* ignore */ }
      setLang(lang);
    }
    $$("[data-colorfield]").forEach(syncColorfield);
    initPreview();
    initSortables();
    var use = $(".chip__ic use");
    if (use) {
      var href = (use.getAttribute("href") || "").split("#")[0];
      if (!href) document.documentElement.classList.add("no-sprite");
      else fetch(href, { method: "HEAD" }).then(function (r) {
        if (!r.ok) document.documentElement.classList.add("no-sprite");
      }).catch(function () {});
    }
  }
  // Deferred scripts run while readyState is "interactive": wait for DOMContentLoaded so every deferred vendor script is ready.
  if (document.readyState === "complete") boot();
  else document.addEventListener("DOMContentLoaded", boot);
})();
