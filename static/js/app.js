(function () {
  "use strict";

  function guestStats() {
    try {
      var raw = sessionStorage.getItem("ll_guest_progress_v1");
      if (!raw) return { xp: 0, n: 0 };
      var o = JSON.parse(raw);
      var done = o.done && typeof o.done === "object" ? o.done : {};
      return { xp: o.xp || 0, n: Object.keys(done).length };
    } catch (e) {
      return { xp: 0, n: 0 };
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.getElementById("navToggle");
    var nav = document.querySelector(".site-header .nav");
    if (toggle && nav) {
      toggle.addEventListener("click", function () {
        nav.classList.toggle("is-open");
      });
    }

    var gx = document.getElementById("guest-xp");
    var gd = document.getElementById("guest-done");
    if (gx && gd) {
      var s = guestStats();
      gx.textContent = String(s.xp);
      gd.textContent = String(s.n);
    }

    var big = document.querySelector(".stat-big[data-counter]");
    if (big) {
      var target = parseInt(big.getAttribute("data-counter") || "0", 10);
      if (!isNaN(target) && target > 0) {
        var start = 0;
        var duration = 600;
        var t0 = performance.now();
        function frame(now) {
          var p = Math.min(1, (now - t0) / duration);
          var eased = 1 - Math.pow(1 - p, 3);
          big.textContent = String(Math.round(start + (target - start) * eased));
          if (p < 1) requestAnimationFrame(frame);
        }
        requestAnimationFrame(frame);
      }
    }
    // Мобильное меню
    const menuBtn = document.getElementById('mobileMenuBtn');
    const overlay = document.getElementById('mobileOverlay');
    const sidebar = document.querySelector('.app-sidebar');
    const duoSidebar = document.querySelector('.duo-sidebar');

    function toggleMenu() {
      if (sidebar) sidebar.classList.toggle('open');
      if (duoSidebar) duoSidebar.classList.toggle('open');
      document.body.classList.toggle('menu-open');
    }

    function closeMenu() {
      if (sidebar) sidebar.classList.remove('open');
      if (duoSidebar) duoSidebar.classList.remove('open');
      document.body.classList.remove('menu-open');
    }

    if (menuBtn) {
      menuBtn.addEventListener('click', toggleMenu);
    }
    if (overlay) {
      overlay.addEventListener('click', closeMenu);
    }
  });
})();
