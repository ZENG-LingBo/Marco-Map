/* Marco-Map demo viewer.
   Vanilla JavaScript on top of OpenSeadragon. Everything the page shows comes from
   data/catalogue.json and one map file (data/<map>.json). No build step.
   Keyboard: , . previous/next annotation · p play/pause tour · l translated labels ·
   e author mode · i index · f full screen · ? help · Esc close. */
(function () {
  'use strict';

  var OSD_IMAGES = 'https://cdnjs.cloudflare.com/ajax/libs/openseadragon/6.1.1/images/';
  var CATEGORY = {
    cartouche: 'Cartouche', inscription: 'Inscription', toponym: 'Place name',
    diagram: 'Diagram', colophon: 'Colophon', illustration: 'Illustration',
    cardinal: 'Cardinal point', passage: 'Passage', numeral: 'Number', placename: 'Towns, rivers and lakes', graticule: 'Degree numbers'
  };
  /* Maps from the existing site's catalogue (data/collection.json) are addressed as #map=tartary-<n>. */
  var COLLECTION_PREFIX = 'tartary-';
  /* Its tiles are in an S3 bucket that sends the CORS header (and Vary: Origin) only when a request
     asks for it. A browser that has cached a tile fetched without CORS, as the existing site fetches
     them, can reuse that copy for this viewer's CORS request, which then fails (seen in a browser that
     does not partition its cache by site; most current browsers do). A query string of our
     own gives these requests their own cache entries; OpenSeadragon carries a query on the .dzi URL
     over to every tile URL, and S3 ignores it. Not needed once the tiles are served with the CORS
     header on every response (docs/01-migration-runbook.md, step 5). */
  var COLLECTION_TILE_QUERY = '?viewer=marco-map';
  /* The phone layout (the same query is in css/demo.css): narrow screens, and phones held sideways. */
  var PHONE = '(max-width: 768px), (max-height: 500px) and (pointer: coarse)';

  var state = {
    catalogue: null, map: null, viewId: null, viewer: null,
    current: null, filter: 'all', labelsOn: false, labelOpacity: 0.92,
    tour: { list: [], timer: null },
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
  /* The original-language form of a title or label: Chinese (zh), Latin (la), Russian (ru) or French (fr). Collection maps have none. */
  function origOf(obj) {
    if (obj && obj.zh) return { text: obj.zh, lang: 'zh' };
    if (obj && obj.la) return { text: obj.la, lang: 'la' };
    if (obj && obj.ru) return { text: obj.ru, lang: 'ru' };
    if (obj && obj.fr) return { text: obj.fr, lang: 'fr' };
    return null;
  }
  function origEl(tag, obj) {
    var o = origOf(obj);
    if (!o) return null;
    var e = el(tag, o.lang, o.text);
    e.lang = o.lang;
    return e;
  }
  function both(obj, sep) { var o = origOf(obj); return o ? o.text + sep + obj.en : obj.en; }
  function byId(id) { return state.map.annotations.filter(function (a) { return a.id === id; })[0]; }
  /* Maps whose labels carry the number written on the map (Remezov) show that number; others count 1, 2, 3. */
  function pinText(a) {
    if (!state.map.annotations.some(function (x) { return x.number != null; })) return String(a.num);
    return a.number ? String(a.number).replace(/\s*\[\?\]/, '?') : '·';
  }
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
      'tourStatus', 'labelsToggle', 'labelOpacity', 'zoomIn', 'zoomOut', 'zoomHome', 'help', 'helpToggle', 'helpClose',
      'about', 'indexToggle', 'fullScreen', 'tooltip', 'toast', 'authorHint', 'stageNote', 'titleZh', 'titleEn',
      'mapSelect', 'workspace', 'index', 'stage', 'credit'
    ].forEach(function (id) { state.els[id] = document.getElementById(id); });

    Promise.all([
      fetch('data/catalogue.json').then(function (r) { return r.json(); }),
      fetch('data/collection.json').then(function (r) { return r.json(); }),
      // maps in demo/private/ (not published: image rights not cleared) exist only where they were built
      fetch('private/catalogue.json').then(function (r) { return r.ok ? r.json() : { maps: [] }; }, function () { return { maps: [] }; })
    ]).then(function (res) {
      var cat = { maps: res[2].maps.concat(res[0].maps) }, coll = res[1];
      state.catalogue = cat;
      var h = readHash();
      var qs = new URLSearchParams(location.search);
      // with no map named, open the first published map, not a local one listed ahead of it
      var first = res[0].maps[0];
      var wanted = h.get('map') || qs.get('map') || first.id;
      var entry = cat.maps.filter(function (m) { return m.id === wanted; })[0];
      var record = entry ? null : coll.maps.filter(function (m) { return COLLECTION_PREFIX + m.n === wanted; })[0];
      if (!entry && !record) entry = first;
      fillMapSelect(cat, coll, entry ? entry.id : wanted);
      if (record) { loadMap(mapFromCollection(record, coll), h); return; }
      return fetch(entry.file).then(function (r) { return r.json(); }).then(function (map) { loadMap(map, h); });
    }).catch(function (err) {
      state.els.readingInner.innerHTML = '<p class="placeholder">Could not load the demo data (' + err.message +
        '). Serve this folder over HTTP, e.g. <code>python3 -m http.server</code>, rather than opening the file directly.</p>';
    });
  }

  function fillMapSelect(cat, coll, current) {
    var sel = state.els.mapSelect;
    function add(parent, id, text) {
      var o = el('option', null, text);
      o.value = id;
      if (id === current) o.selected = true;
      parent.appendChild(o);
    }
    var g1 = el('optgroup'); g1.label = 'Annotated';
    cat.maps.forEach(function (m) { add(g1, m.id, (m.short && m.short.en) || m.title.en); });
    var g2 = el('optgroup'); g2.label = 'Collection (' + coll.maps.length + ' maps)';
    coll.maps.forEach(function (m) { add(g2, COLLECTION_PREFIX + m.n, collectionLabel(m)); });
    sel.appendChild(g1); sel.appendChild(g2);
    sel.addEventListener('change', function () {
      location.hash = 'map=' + sel.value;
      location.reload();
    });
  }
  function collectionLabel(m) {
    var t = m.title || 'Untitled';
    return m.year + ' ' + m.authors.join(', ') + ' · ' + (t.length > 50 ? t.slice(0, 48) + '…' : t);
  }

  /* A collection record carries only what the existing site's catalogue holds: no annotations. */
  function mapFromCollection(m, coll) {
    var source = m.sources.join(', ');
    return {
      id: COLLECTION_PREFIX + m.n,
      title: { en: m.title || 'Untitled' },
      creator: m.authors.join(', '),
      date: m.year,
      description: 'From the TARTARY Project collection (no. ' + m.n + '), as catalogued on the project\'s first site. ' +
        'This map has no transcription or translation yet.',
      catalogue: {
        repository: source,
        reference: 'TARTARY Project, map ' + m.n,
        credit: 'Image: ' + (source || 'source not recorded') + ', via the TARTARY Project',
        url: coll.source + '/maps/' + m.n
      },
      views: [{ id: 'map', label: { en: 'Map' }, tileSource: m.dzi + COLLECTION_TILE_QUERY }],
      annotations: []
    };
  }

  function loadMap(map, h) {
    state.map = map;
    map.annotations.forEach(function (a, i) { a.num = i + 1; });
    document.title = map.title.en + ' · Mapping Tartary';
    var t = origOf(map.title);
    state.els.titleZh.textContent = t ? t.text : '';
    state.els.titleZh.lang = t ? t.lang : '';
    state.els.titleZh.className = t ? t.lang : 'hidden';
    state.els.titleEn.textContent = map.title.en;
    document.body.classList.toggle('no-annotations', !map.annotations.length);
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
    state.els.stageNote.textContent = both(view.label, ' · ') + (view.note ? ' — ' + view.note : '');
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

      // an approximate box is only a default size round the label's centre, so it is not drawn
      var box = el('div', 'region' + (a.region_approx ? ' is-approx' : ''));
      box.dataset.id = a.id;
      state.viewer.addOverlay({ element: box, location: rect });

      var pin = el('button', 'pin', pinText(a));
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
    // within the zoom limits, so a small region does not zoom in past the image's resolution
    state.viewer.viewport.fitBoundsWithConstraints(rect, false);
  }

  /* Opening the reading panel narrows (on phones, shortens) the stage. OpenSeadragon applies a
     resize on its next frame by jumping to the view it was heading for, so a fit started before
     then would not animate, and on phones would be fitted to the taller stage. Fit after it. */
  function afterStageResize(resizing, fn) {
    if (!resizing) { fn(); return; }
    var done = false;
    function run() { if (!done) { done = true; fn(); } }
    // 'after-resize' is raised before OpenSeadragon restores its centre and zoom, hence the timeout
    state.viewer.addOnceHandler('after-resize', function () { setTimeout(run, 0); });
    setTimeout(run, 300);
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
    revealInFilter(a);
    markActive();
    renderReading(a);
    var resizing = openPanel();
    if (opts.zoom !== false) afterStageResize(resizing, function () { fitRegion(a); });
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
    eyebrow.appendChild(el('span', null, catName(a.category) + (a.number != null ? (a.number ? ' · map no. ' + a.number : ' · no number') : ' · no. ' + a.num) + ' · ' + viewById(a.view).label.en));
    var close = el('button', 'close', 'Close ×');
    close.type = 'button';
    close.addEventListener('click', closePanel);
    eyebrow.appendChild(close);
    root.appendChild(eyebrow);

    var h2 = origEl('h2', a.label);
    if (h2) root.appendChild(h2);
    root.appendChild(el('h3', 'en', a.label.en));

    // set by scripts/apply_corrections.py from the specialists' review; until then the map's own
    // notice says what the readings are, and its first sentence goes here, before the text
    var notice = splitNotice(state.map.notice);
    if (state.map.reviewed || a.review) root.appendChild(reviewBadge(a.review));
    else if (notice.status) root.appendChild(el('p', 'review-badge', notice.status));

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
    // a translation is read with the text it translates, so both open together on the first tab;
    // an English text's modern spelling repeats the same words, so it keeps a tab of its own
    var withText = t.translation && hasOriginal && t.lang !== 'en';
    var transLabel = t.lang === 'en' ? 'Modern spelling' : 'Translation';
    var tabs = [];
    if (hasOriginal) tabs.push({ key: 'original', label: t.lang === 'zh' ? '原文 Text' : 'Text' });
    if (t.expanded) tabs.push({ key: 'expanded', label: t.lang === 'ru' ? 'Modern Russian' : 'Expanded' });
    if (t.translation && !withText) tabs.push({ key: 'translation', label: transLabel });
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

    function translationInto(p) {
      t.translation.split('\n').forEach(function (line) { p.appendChild(el('p', 'translation', line)); });
    }
    if (hasOriginal) {
      var p = el('div', 'tabpanel');
      if (withText) p.appendChild(el('div', 'text-label', t.lang === 'zh' ? '原文 Original' : 'Original'));
      var orig = el('div', 'original' + (t.lang === 'zh' ? '' : t.lang === 'ru' ? ' ru' : ' latin'), t.original);
      orig.lang = t.lang || 'la';
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
      if (withText) {
        p.appendChild(el('div', 'text-label', transLabel));
        translationInto(p);
      }
      panels.original = p; root.appendChild(p);
    }
    if (t.expanded) {
      var pe = el('div', 'tabpanel');
      pe.appendChild(el('p', 'note', t.lang === 'ru' ? 'In modern Russian spelling, abbreviations written out.' : 'Abbreviations written out; spelling as on the map.'));
      var ex = el('div', 'original ' + (t.lang === 'ru' ? 'ru' : 'latin'), t.expanded); ex.lang = t.lang;
      pe.appendChild(ex);
      panels.expanded = pe; root.appendChild(pe);
    }
    if (t.translation && !withText) {
      var p2 = el('div', 'tabpanel');
      translationInto(p2);
      panels.translation = p2; root.appendChild(p2);
    }
    if (t.commentary) {
      var p3 = el('div', 'tabpanel');
      t.commentary.split('\n').forEach(function (line) { p3.appendChild(el('p', 'commentary', line)); });
      panels.commentary = p3; root.appendChild(p3);
    }
    if (t.source && t.source.length) {
      var p4 = el('div', 'tabpanel source');
      var ol = el('ol');
      t.source.forEach(function (s) { ol.appendChild(el('li', null, s)); });
      p4.appendChild(ol);
      panels.source = p4; root.appendChild(p4);
    }
    // the first tab is open, whichever kinds of text this annotation has
    Object.keys(panels).forEach(function (k) { panels[k].hidden = k !== tabs[0].key; });

    if (notice.rest) root.appendChild(el('p', 'note', notice.rest));
    root.appendChild(scanLine());
  }

  /* A map's notice opens with what its readings are ("Machine transcription …, not yet reviewed by a
     specialist."); the rest explains the marks in the text. Split at the end of the first sentence. */
  function splitNotice(text) {
    if (!text) return { status: '', rest: '' };
    var m = /^(.+?\.)\s+(.*)$/.exec(text);
    return m ? { status: m[1], rest: m[2] } : { status: text, rest: '' };
  }

  /* Under an annotation, one line on the scan; the full record is under About this map. */
  function scanLine() {
    var p = el('p', 'scan-line');
    var c = state.map.catalogue;
    if (c.repository) p.appendChild(document.createTextNode('Scan: ' + c.repository + ' · '));
    var about = el('button', 'link', 'About this map'); about.type = 'button';
    about.addEventListener('click', showAbout);
    p.appendChild(about);
    return p;
  }

  var REVIEW_TEXT = { accepted: 'Checked by ', corrected: 'Corrected by ', added: 'Added by ', disputed: 'Disputed by ' };
  function reviewBadge(r) {
    if (!r) return el('p', 'review-badge', 'Machine reading, not yet checked by a specialist.');
    var text = (REVIEW_TEXT[r.status] || 'Reviewed by ') + r.by + ', ' + String(r.at).slice(0, 10) + (r.comment ? ': ' + r.comment : '.');
    return el('p', 'review-badge st-' + r.status, text);
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
    var h2 = origEl('h2', state.map.title);
    if (h2) root.appendChild(h2);
    root.appendChild(el('h3', 'en', state.map.title.en));
    root.appendChild(el('p', 'sans muted', [state.map.creator, state.map.date].filter(Boolean).join(' · ')));
    state.map.description.split('\n').forEach(function (line) { root.appendChild(el('p', null, line)); });
    if (state.map.annotations.length) {
      root.appendChild(el('p', 'note', 'Select a numbered pin on the map or an entry in the index to read its original text, translation and commentary. Use the buttons above the map to turn the sheet over or to follow the guided tour.'));
    }
    root.appendChild(catalogueBlock());
    if (state.map.notice) root.appendChild(el('p', 'note', state.map.notice));
    stopTour();
    state.current = null;
    markActive();
    updateTourStatus();
    writeHash({});
    openPanel();
  }

  /* Returns true when the panel was closed, i.e. when opening it resizes the stage. */
  function openPanel() {
    var ws = state.els.workspace, wasClosed = ws.classList.contains('panel-closed');
    ws.classList.remove('panel-closed');
    return wasClosed;
  }
  function closePanel() { stopTour(); state.els.workspace.classList.add('panel-closed'); }

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
        li.appendChild(el('span', 'num', pinText(a)));
        var body = el('div');
        var o = origEl('div', a.label);
        if (o) body.appendChild(o);
        var en = el('div', 'en', a.label.en);
        en.appendChild(el('span', 'cat', catName(a.category)));
        body.appendChild(en);
        li.appendChild(body);
        li.addEventListener('click', function () { select(a.id, { zoom: true, stopTour: true }); closeIndexOnMobile(); });
        li.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); li.click(); } });
        list.appendChild(li);
      });
    });
    // each choice says how many entries it lists; the quiet categories, left out of the first, come last
    var cats = {};
    state.map.annotations.forEach(function (a) { cats[a.category] = (cats[a.category] || 0) + 1; });
    var quiet = quietCats().filter(function (c) { return cats[c]; });
    var keys = Object.keys(cats).filter(function (c) { return quiet.indexOf(c) < 0; }).concat(quiet);
    var main = state.map.annotations.length - quiet.reduce(function (n, c) { return n + cats[c]; }, 0);
    var sel = state.els.filter;
    sel.innerHTML = '';
    var all = el('option', null, (quiet.length ? 'Main entries' : 'All categories') + ' (' + main + ')');
    all.value = 'all'; sel.appendChild(all);
    keys.forEach(function (c) { var o = el('option', null, catName(c) + ' (' + cats[c] + ')'); o.value = c; sel.appendChild(o); });
    sel.addEventListener('change', function () { state.filter = sel.value; applyFilter(); });
  }

  /* Categories a map lists in "quiet" (e.g. hundreds of place names) are left out of the default
     view, so they don't bury the notes; choosing the category in the filter shows them. */
  function quietCats() { return state.map.quiet || []; }
  /* A map may rename a category for its own content ("categories": {"toponym": "Peoples, regions and seas"}). */
  function catName(c) { return (state.map.categories && state.map.categories[c]) || CATEGORY[c] || c; }
  /* How the filter shows an annotation. "away": a quiet category that is not the one chosen, so its
     pin, box and label are not drawn at all. "off": another category is chosen, so its pin is dimmed
     and its box, label and index entry are hidden. */
  function filterState(a) {
    var f = state.filter;
    return { away: quietCats().indexOf(a.category) >= 0 && f !== a.category, off: f !== 'all' && f !== a.category };
  }
  function applyFilter() {
    var states = {};
    state.map.annotations.forEach(function (a) { states[a.id] = filterState(a); });
    $$('.index-list li[data-id], .pin, .region, .label-ovl').forEach(function (n) {
      var s = states[n.dataset.id];
      if (!s) return;
      if (n.classList.contains('pin')) {
        n.classList.toggle('is-dim', s.off && !s.away);
        n.classList.toggle('hidden', s.away);
      } else if (n.tagName === 'LI') {
        n.classList.toggle('is-hidden', s.off || s.away);
      } else {
        n.classList.toggle('hidden', s.off || s.away || (n.classList.contains('label-ovl') && !state.labelsOn));
      }
    });
    // a side's heading only when some of its entries are listed
    $$('.index-list li.index-group').forEach(function (g) {
      var any = false;
      for (var n = g.nextElementSibling; n && !n.classList.contains('index-group'); n = n.nextElementSibling) {
        if (!n.classList.contains('is-hidden')) { any = true; break; }
      }
      g.classList.toggle('hidden', !any);
    });
  }
  /* The annotation being read is always drawn and listed. One the filter hides or dims (opened from
     a link, the tour or a dimmed pin) changes the filter: to its category if that is a quiet one,
     otherwise to all categories. */
  function revealInFilter(a) {
    var s = filterState(a);
    if (!s.away && !s.off) return;
    state.filter = quietCats().indexOf(a.category) >= 0 ? a.category : 'all';
    state.els.filter.value = state.filter;
    applyFilter();
  }

  /* ---------- Tour ---------- */
  function buildTour() {
    state.tour.list = state.map.annotations.filter(function (a) { return a.tour !== false; });
    updateTourStatus();
  }
  /* Steps from the annotation being read, so the tour follows a pin chosen on the map or in the
     index. From one that is not a stop it goes to the nearest stop in map order; with nothing
     selected it starts on the side being shown. */
  function tourStep(dir) {
    var list = state.tour.list, n = list.length, cur = state.current, i;
    if (!n) return;
    if (cur && list.indexOf(cur) >= 0) {
      i = list.indexOf(cur) + dir;
    } else if (cur) {
      for (i = 0; i < n && list[i].num < cur.num; i++);
      if (dir < 0) i -= 1;
    } else {
      var here = list.filter(function (a) { return a.view === state.viewId; });
      if (!here.length) here = list;
      i = list.indexOf(dir > 0 ? here[0] : here[here.length - 1]);
    }
    select(list[(i % n + n) % n].id, { zoom: true });
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
    var n = state.tour.list.length, i = state.current ? state.tour.list.indexOf(state.current) : -1;
    state.els.tourStatus.textContent = i >= 0 ? (i + 1) + ' / ' + n : n + ' stops';
  }

  /* ---------- View switch ---------- */
  function renderViewSwitch() {
    var wrap = state.els.viewSwitch;
    wrap.innerHTML = '';
    wrap.classList.toggle('hidden', state.map.views.length < 2);  // nothing to switch between
    state.map.views.forEach(function (v) {
      var b = el('button', 'btn', both({ zh: v.label.zh, la: v.label.la, en: v.label.en.replace(/\s*\(.*\)$/, '').replace(/:.*$/, '') }, ' '));
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
    var o = origEl('span', a.label);
    if (o) tip.appendChild(o);
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
    // just below the top bar, whose height depends on how many rows its controls wrap onto
    if (show) h.style.top = ($('.topbar').getBoundingClientRect().bottom + 8) + 'px';
    h.classList.toggle('hidden', !show);
    state.els.helpToggle.setAttribute('aria-expanded', String(show));
  }
  function toggleIndex() {
    if (window.matchMedia(PHONE).matches) {
      // on phones the index covers the map; open it at the entry being read
      var open = state.els.index.classList.toggle('is-open');
      var li = open && $('.index-list li.is-active');
      if (li) li.scrollIntoView({ block: 'center' });
    } else state.els.workspace.classList.toggle('index-hidden');
  }
  function closeIndexOnMobile() { state.els.index.classList.remove('is-open'); }
  /* The whole page, not only the map, so the reading panel and the tour stay on a projector's screen.
     Esc leaves full screen in the browser itself. */
  function toggleFullScreen() {
    if (!document.fullscreenEnabled) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen().catch(function () { toast('This browser did not allow full screen'); });
  }

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
    // zoomBy does not apply the zoom limits itself; OpenSeadragon's own buttons follow it with applyConstraints
    e.zoomIn.addEventListener('click', function () { state.viewer.viewport.zoomBy(1.5).applyConstraints(); });
    e.zoomOut.addEventListener('click', function () { state.viewer.viewport.zoomBy(1 / 1.5).applyConstraints(); });
    e.zoomHome.addEventListener('click', function () { state.viewer.viewport.goHome(); });
    e.helpToggle.addEventListener('click', function () { toggleHelp(); });
    e.helpClose.addEventListener('click', function () { toggleHelp(false); });
    // a tap or click anywhere else closes the help (capture phase: the map's handlers stop pointer events)
    document.addEventListener('pointerdown', function (ev) {
      if (!e.help.classList.contains('hidden') && !e.help.contains(ev.target) && !e.helpToggle.contains(ev.target)) toggleHelp(false);
    }, true);
    e.about.addEventListener('click', showAbout);
    e.indexToggle.addEventListener('click', toggleIndex);
    // iPhones offer full screen only for video, so the button is shown only where it works
    e.fullScreen.classList.toggle('hidden', !document.fullscreenEnabled);
    e.fullScreen.addEventListener('click', toggleFullScreen);
    document.addEventListener('fullscreenchange', function () {
      var on = !!document.fullscreenElement;
      e.fullScreen.setAttribute('aria-pressed', String(on));
      e.fullScreen.textContent = on ? 'Exit full screen' : 'Full screen';
    });

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
        case 'f': toggleFullScreen(); break;
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
