/* AI import: upload screen (thumbnails, client-side resize, progress) and review screen (live counts). */
(function () {
  "use strict";

  var MAX_EDGE = 2000;
  var EXPECTED_S = 60;

  /* ---------- upload screen ---------- */
  var form = document.getElementById("ai-form");
  if (form) {
    var max = parseInt(form.dataset.max, 10) || 6;
    var thumbs = document.getElementById("ai-thumbs");
    var countEl = document.getElementById("ai-count");
    var submitBtn = document.getElementById("ai-submit");
    var errorBox = document.getElementById("ai-error");
    var errorText = document.getElementById("ai-error-text");
    var retryBtn = document.getElementById("ai-retry");
    var progress = document.getElementById("ai-progress");
    var fill = document.getElementById("ai-progress-fill");
    var msg = document.getElementById("ai-progress-msg");
    var elapsedEl = document.getElementById("ai-elapsed");
    var files = [];
    var timer = null;

    var updateUI = function () {
      thumbs.textContent = "";
      files.forEach(function (item, i) {
        var li = document.createElement("li");
        li.className = "ai-thumb";
        var img = document.createElement("img");
        img.src = item.url;
        img.alt = "Page " + (i + 1);
        var n = document.createElement("span");
        n.className = "ai-thumb__n";
        n.textContent = "Page " + (i + 1);
        var rm = document.createElement("button");
        rm.type = "button";
        rm.className = "ai-thumb__rm";
        rm.setAttribute("aria-label", "Remove page " + (i + 1));
        rm.innerHTML = "<span aria-hidden='true'>&times;</span>";
        rm.addEventListener("click", function () {
          URL.revokeObjectURL(item.url);
          files.splice(i, 1);
          updateUI();
        });
        li.append(img, n, rm);
        thumbs.appendChild(li);
      });
      countEl.textContent = files.length
        ? files.length + " of " + max + " pages selected. Add more pages or press Read my menu."
        : "Up to " + max + " pages, one photo per page.";
      submitBtn.disabled = files.length === 0;
    };

    var addFiles = function (list) {
      Array.prototype.forEach.call(list, function (f) {
        if (files.length >= max) return;
        if (f.type && f.type.indexOf("image/") !== 0) return;
        files.push({ file: f, url: URL.createObjectURL(f) });
      });
      hideError();
      updateUI();
    };

    ["ai-camera", "ai-files"].forEach(function (id) {
      var input = document.getElementById(id);
      input.addEventListener("change", function () {
        addFiles(input.files);
        input.value = "";
      });
    });

    var showError = function (text) {
      errorText.innerHTML = "";
      var strong = document.createElement("strong");
      strong.textContent = text;
      errorText.appendChild(strong);
      errorBox.classList.add("is-on");
      retryBtn.hidden = files.length === 0;
      form.classList.remove("is-busy");
      progress.classList.remove("is-on");
      stopTimer();
      errorBox.focus();
    };
    var hideError = function () {
      errorBox.classList.remove("is-on");
    };

    var stopTimer = function () {
      if (timer) { clearInterval(timer); timer = null; }
    };
    var startTimer = function () {
      var start = Date.now();
      fill.style.width = "3%";
      elapsedEl.textContent = "0 s";
      msg.textContent = "Usually 20–60 seconds";
      timer = setInterval(function () {
        var s = Math.floor((Date.now() - start) / 1000);
        elapsedEl.textContent = s + " s";
        fill.style.width = Math.min(95, 3 + (s / EXPECTED_S) * 92) + "%";
        if (s > EXPECTED_S) msg.textContent = "Taking longer than usual, please keep this page open";
      }, 500);
    };

    // Downscale in the browser so 6 phone photos do not become a 40 MB upload.
    var shrink = function (file) {
      if (!window.createImageBitmap || !HTMLCanvasElement.prototype.toBlob) return Promise.resolve(file);
      return createImageBitmap(file, { imageOrientation: "from-image" }).then(function (bmp) {
        var scale = Math.min(1, MAX_EDGE / Math.max(bmp.width, bmp.height));
        var canvas = document.createElement("canvas");
        canvas.width = Math.round(bmp.width * scale);
        canvas.height = Math.round(bmp.height * scale);
        var ctx = canvas.getContext("2d");
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height);
        if (bmp.close) bmp.close();
        return new Promise(function (resolve) {
          canvas.toBlob(function (blob) { resolve(blob || file); }, "image/jpeg", 0.85);
        });
      }).catch(function () { return file; });
    };

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (!files.length) return;
      hideError();
      form.classList.add("is-busy");
      progress.classList.add("is-on");
      startTimer();
      Promise.all(files.map(function (item) { return shrink(item.file); })).then(function (blobs) {
        var fd = new FormData();
        fd.append("csrfmiddlewaretoken", form.querySelector("[name=csrfmiddlewaretoken]").value);
        blobs.forEach(function (b, i) { fd.append("photos", b, "page-" + (i + 1) + ".jpg"); });
        return fetch(form.action, {
          method: "POST",
          body: fd,
          credentials: "same-origin",
          headers: { "X-Requested-With": "fetch", "Accept": "application/json" }
        });
      }).then(function (resp) {
        return resp.json().catch(function () { return {}; }).then(function (data) {
          if (resp.ok && data.redirect) {
            stopTimer();
            fill.style.width = "100%";
            window.location.href = data.redirect;
          } else {
            showError(data.error || "Something went wrong (error " + resp.status + "). Please try again.");
          }
        });
      }).catch(function () {
        showError("The connection was lost before the menu could be read. Check your signal and try again.");
      });
    });

    updateUI();
  }

  /* ---------- review screen ---------- */
  var review = document.getElementById("ai-review");
  if (review) {
    var counter = document.getElementById("ai-bar-count");
    var importBtn = document.getElementById("ai-import-btn");
    var update = function () {
      var items = 0, cats = 0;
      review.querySelectorAll(".ai-cat").forEach(function (cat) {
        var catOn = cat.querySelector(".ai-cat__on").checked;
        var n = 0;
        cat.querySelectorAll(".ai-item").forEach(function (item) {
          var on = catOn && item.querySelector(".ai-item__on").checked;
          item.classList.toggle("is-off", !on);
          if (on) n++;
        });
        cat.classList.toggle("is-off", !catOn);
        if (n) { cats++; items += n; }
      });
      review.querySelectorAll(".ai-special").forEach(function (sp) {
        sp.classList.toggle("is-off", !sp.querySelector(".ai-special__on").checked);
      });
      counter.textContent = items + " item" + (items === 1 ? "" : "s") + " in " + cats + " categor" + (cats === 1 ? "y" : "ies") + " will be imported";
      importBtn.disabled = items === 0;
    };
    review.addEventListener("change", function (ev) {
      if (ev.target.matches("input[type=checkbox]")) update();
    });
    var discard = document.getElementById("ai-discard-btn");
    if (discard) {
      discard.addEventListener("click", function (ev) {
        if (!window.confirm("Discard this import? Nothing has been saved yet.")) ev.preventDefault();
      });
    }
    update();
  }
})();
