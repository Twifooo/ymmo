/* ----------------------------------------------------------------------
 * Comparateur de biens — 100% côté client.
 * On stocke les IDs sélectionnés dans sessionStorage : pas de backend,
 * pas de cookie, pas de framework. La page /comparer lit ?ids=... pour
 * rendre la table comparative côté serveur.
 * ---------------------------------------------------------------------- */
(function () {
  "use strict";

  var KEY = "ymmo-compare";
  var MAX = 4;

  function load() {
    try {
      var raw = sessionStorage.getItem(KEY);
      if (!raw) return [];
      return JSON.parse(raw).filter(Boolean);
    } catch (_) { return []; }
  }
  function save(items) {
    try { sessionStorage.setItem(KEY, JSON.stringify(items)); }
    catch (_) {}
  }

  function refresh() {
    var items = load();
    var tray = document.getElementById("compare-tray");
    var list = document.getElementById("compare-tray-list");
    var go = document.getElementById("compare-tray-go");
    var btn = document.querySelector(".compare-tray-btn");
    var count = document.querySelector(".compare-tray-count");

    if (count) count.textContent = items.length;
    if (btn) btn.hidden = items.length === 0;

    // Met à jour les boutons "compare" sur les cartes pour refléter l'état.
    document.querySelectorAll(".compare-btn").forEach(function (b) {
      var id = parseInt(b.dataset.compareId, 10);
      var present = items.some(function (i) { return i.id === id; });
      b.setAttribute("aria-pressed", present ? "true" : "false");
      b.textContent = (present ? "✓ " : "⊕ ") + (b.dataset.compareLabel || "Comparer");
    });

    if (!tray || !list || !go) return;

    if (items.length === 0) {
      tray.hidden = true;
      return;
    }
    tray.hidden = false;
    list.innerHTML = "";
    items.forEach(function (item) {
      var li = document.createElement("li");
      var label = document.createElement("span");
      label.textContent = item.title;
      var rm = document.createElement("button");
      rm.type = "button";
      rm.setAttribute("aria-label", "Retirer");
      rm.textContent = "×";
      rm.addEventListener("click", function () {
        save(load().filter(function (i) { return i.id !== item.id; }));
        refresh();
      });
      li.appendChild(label);
      li.appendChild(rm);
      list.appendChild(li);
    });

    // Construit l'URL /comparer?ids=1,2,3
    var ids = items.map(function (i) { return i.id; }).join(",");
    go.href = "/comparer?ids=" + encodeURIComponent(ids);
  }

  // Conserve le label actuel pour pouvoir le restaurer (i18n FR/EN).
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".compare-btn").forEach(function (b) {
      b.dataset.compareLabel = (b.textContent || "Comparer").replace(/^[⊕✓]\s+/, "").trim();
      b.addEventListener("click", function () {
        var id = parseInt(b.dataset.compareId, 10);
        if (!id) return;
        var items = load();
        var idx = items.findIndex(function (i) { return i.id === id; });
        if (idx >= 0) {
          items.splice(idx, 1);
        } else {
          if (items.length >= MAX) {
            alert("Maximum " + MAX + " biens.");
            return;
          }
          items.push({ id: id, title: b.dataset.compareTitle || ("Bien #" + id) });
        }
        save(items);
        refresh();
      });
    });

    var clear = document.getElementById("compare-tray-clear");
    if (clear) clear.addEventListener("click", function () { save([]); refresh(); });

    var btn = document.querySelector(".compare-tray-btn");
    if (btn) btn.addEventListener("click", function () {
      var t = document.getElementById("compare-tray");
      if (t) t.hidden = !t.hidden;
    });

    refresh();
  });
})();
