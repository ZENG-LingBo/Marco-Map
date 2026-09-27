/* Marco-Map demo: scrollytelling narrative driving the deep-zoom viewer.
   Sections come from the map file's "story" array. As a section reaches the middle of the
   window the viewer flies to that section's annotation (switching the side of the map when
   needed). Same idea as the Leventhal "Map Chat" pages, with a real zoomable map underneath. */
(function () {
  'use strict';
  var OSD_IMAGES = 'https://cdnjs.cloudflare.com/ajax/libs/openseadragon/6.1.1/images/';

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  var qs = new URLSearchParams(location.search);
  var map, viewer, currentView = null, regionBox = null, currentIndex = -1;
  var byId = function (id) { return map.annotations.filter(function (a) { return a.id === id; })[0]; };
  var viewById = function (id) { return map.views.filter(function (v) { return v.id === id; })[0]; };

  fetch('data/catalogue.json').then(function (r) { return r.json(); }).then(function (cat) {
    var entry = cat.maps.filter(function (m) { return m.id === qs.get('map'); })[0] || cat.maps[0];
    var sel = document.getElementById('storySelect');
    cat.maps.forEach(function (m) {
      var o = el('option', null, (m.short && m.short.en) || m.title.en); o.value = m.id; if (m.id === entry.id) o.selected = true; sel.appendChild(o);
    });
    sel.addEventListener('change', function () { location.search = '?map=' + sel.value; });
    return fetch(entry.file).then(function (r) { return r.json(); });
  }).then(function (m) {
    map = m;
    map.annotations.forEach(function (a, i) { a.num = i + 1; });
    build();
  }).catch(function (err) {
    document.getElementById('storyText').innerHTML = '<p class="placeholder">Could not load the demo data (' + err.message + '). Serve this folder over HTTP.</p>';
  });

  function build() {
    document.title = map.story.title.en + ' · Marco-Map demo';
    var text = document.getElementById('storyText');
    var h1 = el('h1');
    var zh = el('span', 'zh', map.story.title.zh); zh.lang = 'zh';
    h1.appendChild(zh); h1.appendChild(document.createTextNode(map.story.title.en));
    text.appendChild(el('div', 'kicker', map.title.en + ' · ' + map.date));
    text.appendChild(h1);
    text.appendChild(el('div', 'byline', map.story.byline));

    map.story.sections.forEach(function (s, i) {
      var sec = el('section');
      sec.dataset.index = i;
      var h2 = el('h2');
      var szh = el('span', 'zh', s.heading.zh); szh.lang = 'zh';
      h2.appendChild(szh); h2.appendChild(document.createTextNode(s.heading.en));
      sec.appendChild(h2);
      var a = s.annotation ? byId(s.annotation) : null;
      if (a && a.text && a.text.original && a.text.original !== '(no text)') {
        var q = el('blockquote', 'orig', a.text.original.split('\n')[0] + (a.text.original.indexOf('\n') > -1 ? ' …' : ''));
        q.lang = a.text.lang === 'zh' ? 'zh' : 'la';
        sec.appendChild(q);
      }
      s.body.forEach(function (p) { sec.appendChild(el('p', null, p)); });
      if (a) {
        var link = el('a', 'sans', 'Open this annotation in the viewer');
        link.href = 'viewer.html#map=' + map.id + '&view=' + a.view + '&a=' + a.id;
        sec.appendChild(link);
      }
      text.appendChild(sec);
    });
    var end = el('p', 'end');
    end.appendChild(document.createTextNode('End of the narrative. '));
    var back = el('a', null, 'Back to the catalogue'); back.href = 'index.html';
    end.appendChild(back);
    text.appendChild(end);

    viewer = OpenSeadragon({
      id: 'osd', prefixUrl: OSD_IMAGES, showNavigationControl: false, showNavigator: false,
      animationTime: 1.8, springStiffness: 5, visibilityRatio: 0.5, minZoomImageRatio: 0.6, maxZoomPixelRatio: 3,
      gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: true, scrollToZoom: false },
      gestureSettingsTouch: { clickToZoom: false },
      crossOriginPolicy: 'Anonymous', ajaxWithCredentials: false
    });

    var mobile = window.matchMedia('(max-width: 768px)').matches;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) go(Number(en.target.dataset.index));
      });
    }, { rootMargin: mobile ? '-55% 0px -35% 0px' : '-42% 0px -48% 0px', threshold: 0 });
    Array.prototype.forEach.call(text.querySelectorAll('section'), function (s) { io.observe(s); });
    go(0);
  }

  function openView(id, then) {
    if (currentView === id) { then && then(); return; }
    currentView = id;
    viewer.clearOverlays(); regionBox = null;
    viewer.addOnceHandler('open', function () { then && then(); });
    viewer.open(viewById(id).tileSource);
  }

  function fit(r, pad) {
    pad = pad == null ? 0.4 : pad;
    var rect = viewer.viewport.imageToViewportRectangle(
      new OpenSeadragon.Rect(r.x - r.w * pad, r.y - r.h * pad, r.w * (1 + 2 * pad), r.h * (1 + 2 * pad)));
    viewer.viewport.fitBounds(rect, false);
  }
  function showRegion(r) {
    var rect = viewer.viewport.imageToViewportRectangle(new OpenSeadragon.Rect(r.x, r.y, r.w, r.h));
    if (!regionBox) { regionBox = el('div', 'region is-active'); viewer.addOverlay({ element: regionBox, location: rect }); }
    else viewer.updateOverlay(regionBox, rect);
    regionBox.classList.remove('hidden');
  }
  function hideRegion() { if (regionBox) regionBox.classList.add('hidden'); }
  function caption(txt) { document.getElementById('caption').textContent = txt; }

  function go(i) {
    if (i === currentIndex) return;
    currentIndex = i;
    var s = map.story.sections[i];
    Array.prototype.forEach.call(document.querySelectorAll('.story section'), function (sec) {
      sec.classList.toggle('is-current', Number(sec.dataset.index) === i);
    });
    if (s.annotation) {
      var a = byId(s.annotation);
      openView(a.view, function () {
        fit(a.region);
        showRegion(a.region);
        caption(a.num + '. ' + a.label.zh + ' · ' + a.label.en + ' — ' + viewById(a.view).label.en);
      });
    } else {
      openView(s.view, function () {
        viewer.viewport.goHome();
        hideRegion();
        caption(viewById(s.view).label.zh + ' · ' + viewById(s.view).label.en);
      });
    }
  }
})();
