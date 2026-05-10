/* ----------------------------------------------------------------------
 * Ymmo — JS d'interactions progressives.
 * Aucun framework. Le site reste 100 % utilisable sans JavaScript.
 * ---------------------------------------------------------------------- */
(function () {
  "use strict";

  /* --- 1. Thème clair / sombre ------------------------------------- */
  // L'override "data-theme" sur <html> a priorité sur prefers-color-scheme.
  // On stocke le choix dans localStorage pour le re-appliquer au reload.
  var STORAGE = "ymmo-theme";
  var html = document.documentElement;
  try {
    var saved = localStorage.getItem(STORAGE);
    if (saved === "light" || saved === "dark") html.setAttribute("data-theme", saved);
  } catch (e) { /* localStorage indisponible -> on s'en passe */ }

  document.querySelectorAll(".theme-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var current = html.getAttribute("data-theme");
      var prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      var isDark = current === "dark" || (!current && prefersDark);
      var next = isDark ? "light" : "dark";
      html.setAttribute("data-theme", next);
      try { localStorage.setItem(STORAGE, next); } catch (e) {}
      btn.setAttribute("aria-pressed", String(next === "dark"));
    });
  });

  /* --- 2. Topbar : ombre quand on a scrollé un peu ----------------- */
  var topbar = document.querySelector("[data-topbar]");
  if (topbar) {
    var onScroll = function () {
      topbar.classList.toggle("is-scrolled", window.scrollY > 4);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* --- 3. Menu mobile (burger) ------------------------------------- */
  var burger = document.querySelector(".burger");
  var nav = document.getElementById("primary-nav");
  if (burger && nav) {
    burger.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", String(open));
    });
    // Ferme le menu après la navigation : sinon on garde l'overlay ouvert.
    nav.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        nav.classList.remove("is-open");
        burger.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* --- 4. Selects auto-submit (tri liste, rôle admin, agence) ----- */
  document.querySelectorAll("[data-auto-submit]").forEach(function (sel) {
    sel.addEventListener("change", function () { sel.form && sel.form.submit(); });
  });

  /* --- 5. Confirm sur les actions destructives -------------------- */
  document.querySelectorAll("[data-confirm]").forEach(function (btn) {
    btn.addEventListener("click", function (event) {
      var msg = btn.getAttribute("data-confirm");
      if (msg && !window.confirm(msg)) event.preventDefault();
    });
  });

  /* --- 6. Cases à cocher "tout sélectionner" (bulk agent) --------- */
  document.querySelectorAll("[data-select-all]").forEach(function (master) {
    master.addEventListener("change", function () {
      var form = master.form || master.closest("form");
      if (!form) return;
      form.querySelectorAll('input[type="checkbox"][name="property_ids"]').forEach(function (cb) {
        cb.checked = master.checked;
      });
    });
  });
})();
