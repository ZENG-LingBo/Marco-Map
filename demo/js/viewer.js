/* Marco-Map demo viewer.
   Vanilla JavaScript on top of OpenSeadragon. Everything the page shows comes from
   data/catalogue.json and one map file (data/<map>.json). No build step.
   Keyboard: , . previous/next annotation · p play/pause tour · l translated labels ·
   e author mode · i index · ? help · Esc close. */
(function () {
  'use strict';

  var OSD_IMAGES = 'https://cdnjs.cloudflare.com/ajax/libs/openseadragon/6.1.1/images/';
  var CATEGORY = {
    cartouche: 'Cartouche', inscription: 'Inscription', toponym: 'Place name',
    diagram: 'Diagram', colophon: 'Colophon', illustration: 'Illustration'
  };

  var state = {
    catalogue: null, map: null, viewId: null, viewer: null,
    current: null, filter: 'all', labelsOn: false, labelOpacity: 0.92,
    tour: { list: [], index: -1, timer: null },
    author: { on: false, tracker: null, start: null, box: null },
    pending: null, vertical: false, els: {}
  };

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function byId(id) { return state.map.annotations.filter(function (a) { return a.id === id; })[0]; }
  function viewById(id) { return state.map.views.filter(function (v) { return v.id === id; })[0]; }

  /* ---------- URL state ---------- */
  function readHash() { return new URLSearchParams(location.hash.replace(/^#/, '')); }
  function writeHash(extra) {
    var h = new URLSearchParams();
    if (state.map) h.set('map', state.map.id);
    if (state.viewId) h.set('view', state.viewId);
    if (extra && extra.a) h.set('a', extra.a);
    else if (extra && extra.v) h.set('v', extra.v);
    history.replaceState(null, '', '#' + h.toString());
  }
  function viewportString() {
    var vp = state.viewer.viewport;
    var c = vp.viewportToImageCoordinates(vp.getCenter(true));
    return Math.round(c.x) + ',' + Math.round(c.y) + ',' + vp.getZoom(true).toFixed(3);
  }
  function applyViewport(str) {
    var p = String(str).split(',').map(Number);
    if (p.length !== 3 || p.some(isNaN)) return;
    var vp = state.viewer.viewport;
    vp.zoomTo(p[2], null, true);
    vp.panTo(vp.imageToViewportCoordinates(p[0], p[1]), true);
  }

  /* ---------- Boot ---------- */
  function boot() {
    ['osd', 'indexList', 'filter', 'readingInner', 'viewSwitch', 'tourPrev', 'tourNext', 'tourPlay',
      'tourStatus', 'labelsToggle', 'labelOpacity', 'zoomIn', 'zoomOut', 'zoomHome', 'help', 'helpToggle',
      'about', 'indexToggle', 'tooltip', 'toast', 'authorHint', 'stageNote', 'titleZh', 'titleEn',
      'mapSelect', 'workspace', 'index', 'stage', 'credit'
    ].forEach(function (id) { state.els[id] = document.getElementById(id); });

    fetch('data/catalogue.json').then(function (r) { return r.json(); }).then(function (cat) {
      state.catalogue = cat;
      var h = readHash();
      var qs = new URLSearchParams(location.search);
      var wanted = h.get('map') || qs.get('map') || cat.maps[0].id;
      var entry = cat.maps.filter(function (m) { return m.id === wanted; })[0] || cat.maps[0];
      cat.maps.forEach(function (m) {
        var o = el('option', null, (m.short && m.short.en) || m.title.en);
        o.value = m.id;
        if (m.id === entry.id) o.selected = true;
        state.els.mapSelect.appendChild(o);
      });
      state.els.mapSelect.addEventListener('change', function () {
        location.hash = 'map=' + state.els.mapSelect.value;
        location.reload();
      });
      return fetch(entry.file).then(function (r) { return r.json(); }).then(function (map) { loadMap(map, h); });
    }).catch(function (err) {
      state.els.readingInner.innerHTML = '<p class="placeholder">Could not load the demo data (' + err.message +
        '). Serve this folder over HTTP, e.g. <code>python3 -m http.server</code>, rather than opening the file directly.</p>';
    });
  }

  function loadMap(map, h) {
    state.map = map;
    map.annotations.forEach(function (a, i) { a.num = i + 1; });
    document.title = map.title.en + ' · Marco-Map demo';
    state.els.titleZh.textContent = map.title.zh;
    state.els.titleEn.textContent = map.title.en;
    state.els.credit.textContent = map.catalogue.credit;
    renderViewSwitch();
    renderIndex();
    buildTour();
    bindControls();
    initViewer();

    var a = h.get('a'), v = h.get('v');
    var viewId = viewById(h.get('view')) ? h.get('view') : map.views[0].id;
    if (a && byId(a)) {
      state.pending = { a: a };
      openView(byId(a).view);
    } else {
      state.pending = v ? { v: v } : null;
      openView(viewId);
      showAbout();
    }
  }

  /* ---------- OpenSeadragon ---------- */
  function initViewer() {
    state.viewer = OpenSeadragon({
      id: 'osd',
      prefixUrl: OSD_IMAGES,
      showNavigationControl: false,
      showNavigator: true,
      navigatorPosition: 'BOTTOM_LEFT',
      navigatorSizeRatio: 0.13,
      navigatorAutoFade: false,
      animationTime: 1.4,
      springStiffness: 6,
      visibilityRatio: 0.5,
      minZoomImageRatio: 0.6,
      maxZoomPixelRatio: 3,
      zoomPerScroll: 1.25,
      gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: true },
      gestureSettingsTouch: { clickToZoom: false },
      crossOriginPolicy: 'Anonymous',
      ajaxWithCredentials: false,
      imageLoaderLimit: 6
    });
    state.viewer.addHandler('open', onOpen);
    state.viewer.addHandler('open-failed', function (e) {
      toast('Could not load the image tiles' + (e.message ? ': ' + e.message : '.'));
    });
    state.viewer.addHandler('animation-finish', function () {
      if (!state.current) writeHash({ v: viewportString() });
    });
  }

  function openView(id) {
    var view = viewById(id);
    if (!view) return;
    state.viewId = id;
    $$('#viewSwitch .btn').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.view === id)); });
    state.els.stageNote.textContent = view.label.zh + ' · ' + view.label.en + (view.note ? ' — ' + view.note : '');
    state.viewer.clearOverlays();
    state.viewer.open(view.tileSource);
  }

  function onOpen() {
    addOverlays();
    var p = state.pending;
    state.pending = null;
    if (p && p.a) select(p.a, { zoom: true });
    else if (p && p.v) applyViewport(p.v);
    else writeHash({});
  }

  function addOverlays() {
    var vp = state.viewer.viewport;
    state.map.annotations.forEach(function (a) {
      if (a.view !== state.viewId) return;
      var r = a.region;
      var rect = vp.imageToViewportRectangle(new OpenSeadragon.Rect(r.x, r.y, r.w, r.h));

      var box = el('div', 'region');
      box.dataset.id = a.id;
      state.viewer.addOverlay({ element: box, location: rect });

      var pin = el('button', 'pin', String(a.num));
      pin.type = 'button';
      pin.dataset.id = a.id;
      pin.setAttribute('aria-label', a.label.en);
      state.viewer.addOverlay({
        element: pin,
        location: new OpenSeadragon.Point(rect.x + rect.width / 2, rect.y + rect.height / 2),
        placement: OpenSeadragon.Placement.CENTER,
        checkResize: false
      });
      new OpenSeadragon.MouseTracker({
        element: pin,
        clickHandler: function () { select(a.id, { zoom: true, stopTour: true }); }
      });
      pin.addEventListener('mouseenter', function () { showTooltip(a, pin); });
      pin.addEventListener('mouseleave', hideTooltip);

      var lab = el('div', 'label-ovl', a.label.en);
      lab.dataset.id = a.id;
      lab.style.opacity = state.labelOpacity;
      if (!state.labelsOn) lab.classList.add('hidden');
      state.viewer.addOverlay({
        element: lab,
        location: new OpenSeadragon.Point(rect.x, rect.y),
        placement: OpenSeadragon.Placement.BOTTOM_LEFT,
        checkResize: false
      });
    });
    applyFilter();
    markActive();
  }

  function fitRegion(a) {
    var r = a.region, pad = 0.35;
    var rect = state.viewer.viewport.imageToViewportRectangle(
      new OpenSeadragon.Rect(r.x - r.w * pad, r.y - r.h * pad, r.w * (1 + 2 * pad), r.h * (1 + 2 * pad)));
    state.viewer.viewport.fitBounds(rect, false);
  }

  /* ---------- Selection ---------- */
  function select(id, opts) {
    opts = opts || {};
    var a = byId(id);
    if (!a) return;
    if (opts.stopTour) stopTour();
    if (a.view !== state.viewId) {
      state.pending = { a: id };
      openView(a.view);
      return;
    }
    state.current = a;
    markActive();
    renderReading(a);
    openPanel();
    if (opts.zoom !== false) fitRegion(a);
    var i = state.tour.list.indexOf(a);
    if (i >= 0) state.tour.index = i;
    updateTourStatus();
    writeHash({ a: id });
    var li = $('.index-list li[data-id="' + id + '"]');
    if (li) li.scrollIntoView({ block: 'nearest' });
  }

  function markActive() {
    var id = state.current ? state.current.id : null;
    $$('.pin, .region, .index-list li[data-id]').forEach(function (n) {
      n.classList.toggle('is-active', n.dataset.id === id);
    });
  }

  /* ---------- Reading panel ---------- */
  function renderReading(a) {
    var root = state.els.readingInner;
    root.innerHTML = '';
    var eyebrow = el('div', 'eyebrow');
    eyebrow.appendChild(el('span', null, (CATEGORY[a.category] || a.category) + ' · no. ' + a.num + ' · ' + viewById(a.view).label.en));
    var close = el('button', 'close', 'Close ×');
    close.type = 'button';
    close.addEventListener('click', closePanel);
    eyebrow.appendChild(close);
    root.appendChild(eyebrow);

    var h2 = el('h2', 'zh', a.label.zh); h2.lang = 'zh';
    root.appendChild(h2);
    root.appendChild(el('h3', 'en', a.label.en));

    var actions = el('div', 'actions');
    var zoomBtn = el('button', 'btn', 'Zoom to region'); zoomBtn.type = 'button';
    zoomBtn.addEventListener('click', function () { fitRegion(a); });
    var linkBtn = el('button', 'btn', 'Copy link'); linkBtn.type = 'button';
    linkBtn.addEventListener('click', function () { copyText(location.href, 'Link copied'); });
    var nextBtn = el('button', 'btn', 'Next ›'); nextBtn.type = 'button';
    nextBtn.addEventListener('click', function () { tourStep(1); });
    actions.appendChild(zoomBtn); actions.appendChild(linkBtn); actions.appendChild(nextBtn);
    root.appendChild(actions);

    var t = a.text || {};
    var hasOriginal = t.original && t.original !== '(no text)';
    var tabs = [];
    if (hasOriginal) tabs.push({ key: 'original', label: t.lang === 'zh' ? '原文 Original' : 'Original' });
    if (t.translation) tabs.push({ key: 'translation', label: 'Translation' });
    if (t.commentary) tabs.push({ key: 'commentary', label: 'Commentary' });
    if (t.source && t.source.length) tabs.push({ key: 'source', label: 'Source' });

    var tablist = el('div', 'tabs'); tablist.setAttribute('role', 'tablist');
    var panels = {};
    tabs.forEach(function (tab, i) {
      var b = el('button', null, tab.label);
      b.type = 'button'; b.setAttribute('role', 'tab'); b.dataset.tab = tab.key;
      b.setAttribute('aria-selected', String(i === 0));
      b.addEventListener('click', function () {
        $$('button', tablist).forEach(function (x) { x.setAttribute('aria-selected', String(x === b)); });
        Object.keys(panels).forEach(function (k) { panels[k].hidden = k !== tab.key; });
      });
      tablist.appendChild(b);
    });
    root.appendChild(tablist);

    if (hasOriginal) {
      var p = el('div', 'tabpanel');
      var orig = el('div', 'original' + (t.lang === 'zh' ? '' : ' latin'), t.original);
      orig.lang = t.lang === 'zh' ? 'zh' : 'la';
      if (t.lang === 'zh') {
        if (state.vertical) orig.classList.add('vertical');
        var vbtn = el('button', 'btn', state.vertical ? 'Horizontal' : 'Vertical (直排)');
        vbtn.type = 'button';
        vbtn.addEventListener('click', function () {
          state.vertical = !state.vertical;
          orig.classList.toggle('vertical', state.vertical);
          vbtn.textContent = state.vertical ? 'Horizontal' : 'Vertical (直排)';
        });
        p.appendChild(vbtn);
      }
      p.appendChild(orig);
      panels.original = p; root.appendChild(p);
    }
    if (t.translation) {
      var p2 = el('div', 'tabpanel'); p2.hidden = true;
      t.translation.split('\n').forEach(function (line) { p2.appendChild(el('p', 'translation', line)); });
      panels.translation = p2; root.appendChild(p2);
    }
    if (t.commentary) {
      var p3 = el('div', 'tabpanel'); p3.hidden = true;
      t.commentary.split('\n').forEach(function (line) { p3.appendChild(el('p', 'commentary', line)); });
      panels.commentary = p3; root.appendChild(p3);
    }
    if (t.source && t.source.length) {
      var p4 = el('div', 'tabpanel source'); p4.hidden = true;
      var ol = el('ol');
      t.source.forEach(function (s) { ol.appendChild(el('li', null, s)); });
      p4.appendChild(ol);
      panels.source = p4; root.appendChild(p4);
    }
    if (!hasOriginal && panels.commentary) {
      panels.commentary.hidden = false;
      $$('button', tablist).forEach(function (x) { x.setAttribute('aria-selected', String(x.dataset.tab === 'commentary')); });
    }
    root.appendChild(catalogueBlock());
    root.appendChild(el('p', 'note', 'Demo content: transcriptions and translations are illustrative and must be checked before publication.'));
  }

  function catalogueBlock() {
    var c = state.map.catalogue;
    var wrap = el('div', 'catalogue');
    var dl = el('dl');
    [['Repository', c.repository], ['Reference', c.reference], ['Extent', c.extent], ['Digitised', c.digitised], ['Date', state.map.date], ['Credit', c.credit]]
      .forEach(function (row) {
        if (!row[1]) return;
        dl.appendChild(el('dt', null, row[0]));
        dl.appendChild(el('dd', null, row[1]));
      });
    if (c.url) {
      dl.appendChild(el('dt', null, 'Record'));
      var dd = el('dd'); var a = el('a', null, c.url.replace(/^https?:\/\//, '')); a.href = c.url; a.target = '_blank'; a.rel = 'noopener';
      dd.appendChild(a); dl.appendChild(dd);
    }
    wrap.appendChild(dl);
    return wrap;
  }

  function showAbout() {
    var root = state.els.readingInner;
    root.innerHTML = '';
    var eyebrow = el('div', 'eyebrow');
    eyebrow.appendChild(el('span', null, 'About this map'));
    var close = el('button', 'close', 'Close ×'); close.type = 'button';
    close.addEventListener('click', closePanel);
    eyebrow.appendChild(close);
    root.appendChild(eyebrow);
    var h2 = el('h2', 'zh', state.map.title.zh); h2.lang = 'zh';
    root.appendChild(h2);
    root.appendChild(el('h3', 'en', state.map.title.en));
    root.appendChild(el('p', 'sans muted', state.map.creator + ' · ' + state.map.date));
    state.map.description.split('\n').forEach(function (line) { root.appendChild(el('p', null, line)); });
    root.appendChild(el('p', 'note', 'Select a numbered pin on the map or an entry in the index to read its original text, translation and commentary. Use the buttons above the map to turn the sheet over or to follow the guided tour.'));
    root.appendChild(catalogueBlock());
    state.current = null;
    markActive();
    openPanel();
  }

  function openPanel() { state.els.workspace.classList.remove('panel-closed'); }
  function closePanel() { state.els.workspace.classList.add('panel-closed'); }

  /* ---------- Index ---------- */
  function renderIndex() {
    var list = state.els.indexList;
    list.innerHTML = '';
    state.map.views.forEach(function (v) {
      var anns = state.map.annotations.filter(function (a) { return a.view === v.id; });
      if (!anns.length) return;
      list.appendChild(el('li', 'index-group', v.label.en));
      anns.forEach(function (a) {
        var li = el('li');
        li.dataset.id = a.id; li.dataset.category = a.category; li.tabIndex = 0;
        li.appendChild(el('span', 'num', String(a.num)));
        var body = el('div');
        var zh = el('div', 'zh', a.label.zh); zh.lang = 'zh';
        body.appendChild(zh);
        var en = el('div', 'en', a.label.en);
        en.appendChild(el('span', 'cat', CATEGORY[a.category] || a.category));
        body.appendChild(en);
        li.appendChild(body);
        li.addEventListener('click', function () { select(a.id, { zoom: true, stopTour: true }); closeIndexOnMobile(); });
        li.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); li.click(); } });
        list.appendChild(li);
      });
    });
    var cats = {};
    state.map.annotations.forEach(function (a) { cats[a.category] = true; });
    var sel = state.els.filter;
    sel.innerHTML = '';
    var all = el('option', null, 'All categories'); all.value = 'all'; sel.appendChild(all);
    Object.keys(cats).forEach(function (c) { var o = el('option', null, CATEGORY[c] || c); o.value = c; sel.appendChild(o); });
    sel.addEventListener('change', function () { state.filter = sel.value; applyFilter(); });
  }

  function applyFilter() {
    var f = state.filter;
    $$('.index-list li[data-id]').forEach(function (li) { li.classList.toggle('is-hidden', f !== 'all' && li.dataset.category !== f); });
    state.map.annotations.forEach(function (a) {
      var off = f !== 'all' && a.category !== f;
      $$('.pin[data-id="' + a.id + '"]').forEach(function (p) { p.classList.toggle('is-dim', off); });
      $$('.region[data-id="' + a.id + '"], .label-ovl[data-id="' + a.id + '"]').forEach(function (n) {
        n.classList.toggle('hidden', off || (n.classList.contains('label-ovl') && !state.labelsOn));
      });
    });
  }

  /* ---------- Tour ---------- */
  function buildTour() {
    state.tour.list = state.map.annotations.filter(function (a) { return a.tour !== false; });
    state.tour.index = -1;
    updateTourStatus();
  }
  function tourStep(dir) {
    var n = state.tour.list.length;
    if (!n) return;
    state.tour.index = ((state.tour.index + dir) % n + n) % n;
    select(state.tour.list[state.tour.index].id, { zoom: true });
  }
  function playTour() {
    if (state.tour.timer) { stopTour(); return; }
    tourStep(1);
    state.tour.timer = setInterval(function () { tourStep(1); }, 7000);
    state.els.tourPlay.textContent = 'Pause';
    state.els.tourPlay.setAttribute('aria-pressed', 'true');
  }
  function stopTour() {
    if (state.tour.timer) clearInterval(state.tour.timer);
    state.tour.timer = null;
    state.els.tourPlay.textContent = 'Play tour';
    state.els.tourPlay.setAttribute('aria-pressed', 'false');
  }
  function updateTourStatus() {
    var n = state.tour.list.length;
    state.els.tourStatus.textContent = state.tour.index >= 0 ? (state.tour.index + 1) + ' / ' + n : n + ' stops';
  }

  /* ---------- View switch ---------- */
  function renderViewSwitch() {
    var wrap = state.els.viewSwitch;
    wrap.innerHTML = '';
    state.map.views.forEach(function (v) {
      var b = el('button', 'btn', v.label.zh + ' ' + v.label.en.replace(/\s*\(.*\)$/, '').replace(/:.*$/, ''));
      b.type = 'button'; b.dataset.view = v.id; b.title = v.label.en;
      b.addEventListener('click', function () {
        if (state.viewId === v.id) return;
        stopTour();
        state.current = null;
        state.pending = null;
        openView(v.id);
        showAbout();
      });
      wrap.appendChild(b);
    });
  }

  /* ---------- Labels layer ---------- */
  function toggleLabels(force) {
    state.labelsOn = force != null ? force : !state.labelsOn;
    state.els.labelsToggle.setAttribute('aria-pressed', String(state.labelsOn));
    applyFilter();
  }

  /* ---------- Author mode ---------- */
  function toggleAuthor(force) {
    var on = force != null ? force : !state.author.on;
    state.author.on = on;
    state.els.authorHint.classList.toggle('hidden', !on);
    state.viewer.setMouseNavEnabled(!on);
    if (!state.author.tracker) {
      state.author.tracker = new OpenSeadragon.MouseTracker({
        element: state.viewer.canvas,
        startDisabled: true,
        pressHandler: function (e) {
          state.author.start = state.viewer.viewport.pointFromPixel(e.position, true);
          updateBox(state.author.start, state.author.start);
        },
        dragHandler: function (e) {
          if (!state.author.start) return;
          updateBox(state.author.start, state.viewer.viewport.pointFromPixel(e.position, true));
        },
        releaseHandler: function (e) {
          if (!state.author.start) return;
          finishBox(state.author.start, state.viewer.viewport.pointFromPixel(e.position, true));
          state.author.start = null;
        }
      });
    }
    state.author.tracker.setTracking(on);
    if (!on) removeBox();
    toast(on ? 'Author mode on: drag a rectangle to copy its region' : 'Author mode off');
  }
  function rectFrom(p1, p2) {
    return new OpenSeadragon.Rect(Math.min(p1.x, p2.x), Math.min(p1.y, p2.y), Math.abs(p2.x - p1.x), Math.abs(p2.y - p1.y));
  }
  function updateBox(p1, p2) {
    var rect = rectFrom(p1, p2);
    if (!state.author.box) {
      state.author.box = el('div', 'author-box');
      state.viewer.addOverlay({ element: state.author.box, location: rect });
    } else {
      state.viewer.updateOverlay(state.author.box, rect);
    }
  }
  function removeBox() {
    if (state.author.box) { state.viewer.removeOverlay(state.author.box); state.author.box = null; }
  }
  function finishBox(p1, p2) {
    var ir = state.viewer.viewport.viewportToImageRectangle(rectFrom(p1, p2));
    var region = { x: Math.round(ir.x), y: Math.round(ir.y), w: Math.round(ir.width), h: Math.round(ir.height) };
    if (region.w < 4 || region.h < 4) { removeBox(); return; }
    var snippet = '"region": ' + JSON.stringify(region);
    window.lastRegion = region;
    console.log('[Marco-Map author mode] view=' + state.viewId + ' ' + snippet);
    copyText(snippet, 'Region copied: ' + JSON.stringify(region));
  }

  /* ---------- Small UI ---------- */
  function copyText(text, msg) {
    var done = function () { toast(msg || 'Copied'); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { window.prompt('Copy:', text); });
    } else { window.prompt('Copy:', text); }
  }
  var toastTimer = null;
  function toast(msg) {
    var t = state.els.toast;
    t.textContent = msg;
    t.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('is-on'); }, 2600);
  }
  function showTooltip(a, pin) {
    var tip = state.els.tooltip;
    tip.innerHTML = '';
    var zh = el('span', 'zh', a.label.zh); zh.lang = 'zh';
    tip.appendChild(zh);
    tip.appendChild(document.createTextNode(a.label.en));
    tip.classList.remove('hidden');
    var sr = state.els.stage.getBoundingClientRect();
    var pr = pin.getBoundingClientRect();
    tip.style.left = Math.min(pr.right - sr.left + 8, sr.width - tip.offsetWidth - 8) + 'px';
    tip.style.top = Math.max(8, pr.top - sr.top - 8) + 'px';
  }
  function hideTooltip() { state.els.tooltip.classList.add('hidden'); }
  function toggleHelp(force) {
    var h = state.els.help;
    var show = force != null ? force : h.classList.contains('hidden');
    h.classList.toggle('hidden', !show);
    state.els.helpToggle.setAttribute('aria-expanded', String(show));
  }
  function toggleIndex() {
    if (window.matchMedia('(max-width: 768px)').matches) state.els.index.classList.toggle('is-open');
    else state.els.workspace.classList.toggle('index-hidden');
  }
  function closeIndexOnMobile() { state.els.index.classList.remove('is-open'); }

  function bindControls() {
    var e = state.els;
    e.tourPrev.addEventListener('click', function () { stopTour(); tourStep(-1); });
    e.tourNext.addEventListener('click', function () { stopTour(); tourStep(1); });
    e.tourPlay.addEventListener('click', playTour);
    e.labelsToggle.addEventListener('click', function () { toggleLabels(); });
    e.labelOpacity.addEventListener('input', function () {
      state.labelOpacity = Number(e.labelOpacity.value);
      $$('.label-ovl').forEach(function (n) { n.style.opacity = state.labelOpacity; });
    });
    e.zoomIn.addEventListener('click', function () { state.viewer.viewport.zoomBy(1.5); });
    e.zoomOut.addEventListener('click', function () { state.viewer.viewport.zoomBy(1 / 1.5); });
    e.zoomHome.addEventListener('click', function () { state.viewer.viewport.goHome(); });
    e.helpToggle.addEventListener('click', function () { toggleHelp(); });
    e.about.addEventListener('click', showAbout);
    e.indexToggle.addEventListener('click', toggleIndex);

    document.addEventListener('keydown', function (ev) {
      var tag = (ev.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'select' || tag === 'textarea' || ev.metaKey || ev.ctrlKey || ev.altKey) return;
      switch (ev.key) {
        case '.': case ']': stopTour(); tourStep(1); break;
        case ',': case '[': stopTour(); tourStep(-1); break;
        case 'p': playTour(); break;
        case 'l': toggleLabels(); break;
        case 'e': toggleAuthor(); break;
        case 'i': toggleIndex(); break;
        case '?': toggleHelp(); break;
        case 'h': state.viewer.viewport.goHome(); break;
        case 'Escape':
          if (!e.help.classList.contains('hidden')) toggleHelp(false);
          else if (state.author.on) toggleAuthor(false);
          else closePanel();
          break;
        default: return;
      }
      ev.preventDefault();
    });
    window.addEventListener('hashchange', function () {
      var h = readHash();
      if (h.get('map') && state.map && h.get('map') !== state.map.id) { location.reload(); return; }
      var a = h.get('a');
      if (a && byId(a) && (!state.current || state.current.id !== a)) select(a, { zoom: true, stopTour: true });
    });
  }

  window.MarcoMapViewer = { state: state, select: select, openView: openView, toggleAuthor: toggleAuthor, toggleLabels: toggleLabels, tourStep: tourStep };
  document.addEventListener('DOMContentLoaded', boot);
})();
