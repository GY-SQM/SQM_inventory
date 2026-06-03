/* =======================================================================
   SQM menu visibility hardening
   - Keeps cascading submenus readable and inside the viewport.
   - Gives child menus a distinct surface from their parent menu.
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_MENU_FIX__) return;
  window.__SQM_MENU_FIX__ = true;

  var VIEWPORT_GAP = 8;

  function resetRootDropdown(dropdown) {
    dropdown.style.left = '';
    dropdown.style.right = '';
    dropdown.style.maxHeight = '';
    dropdown.style.overflowY = '';
  }

  function fitRootDropdown(dropdown) {
    if (!dropdown) return;
    resetRootDropdown(dropdown);

    var viewportW = window.innerWidth || document.documentElement.clientWidth || 1200;
    var viewportH = window.innerHeight || document.documentElement.clientHeight || 800;
    var rect = dropdown.getBoundingClientRect();

    if (rect.right > viewportW - VIEWPORT_GAP) {
      dropdown.style.left = 'auto';
      dropdown.style.right = '0';
      rect = dropdown.getBoundingClientRect();
    }

    var maxH = Math.max(180, viewportH - rect.top - VIEWPORT_GAP);
    dropdown.style.maxHeight = maxH + 'px';
    dropdown.style.overflowY = rect.height > maxH ? 'auto' : 'visible';
  }

  function resetSubmenu(submenu) {
    submenu.classList.remove('open-left');
    submenu.style.top = '';
    submenu.style.left = '';
    submenu.style.right = '';
    submenu.style.maxHeight = '';
    submenu.style.overflowY = '';
  }

  function fitSubmenu(parent) {
    if (!parent) return;
    var submenu = parent.querySelector(':scope > .submenu-dropdown');
    if (!submenu) return;

    resetSubmenu(submenu);

    var viewportW = window.innerWidth || document.documentElement.clientWidth || 1200;
    var viewportH = window.innerHeight || document.documentElement.clientHeight || 800;
    var parentRect = parent.getBoundingClientRect();

    submenu.style.display = 'block';
    var rect = submenu.getBoundingClientRect();

    if (rect.right > viewportW - VIEWPORT_GAP && parentRect.left > rect.width + VIEWPORT_GAP) {
      submenu.classList.add('open-left');
      rect = submenu.getBoundingClientRect();
    }

    var overflowBottom = rect.bottom - (viewportH - VIEWPORT_GAP);
    var nextTop = -5;
    if (overflowBottom > 0) nextTop -= overflowBottom;

    var minTop = VIEWPORT_GAP - parentRect.top;
    if (nextTop < minTop) nextTop = minTop;
    submenu.style.top = Math.round(nextTop) + 'px';

    rect = submenu.getBoundingClientRect();
    var maxH = Math.max(180, viewportH - VIEWPORT_GAP - Math.max(VIEWPORT_GAP, rect.top));
    submenu.style.maxHeight = maxH + 'px';
    submenu.style.overflowY = rect.height > maxH ? 'auto' : 'visible';
  }

  function installMenuFix() {
    document.querySelectorAll('.menu-btn[data-menu]').forEach(function (menuBtn) {
      if (menuBtn.dataset.sqmMenuFixBound) return;
      menuBtn.dataset.sqmMenuFixBound = '1';

      var dropdown = menuBtn.querySelector(':scope > .menu-dropdown');
      if (!dropdown) return;

      ['mouseenter', 'focusin', 'click'].forEach(function (eventName) {
        menuBtn.addEventListener(eventName, function () {
          requestAnimationFrame(function () { fitRootDropdown(dropdown); });
        }, true);
      });
    });

    document.querySelectorAll('.submenu-parent').forEach(function (parent) {
      if (parent.dataset.sqmSubmenuFixBound) return;
      parent.dataset.sqmSubmenuFixBound = '1';

      ['mouseenter', 'focusin'].forEach(function (eventName) {
        parent.addEventListener(eventName, function () {
          requestAnimationFrame(function () { fitSubmenu(parent); });
        }, true);
      });

      var btn = parent.querySelector(':scope > .submenu-parent-btn');
      if (btn) {
        btn.addEventListener('click', function () {
          requestAnimationFrame(function () { fitSubmenu(parent); });
        }, true);
      }
    });
  }

  function refreshOpenMenus() {
    document.querySelectorAll('.menu-btn.open > .menu-dropdown, .menu-btn:hover > .menu-dropdown').forEach(fitRootDropdown);
    document.querySelectorAll('.submenu-parent.open, .submenu-parent:hover').forEach(fitSubmenu);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installMenuFix);
  } else {
    installMenuFix();
  }

  window.addEventListener('resize', refreshOpenMenus);
  window.SQM = window.SQM || {};
  window.SQM.fitMenus = refreshOpenMenus;
})();
