/* ============================================================================
 * chronicle.js  ·  FamilyHub — "CHRONICLE" — ANTIQUE / EXPEDITION home page
 * Sample data, render functions (dossier, contact sheet, collections, wall,
 * the MAP-ROUTE timeline), sticky masthead, mobile menu, scroll-reveal, a
 * catalog search, and the year stamp. Vanilla JS.
 *
 * CSP COMPLIANCE NOTE: The original static build used inline style attributes
 * (style="--p1:...; --p2:...") for sepia photo tones and tree node positions.
 * FamilyHub's strict Content-Security-Policy (style-src 'self', no
 * 'unsafe-inline') blocks those. Fix: store values in data-p1/data-p2 and
 * data-x/data-y, then apply via element.style.setProperty() and
 * element.style.left — direct property writes ARE allowed by CSP.
 *
 * -> WGU: JavaScript Programming (D280), Back-End (D286+), Security (D315)
 * ==========================================================================*/

'use strict';

/* 0) SAMPLE DATA (GEDCOM-7-shaped; `tones` tint the sepia photo placeholders) */
const SAMPLE_DATA = {
  people: [
    { given: 'Mateo',  surname: 'Rivera', birth: 2017, living: true,  rel: 'Newest record',     place: 'Spring Hill, TN', tones: ['#caa066', '#43301a'] },
    { given: 'Sofía',  surname: 'Rivera', birth: 1989, living: true,  rel: 'Mother',            place: 'Spring Hill, TN', tones: ['#c0894c', '#3a2714'] },
    { given: 'Diego',  surname: 'Rivera', birth: 1986, living: true,  rel: 'Father',            place: 'Franklin, TN',    tones: ['#b07c43', '#33230f'] },
    { given: 'Grace',  surname: 'Okafor', birth: 1958, living: true,  rel: 'Grandmother',       place: 'Nashville, TN',   tones: ['#c79355', '#3c2815'] },
    { given: 'Elias',  surname: 'Okafor', birth: 1955, living: true,  rel: 'Grandfather',       place: 'Nashville, TN',   tones: ['#a9763f', '#2e1f0e'] },
    { given: 'Rosa',   surname: 'Vega',   birth: 1951, death: 2019,   living: false, rel: 'Great-grandmother', place: 'San Antonio, TX', tones: ['#bd8a4e', '#3d2a16'] },
    { given: 'Javier', surname: 'Vega',   birth: 1948, death: 2011,   living: false, rel: 'Great-grandfather', place: 'San Antonio, TX', tones: ['#9c6e3a', '#2c1d0d'] },
    { given: 'Lena',   surname: 'Okafor', birth: 2015, living: true,  rel: 'Cousin',            place: 'Columbia, TN',    tones: ['#ca9a60', '#42301b'] }
  ],
  families: [
    { name: 'Rivera', location: 'Spring Hill, TN', count: 5, extra: 2, faces: [['#caa066','#43301a'],['#c0894c','#3a2714'],['#b07c43','#33230f']], label: ['MR','SR','DR'] },
    { name: 'Okafor', location: 'Nashville, TN',   count: 7, extra: 4, faces: [['#c79355','#3c2815'],['#a9763f','#2e1f0e'],['#ca9a60','#42301b']], label: ['GO','EO','LO'] },
    { name: 'Vega',   location: 'San Antonio, TX', count: 9, extra: 6, faces: [['#bd8a4e','#3d2a16'],['#9c6e3a','#2c1d0d'],['#b88347','#382612']], label: ['RV','JV','MV'] }
  ],
  dossier: {
    given: 'Rosa', surname: 'Vega', mono: 'RV', tones: ['#bd8a4e', '#34230f'], file: 'FILE NO. 0247',
    fields: [
      ['NAME', 'Rosa María Vega'], ['BORN', 'May 1951 · San Antonio, TX'],
      ['DIED', 'Mar 2019 · Spring Hill, TN'], ['ROLE', 'Great-grandmother'], ['FILED', '38 yrs · schoolteacher']
    ],
    quote: 'She kept a tin of butter cookies on the top shelf and a story for every one of us. The whole family ran on Sunday afternoons at Rosa's table.',
    by: '— Narrated by Sofía Rivera, 2024'
  },
  events: [
    { year: 1948, title: 'Javier Vega is born',             place: 'San Antonio, TX', cap: 'Javier, age 3',  tones: ['#9c6e3a', '#2c1d0d'] },
    { year: 1962, title: 'Rosa & Javier are married',       place: 'San Antonio, TX', cap: 'The wedding',    tones: ['#bd8a4e', '#3d2a16'] },
    { year: 1986, title: 'Diego Rivera is born',            place: 'Franklin, TN',    cap: 'Baby Diego',     tones: ['#b07c43', '#33230f'] },
    { year: 2013, title: 'Sofía & Diego are married',       place: 'Nashville, TN',   cap: 'Sofía & Diego',  tones: ['#c0894c', '#3a2714'] },
    { year: 2016, title: 'The family moves to Spring Hill', place: 'Spring Hill, TN', cap: 'Moving day',     tones: ['#a9763f', '#2e1f0e'] },
    { year: 2017, title: 'Mateo Rivera is born',            place: 'Spring Hill, TN', cap: 'Mateo arrives',  tones: ['#caa066', '#43301a'] }
  ],
  photos: [
    { kind: 'photo', cap: 'Sunday at Rosa's', date: 'c. 1971', size: 'cell--wide cell--tall', tones: ['#bd8a4e','#3a2714'] },
    { kind: 'photo', cap: 'Wedding day',      date: '1962',    size: '', tones: ['#c0894c','#33230f'] },
    { kind: 'photo', cap: 'First steps',      date: '2018',    size: '', tones: ['#caa066','#43301a'] },
    { kind: 'note',  q: '"Abuelo taught me to whistle on the porch in San Antonio."', by: '— Diego, 1992', size: 'cell--wide' },
    { kind: 'photo', cap: 'The lake house',   date: '2003',    size: '', tones: ['#a9763f','#2e1f0e'] },
    { kind: 'photo', cap: 'Graduation',       date: '2011',    size: '', tones: ['#b88347','#382612'] }
  ]
};

/* Old-map marker icons (inherit the marker's color via currentColor). */
const MARKERS = [
  "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><circle cx='12' cy='12' r='9'/><path d='M15.5 8.5 L10.5 10.5 L8.5 15.5 L13.5 13.5 Z' fill='currentColor' stroke='none'/></svg>",
  "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.6' stroke-linecap='round'><path d='M6 6 L18 18 M18 6 L6 18'/></svg>",
  "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round'><path d='M7 21 V4'/><path d='M7 5 H18 L15 9 L18 13 H7' fill='currentColor' stroke='none'/></svg>",
  "<svg viewBox='0 0 24 24' fill='currentColor'><path d='M2 21 L9 7 L13 14 L16 10 L22 21 Z'/></svg>",
  "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round'><circle cx='12' cy='5' r='2'/><path d='M12 7 V21 M4 13 a8 8 0 0 0 16 0 M3 13 h3 M18 13 h3'/></svg>",
  "<svg viewBox='0 0 24 24' fill='currentColor'><path d='M12 2 C8 2 5 5 5 9 c0 5 7 13 7 13 s7 -8 7 -13 c0 -4 -3 -7 -7 -7 Z'/></svg>"
];

/* 1) HELPERS */

/* CSP-SAFE photo tone application.
 * The CSP (style-src 'self') blocks inline style="..." on elements. Instead
 * we store tones in data-p1/data-p2 attributes and apply them here via
 * element.style.setProperty(), which bypasses the style-src restriction.
 * Call this after ANY innerHTML insertion that contains .photo elements. */
function applyTones(root) {
  (root || document).querySelectorAll('.photo[data-p1]').forEach(function(el) {
    el.style.setProperty('--p1', el.dataset.p1);
    el.style.setProperty('--p2', el.dataset.p2);
  });
}

/* Builds a sepia photo placeholder div. Tones stored as data attributes
 * so the CSP-safe applyTones() sweep can pick them up after insertion. */
function photo(mono, tones, cls) {
  cls = cls || '';
  return '<div class="photo ' + cls + '" data-p1="' + tones[0] + '" data-p2="' + tones[1] + '">' +
         (mono ? '<span class="photo__mono" aria-hidden="true">' + mono + '</span>' : '') + '</div>';
}

function initials(g, s) { return (g[0] + (s ? s[0] : '')).toUpperCase(); }
function lifespan(p) { return p.living ? 'b. ' + p.birth : p.birth + '–' + (p.death || ''); }
function pad(n, w) { w = w || 2; return String(n).padStart(w, '0'); }

document.addEventListener('DOMContentLoaded', function() {

  /* INIT: apply positions and tones to statically rendered tree nodes.
   * Tree nodes use data-x/data-y instead of inline style (CSP compliance);
   * tree photo placeholders use data-p1/data-p2 instead of inline style. */
  document.querySelectorAll('.node[data-x]').forEach(function(el) {
    el.style.left = el.dataset.x;
    el.style.top  = el.dataset.y;
  });
  applyTones(); /* covers all static .photo[data-p1] in the tree section */

  /* 0) INTRO SPLASH — play the tree animation, then FLIP the logo up into the
   * nav so it lands exactly on the real nav logo. Skippable; skipped entirely
   * under prefers-reduced-motion. -> WGU: JavaScript Programming (D280). */
  (function intro() {
    var splash = document.getElementById('splash');
    if (!splash) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { splash.remove(); return; }
    var vid    = document.getElementById('splashVid');
    var logoEl = document.getElementById('splashLogo');
    var skip   = document.getElementById('splashSkip');
    var done   = false;
    document.body.style.overflow = 'hidden';
    var finish = function() {
      if (done) return; done = true;
      splash.style.transition = 'opacity 0.5s ease'; splash.style.opacity = '0';
      document.body.style.overflow = '';
      setTimeout(function() { splash.remove(); }, 560);
    };
    var flyToNav = function() {
      var nav = document.querySelector('.site-header .brand__mark');
      if (nav && logoEl) {
        var t = nav.getBoundingClientRect(), b = logoEl.getBoundingClientRect();
        if (b.width) {
          var sc = t.width / b.width;
          var dx = (t.left + t.width / 2) - (b.left + b.width / 2);
          var dy = (t.top + t.height / 2) - (b.top + b.height / 2);
          logoEl.style.transform = 'translate(' + dx.toFixed(1) + 'px, ' + dy.toFixed(1) + 'px) scale(' + sc.toFixed(3) + ')';
        }
      }
      splash.classList.add('is-bg-out');
      setTimeout(finish, 1000);
    };
    var bloomThenFly = function() { splash.classList.add('is-crossfade'); setTimeout(flyToNav, 600); };
    var t1 = setTimeout(bloomThenFly, 2400);
    if (vid) { vid.play().catch(function() {}); }
    var doSkip = function() { clearTimeout(t1); finish(); };
    if (skip) skip.addEventListener('click', doSkip);
    document.addEventListener('keydown', function(e) { if (e.key === 'Escape') doSkip(); });
  })();

  /* 2) RENDER: DOSSIER */
  var dossierEl = document.getElementById('dossier');
  if (dossierEl) {
    var d = SAMPLE_DATA.dossier;
    var rows = d.fields.map(function(kv) {
      return '<div class="row"><span class="k">' + kv[0] + '</span><span class="v">' + kv[1] + '</span></div>';
    }).join('');
    dossierEl.innerHTML =
      '<div class="dossier">' +
        '<div class="dossier__photo">' +
          photo(d.mono, d.tones) +
          '<div class="dossier__file">' + d.file + '</div>' +
        '</div>' +
        '<div class="dossier__body">' +
          '<h3>' + d.given + ' ' + d.surname + '</h3>' +
          '<div class="dossier__fields">' + rows + '</div>' +
          '<blockquote class="dossier__quote">' + d.quote + '<cite>' + d.by + '</cite></blockquote>' +
        '</div>' +
      '</div>';
    applyTones(dossierEl);
  }

  /* 3) RENDER: PEOPLE CONTACT SHEET */
  var sheet = document.getElementById('peopleSheet');
  if (sheet) {
    sheet.innerHTML = SAMPLE_DATA.people.map(function(p, i) {
      return '<a class="frame-card reveal" href="#" aria-label="' + p.given + ' ' + p.surname + ', ' + p.rel + '">' +
        photo(initials(p.given, p.surname), p.tones) +
        '<div class="frame-card__no"><span>FRAME ' + pad(i + 1) + '</span><span>&#8599;</span></div>' +
        '<div class="frame-card__name">' + p.given + ' ' + p.surname + '</div>' +
        '<div class="frame-card__life">' + lifespan(p) + ' &middot; ' + p.place + '</div>' +
        '<span class="frame-card__rel">' + p.rel + '</span>' +
      '</a>';
    }).join('');
    applyTones(sheet);
  }

  /* 4) RENDER: FAMILY COLLECTIONS */
  var collections = document.getElementById('collections');
  if (collections) {
    collections.innerHTML = SAMPLE_DATA.families.map(function(f, i) {
      var faces = f.faces.map(function(t, j) { return photo(f.label[j] || '', t); }).join('');
      return '<a class="collection reveal" href="#" aria-label="The ' + f.name + ' family collection">' +
        '<div class="collection__no">COLLECTION ' + pad(i + 1) + '</div>' +
        '<div class="collection__name">The ' + f.name + 's</div>' +
        '<div class="collection__faces">' + faces + '<span class="more">+' + f.extra + '</span></div>' +
        '<div class="collection__meta">' + f.location + ' &middot; ' + f.count + ' records</div>' +
      '</a>';
    }).join('');
    applyTones(collections);
  }

  /* 5) RENDER: PHOTO WALL + FIELD NOTE */
  var wall = document.getElementById('wall');
  if (wall) {
    wall.innerHTML = SAMPLE_DATA.photos.map(function(m) {
      if (m.kind === 'note') {
        return '<figure class="cell cell--note ' + m.size + '">' +
          '<div class="tag">Field note</div>' +
          '<blockquote class="q">' + m.q + '</blockquote>' +
          '<figcaption class="by">' + m.by + '</figcaption>' +
        '</figure>';
      }
      return '<figure class="cell ' + m.size + '">' +
        photo('', m.tones) +
        '<figcaption class="cell__cap"><span class="t">' + m.cap + '</span><span class="d">' + m.date + '</span></figcaption>' +
      '</figure>';
    }).join('');
    applyTones(wall);
  }

  /* 6) RENDER: THE ROUTE (map timeline) + hover photo-pop */
  var trail = document.getElementById('trailList');
  if (trail) {
    trail.innerHTML = SAMPLE_DATA.events.map(function(e, i) {
      return '<li class="trail-row" tabindex="0"' +
          ' data-cap="' + e.cap + '" data-year="' + e.year + '"' +
          ' data-p1="' + e.tones[0] + '" data-p2="' + e.tones[1] + '"' +
          ' aria-label="' + e.year + ': ' + e.title + ', ' + e.place + '. Has a photograph — hover or focus to view.">' +
        '<span class="trail-row__marker" aria-hidden="true">' + MARKERS[i % MARKERS.length] + '</span>' +
        '<span class="trail-row__year">' + e.year + '</span>' +
        '<span class="trail-row__title">' + e.title + '</span>' +
        '<span class="trail-row__meta">' + e.place + '</span>' +
        '<span class="trail-row__cue">view</span>' +
      '</li>';
    }).join('');

    var pop = document.createElement('figure');
    pop.className = 'tl-pop';
    document.body.appendChild(pop);
    var active = null;

    var show = function(row) {
      /* Build the pop using data-p1/data-p2 on the photo div, then apply
       * tones via applyTones() — CSP-safe, no inline style attributes. */
      pop.innerHTML =
        '<div class="photo" data-p1="' + row.dataset.p1 + '" data-p2="' + row.dataset.p2 + '"></div>' +
        '<figcaption><span class="t">' + row.dataset.cap + '</span><span class="d">' + row.dataset.year + '</span></figcaption>';
      applyTones(pop);
      pop.classList.add('is-on');
    };
    var hide = function() { pop.classList.remove('is-on'); active = null; };
    var place = function(x, y) {
      var w = 212, h = pop.offsetHeight || 180, padpx = 14;
      var nx = x + 18; if (nx + w + padpx > window.innerWidth) nx = x - w - 18;
      var ny = Math.max(padpx, Math.min(y - h / 2, window.innerHeight - h - padpx));
      pop.style.left = nx + 'px'; pop.style.top = ny + 'px';
    };
    trail.querySelectorAll('.trail-row').forEach(function(row) {
      row.addEventListener('pointerenter', function(e) { active = row; show(row); place(e.clientX, e.clientY); });
      row.addEventListener('pointermove',  function(e) { if (active === row) place(e.clientX, e.clientY); });
      row.addEventListener('pointerleave', hide);
      row.addEventListener('focus', function() {
        active = row; show(row);
        var r = row.getBoundingClientRect();
        place(r.left + r.width * 0.5, r.top + r.height / 2);
      });
      row.addEventListener('blur', hide);
    });
    window.addEventListener('scroll', function() { if (active) hide(); }, { passive: true });
  }

  /* 7) STICKY MASTHEAD */
  var header = document.getElementById('siteHeader');
  var onScroll = function() { header.classList.toggle('is-scrolled', window.scrollY > 20); };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  /* 8) MOBILE MENU TOGGLE */
  var toggle = document.getElementById('navToggle');
  var links  = document.getElementById('navLinks');
  if (toggle && links) {
    var setIcon = function(open) {
      toggle.innerHTML = '<i aria-hidden="true">' + (open ? '&#10005;' : '&#9776;') + '</i>';
      toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    };
    toggle.addEventListener('click', function() {
      var open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open)); setIcon(open);
    });
    links.querySelectorAll('a').forEach(function(a) {
      a.addEventListener('click', function() {
        links.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
        setIcon(false);
      });
    });
  }

  /* 9) SCROLL-REVEAL */
  var revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && revealEls.length) {
    var observer = new IntersectionObserver(function(entries, obs) {
      entries.forEach(function(entry, i) {
        if (entry.isIntersecting) {
          entry.target.style.transitionDelay = (i % 6) * 70 + 'ms';
          entry.target.classList.add('is-visible');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(function(el) { observer.observe(el); });
  } else {
    revealEls.forEach(function(el) { el.classList.add('is-visible'); });
  }

  /* 10) RUNNING TIMECODE (the "restoring" readout on the film plate) */
  var tc = document.getElementById('timecode');
  if (tc) {
    var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var f = 0;
    var format = function(frames) {
      var ff = frames % 24, s = Math.floor(frames / 24) % 60,
          m = Math.floor(frames / 1440) % 60, h = Math.floor(frames / 86400) % 100;
      return pad(h) + ':' + pad(m) + ':' + pad(s) + ':' + pad(ff);
    };
    if (reduced) { tc.textContent = format(1287); }
    else { setInterval(function() { f += 3; tc.textContent = format(f); }, 100); }
  }

  /* 10b) BACKGROUND PARALLAX — the vintage map drifts as you scroll. */
  var mapscene = document.querySelector('.mapscene');
  if (mapscene && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var mraf = null;
    var drift = function() {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var prog = max > 0 ? window.scrollY / max : 0;
      mapscene.style.transform = 'translateY(' + (prog * 230).toFixed(1) + 'px)';
      mraf = null;
    };
    window.addEventListener('scroll', function() { if (!mraf) mraf = requestAnimationFrame(drift); }, { passive: true });
    drift();
  }

  /* 10c) TREE CURSOR PARALLAX */
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches &&
      window.matchMedia('(hover: hover)').matches) {
    var tl = document.querySelectorAll('.tree [data-depth]');
    if (tl.length) {
      var tx = 0, ty = 0, traf = null;
      var ta = function() {
        tl.forEach(function(el) {
          var depth = parseFloat(el.getAttribute('data-depth')) || 0;
          el.style.transform = 'translate(' + (tx * depth).toFixed(1) + 'px, ' + (ty * depth).toFixed(1) + 'px)';
        });
        traf = null;
      };
      window.addEventListener('pointermove', function(e) {
        tx = (e.clientX / window.innerWidth - 0.5) * -50;
        ty = (e.clientY / window.innerHeight - 0.5) * -50;
        if (!traf) traf = requestAnimationFrame(ta);
      }, { passive: true });
    }
  }

  /* 11) CATALOG SEARCH (front-end only) */
  var form  = document.getElementById('searchForm');
  var input = document.getElementById('searchInput');
  var hint  = document.getElementById('searchHint');
  if (form && input && hint) {
    var index = [];
    SAMPLE_DATA.people.forEach(function(p) {
      index.push({ t: p.given + ' ' + p.surname, c: 'person' });
      index.push({ t: p.place, c: 'place' });
    });
    SAMPLE_DATA.families.forEach(function(f) {
      index.push({ t: f.name, c: 'person' });
      index.push({ t: f.location, c: 'place' });
    });
    SAMPLE_DATA.events.forEach(function(e) {
      index.push({ t: e.title + ' ' + e.year + ' ' + e.place + ' ' + e.cap, c: 'record' });
    });
    SAMPLE_DATA.photos.forEach(function(m) {
      index.push({ t: (m.cap || '') + ' ' + (m.q || '') + ' ' + (m.date || ''), c: 'record' });
    });

    var DEFAULT = '<b>248</b> records &middot; <b>63</b> collections &middot; <b>1,412</b> photographs on file.';
    var run = function(raw) {
      var q = raw.trim().toLowerCase();
      if (!q) { hint.innerHTML = DEFAULT; return; }
      var hits = index.filter(function(x) { return x.t && x.t.toLowerCase().includes(q); });
      if (!hits.length) {
        hint.innerHTML = 'No catalog match for <b>' + raw + '</b> in this preview &mdash; the full archive searches all 248 records.';
        return;
      }
      var people  = hits.filter(function(h) { return h.c === 'person'; }).length;
      var places  = hits.filter(function(h) { return h.c === 'place';  }).length;
      var records = hits.filter(function(h) { return h.c === 'record'; }).length;
      var parts = [];
      if (people)  parts.push('<b>' + people  + '</b> ' + (people  === 1 ? 'person'  : 'people'));
      if (places)  parts.push('<b>' + places  + '</b> ' + (places  === 1 ? 'place'   : 'places'));
      if (records) parts.push('<b>' + records + '</b> ' + (records === 1 ? 'record'  : 'records'));
      hint.innerHTML = 'Found ' + parts.join(' &middot; ') + ' for <b>' + raw + '</b>.';
    };
    input.addEventListener('input', function() { run(input.value); });
    form.addEventListener('submit', function(e) { e.preventDefault(); run(input.value); });
    document.querySelectorAll('.chip').forEach(function(chip) {
      chip.addEventListener('click', function() { input.value = chip.dataset.q; run(input.value); input.focus(); });
    });
  }

  /* 12) CURRENT YEAR */
  document.querySelectorAll('#year').forEach(function(el) { el.textContent = new Date().getFullYear(); });

});
