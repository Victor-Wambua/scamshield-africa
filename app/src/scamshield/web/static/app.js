/* Small progressive-enhancement script. No third-party code, no network calls. */
(function () {
  'use strict';
  document.documentElement.classList.add('js');

  // Theme toggle
  var tt = document.querySelector('[data-theme-toggle]');
  if (tt) tt.addEventListener('click', function () {
    var cur = document.documentElement.getAttribute('data-theme');
    var dark = cur === 'dark' || (!cur && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var next = dark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('ss-theme', next); } catch (e) { /* ignore */ }
  });

  // Account menu
  var mb = document.querySelector('[data-menu]');
  var pop = document.getElementById('acct');
  if (mb && pop) {
    mb.addEventListener('click', function () {
      pop.hidden = !pop.hidden;
      mb.setAttribute('aria-expanded', String(!pop.hidden));
      if (!pop.hidden) { var f = pop.querySelector('a,button'); if (f) f.focus(); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !pop.hidden) { pop.hidden = true; mb.setAttribute('aria-expanded', 'false'); mb.focus(); }
    });
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.menu') && !pop.hidden) { pop.hidden = true; mb.setAttribute('aria-expanded', 'false'); }
    });
  }

  // Multi-step report form
  var wiz = document.querySelector('[data-wizard]');
  if (wiz) {
    var steps = Array.prototype.slice.call(wiz.querySelectorAll('.step'));
    var bar = document.querySelectorAll('.stepper li');
    var i = 0;
    var hasErr = wiz.querySelector('[aria-invalid="true"]');
    var show = function (n) {
      i = n;
      steps.forEach(function (s, k) { s.hidden = k !== n; });
      bar.forEach(function (b, k) { b.className = k < n ? 'done' : k === n ? 'now' : ''; });
      var h = steps[n].querySelector('h2'); if (h) { h.tabIndex = -1; h.focus(); }
      var back = wiz.querySelector('[data-back]'), next = wiz.querySelector('[data-next]'), sub = wiz.querySelector('[data-submit]');
      back.hidden = n === 0; next.hidden = n === steps.length - 1; sub.hidden = n !== steps.length - 1;
    };
    var valid = function (n) {
      var ok = true;
      steps[n].querySelectorAll('[required]').forEach(function (el) { if (!el.checkValidity()) { ok = false; el.reportValidity(); } });
      return ok;
    };
    wiz.querySelector('[data-next]').addEventListener('click', function () { if (valid(i)) show(i + 1); });
    wiz.querySelector('[data-back]').addEventListener('click', function () { show(i - 1); });
    wiz.noValidate = false;
    if (!hasErr) show(0); else { steps.forEach(function (s) { s.hidden = false; }); wiz.querySelector('.step-nav').hidden = true; wiz.querySelector('[data-submit-all]').hidden = false; }
    var rev = document.getElementById('review-box');
    if (rev) wiz.addEventListener('input', function () {
      var v = function (n) { var e = wiz.elements[n]; return e ? e.value : ''; };
      rev.textContent = 'Type: ' + v('itype') + '\nValue: ' + (v('value') || '(message text)') + '\nWhat happened: ' + v('description').slice(0, 120);
    });
  }

  // Copy buttons
  document.querySelectorAll('[data-copy]').forEach(function (b) {
    b.addEventListener('click', function () {
      var el = document.getElementById(b.getAttribute('data-copy'));
      if (el && navigator.clipboard) navigator.clipboard.writeText(el.textContent.trim()).then(function () { b.textContent = 'Copied'; });
    });
  });

  // Dialog openers
  document.querySelectorAll('[data-dialog]').forEach(function (b) {
    b.addEventListener('click', function () {
      var d = document.getElementById(b.getAttribute('data-dialog'));
      if (d && d.showModal) d.showModal();
    });
  });
  document.querySelectorAll('[data-close]').forEach(function (b) {
    b.addEventListener('click', function () { var d = b.closest('dialog'); if (d) d.close(); });
  });

  // Auto-submit selects (replaces inline handlers, which the CSP blocks)
  document.querySelectorAll('select[data-autosubmit]').forEach(function (sel) {
    sel.addEventListener('change', function () { if (sel.form) sel.form.submit(); });
  });

  // Confirm destructive actions
  document.querySelectorAll('[data-confirm]').forEach(function (b) {
    b.addEventListener('click', function (e) { if (!window.confirm(b.getAttribute('data-confirm'))) e.preventDefault(); });
  });
})();
