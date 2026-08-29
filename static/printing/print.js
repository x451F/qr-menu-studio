/* Print page behaviour: copy URL, QR colour switch, PDF previews. No dependencies. */
(function () {
  "use strict";
  var root = document.querySelector("[data-pr-root]");
  if (!root) return;

  // swatches (set via CSSOM so the page works under a strict CSP)
  root.querySelectorAll("[data-color]").forEach(function (el) {
    el.style.backgroundColor = el.getAttribute("data-color");
  });

  // copy the public URL
  var copyBtn = root.querySelector("[data-pr-copy]");
  var urlInput = root.querySelector("[data-pr-url]");
  var status = root.querySelector("[data-pr-copy-status]");
  if (copyBtn && urlInput) {
    copyBtn.addEventListener("click", function () {
      var done = function (ok) {
        if (status) status.textContent = ok ? "Address copied." : "Press Ctrl/Cmd+C to copy.";
      };
      urlInput.select();
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(urlInput.value).then(function () { done(true); }, function () { done(false); });
      } else {
        try { done(document.execCommand("copy")); } catch (e) { done(false); }
      }
    });
  }

  // QR colour switch: preview + download links
  function setColor(value) {
    root.querySelectorAll("[data-pr-qr]").forEach(function (box) {
      box.hidden = box.getAttribute("data-pr-qr") !== value;
    });
    root.querySelectorAll("[data-pr-dl]").forEach(function (a) {
      var url = new URL(a.getAttribute("href"), window.location.href);
      url.searchParams.set("color", value);
      a.setAttribute("href", url.pathname + url.search);
    });
  }
  root.querySelectorAll("[data-pr-color]").forEach(function (input) {
    input.addEventListener("change", function () { if (input.checked) setColor(input.value); });
  });

  // PDF previews (real PDF in an iframe, same origin)
  root.querySelectorAll("[data-pr-pdf-form]").forEach(function (form) {
    var btn = form.querySelector("[data-pr-preview]");
    var box = form.querySelector("[data-pr-preview-box]");
    var frame = form.querySelector("[data-pr-frame]");
    var open = form.querySelector("[data-pr-open]");
    if (!btn || !box || !frame) return;

    function previewUrl() {
      var params = new URLSearchParams(new FormData(form));
      params.set("inline", "1");
      return form.getAttribute("action") + "?" + params.toString();
    }
    function refresh() {
      var url = previewUrl();
      frame.src = url + "#toolbar=0&navpanes=0&view=Fit";
      if (open) open.href = url;
      box.hidden = false;
    }
    btn.addEventListener("click", refresh);
    var timer = null;
    form.addEventListener("change", function () {
      if (box.hidden) return;
      clearTimeout(timer);
      timer = setTimeout(refresh, 350);
    });
    form.addEventListener("input", function (e) {
      if (box.hidden || e.target.type !== "text") return;
      clearTimeout(timer);
      timer = setTimeout(refresh, 700);
    });
  });
})();
