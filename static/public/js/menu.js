/* QR Menu Studio public menu: scroll-spy, dish sheet (history + swipe), search/filter. No deps. */
(() => {
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const root = document.documentElement, reduce = matchMedia('(prefers-reduced-motion:reduce)').matches;
  const bar = $('.bar'), chips = $$('.bar a'), secs = $$('.cat'), dishes = $$('.dish');
  const barH = () => parseFloat(getComputedStyle(root).getPropertyValue('--bar-h')) || 0;

  // --- category chips: scroll-spy + centring ---------------------------------------------------
  if (bar && chips.length) {
    const ul = $('ul', bar);
    let tick = 0, cur = null;
    const spy = () => {
      tick = 0;
      const y = barH() + 24;
      let id = secs[0] && secs[0].id;
      for (const s of secs) if (!s.hidden && s.getBoundingClientRect().top <= y) id = s.id;
      if (innerHeight + scrollY >= document.body.scrollHeight - 4) id = secs.filter(s => !s.hidden).pop()?.id || id;
      if (id === cur) return;
      cur = id;
      for (const a of chips) {
        const on = a.hash === '#' + id;
        if (on) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
        if (on && ul.scrollWidth > ul.clientWidth && getComputedStyle(ul).flexDirection === 'row')
          ul.scrollTo({ left: a.parentNode.offsetLeft - (ul.clientWidth - a.offsetWidth) / 2, behavior: reduce ? 'auto' : 'smooth' });
      }
    };
    addEventListener('scroll', () => { if (!tick) tick = requestAnimationFrame(spy); }, { passive: true });
    addEventListener('resize', spy);
    spy();
    bar.addEventListener('click', e => {
      const a = e.target.closest('a');
      const s = a && $(a.hash);
      if (!s) return;
      e.preventDefault();
      s.scrollIntoView();
      history.replaceState(history.state, '', a.hash);
    });
  }

  // --- sheets ----------------------------------------------------------------------------------
  const sheet = $('#sheet'), fdlg = $('#filters');
  const openDlg = (d, hash, cold) => {
    if (d.open) return;
    d.showModal();
    const st = { sheet: d.id, cold: cold ? 1 : 0 };
    if (cold) history.replaceState(st, '', hash || location.href); else history.pushState(st, '', hash || location.href);
  };
  const closeUI = d => {
    const st = history.state;
    if (st && st.sheet === d.id && !st.cold) history.back();
    else { if (st && st.cold) history.replaceState(null, '', location.pathname + location.search); d.close(); }
  };
  const dlgs = [sheet, fdlg].filter(Boolean);
  for (const d of dlgs) {
    d.addEventListener('cancel', e => { e.preventDefault(); closeUI(d); });
    d.addEventListener('click', e => { if (e.target === d || e.target.closest('[data-close]')) closeUI(d); });
    d.addEventListener('close', () => { d.firstElementChild.style.transform = ''; });
    swipe(d);
  }
  addEventListener('popstate', () => {
    const st = history.state, want = st && st.sheet;
    for (const d of dlgs) if (d.open && d.id !== want) d.close();
    if (want === 'sheet') { const li = $(location.hash); if (li && li.classList.contains('dish')) { fill(li); sheet.showModal(); } }
    if (want === 'filters' && fdlg) fdlg.showModal();
  });

  function swipe(d) {
    const box = d.firstElementChild, body = $('.sheet-body', d);
    let y0 = 0, dy = 0, t0 = 0, on = false;
    box.addEventListener('touchstart', e => { on = body.scrollTop <= 0; y0 = e.touches[0].clientY; dy = 0; t0 = e.timeStamp; }, { passive: true });
    box.addEventListener('touchmove', e => {
      if (!on) return;
      dy = e.touches[0].clientY - y0;
      if (dy > 0 && body.scrollTop <= 0) { e.preventDefault(); box.style.transition = 'none'; box.style.transform = `translateY(${dy}px)`; }
      else { dy = 0; box.style.transform = ''; }
    }, { passive: false });
    box.addEventListener('touchend', e => {
      if (!on || dy <= 0) return;
      box.style.transition = 'transform .18s';
      if (dy > 96 || dy / (e.timeStamp - t0) > .5) { box.style.transform = 'translateY(100%)'; setTimeout(() => closeUI(d), 120); }
      else box.style.transform = '';
      on = false;
    });
  }

  function fill(li) {
    const g = s => $(s, li), name = g('.dish-name');
    const link = $('a', name);
    $('#s-name').textContent = (link || name).firstChild.textContent.trim();
    $('#s-desc').textContent = g('.dish-desc') ? g('.dish-desc').textContent : '';
    $('#s-prices').innerHTML = g('.dish-prices') ? g('.dish-prices').innerHTML : '';
    const pill = g('.pill'), sold = $('#s-sold');
    sold.hidden = !pill; sold.innerHTML = pill ? pill.outerHTML : '';
    const img = g('.dish-thumb'), ph = $('#s-photo');
    ph.textContent = '';
    if (img) {
      const i = new Image();
      i.alt = '';
      if (img.dataset.fullset) { i.srcset = img.dataset.fullset; i.sizes = '(min-width:720px) 576px, 100vw'; }
      i.src = img.dataset.full;
      ph.append(i);
    }
    for (const [id, sel] of [['s-diets', '.diet'], ['s-al', '.tag:not(.diet)']]) {
      const ul = $('#' + id), hd = $('#' + (id === 's-al' ? 's-ah' : 's-dh'));
      ul.textContent = '';
      for (const t of $$(sel, li)) ul.append(t.cloneNode(true));
      hd.hidden = !ul.children.length;
    }
    $('.sheet-body', sheet).scrollTop = 0;
  }

  for (const a of $$('.dish-link')) a.setAttribute('aria-haspopup', 'dialog');
  const openDish = (li, cold) => { fill(li); openDlg(sheet, '#' + li.id, cold); };
  document.addEventListener('click', e => {
    const a = e.target.closest('.dish-link');
    if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey) return;
    e.preventDefault();
    openDish(a.closest('.dish'));
  });
  if (/^#dish-\d+$/.test(location.hash)) {
    const li = $(location.hash);
    if (li && $('.dish-link', li)) requestAnimationFrame(() => { li.scrollIntoView(); openDish(li, true); });
  }

  // --- search + filter -------------------------------------------------------------------------
  if (!fdlg || !$('#fbtn')) return;
  const KEY = 'mf' + location.pathname;
  const fbtn = $('#fbtn'), fstat = $('#fstat'), q = $('#fq'), form = $('#fform'), show = $('#fshow');
  fbtn.hidden = false;
  const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  for (const li of dishes) li._t = norm(li.textContent);
  const fmt = (n, one, many) => (n === 1 ? one : many.replace('{n}', n));
  const apply = () => {
    const diets = $$('input[name=diet]:checked', form).map(i => i.value), al = $$('input[name=al]:checked', form).map(i => i.value);
    const term = q ? norm(q.value.trim()) : '';
    let hid = 0, vis = 0;
    for (const li of dishes) {
      const d = ' ' + li.dataset.diet + ' ', a = ' ' + li.dataset.al + ' ';
      const hide = (term && !li._t.includes(term)) || diets.some(x => !d.includes(' ' + x + ' ')) || al.some(x => a.includes(' ' + x + ' '));
      li.hidden = hide;
      hide ? hid++ : vis++;
    }
    for (const s of secs) s.hidden = !$('.dish:not([hidden])', s);
    for (const a of chips) a.parentNode.hidden = $(a.hash).hidden;
    const active = !!(term || diets.length || al.length);
    fbtn.toggleAttribute('data-on', active);
    fstat.hidden = !hid;
    $('span', fstat).textContent = fmt(hid, fstat.dataset.one, fstat.dataset.n);
    $('#noresults').hidden = vis > 0;
    show.textContent = vis ? fmt(vis, show.dataset.one, show.dataset.n) : show.dataset.none;
    sessionStorage.setItem(KEY, JSON.stringify({ diets, al, term }));
  };
  const reset = () => { form.reset(); apply(); };
  form.addEventListener('input', apply);
  $('#freset2').addEventListener('click', reset);
  $('#freset').addEventListener('click', reset);
  show.addEventListener('click', () => closeUI(fdlg));
  fbtn.addEventListener('click', () => openDlg(fdlg, null, false));
  try {
    const st = JSON.parse(sessionStorage.getItem(KEY) || 'null');
    if (st) {
      for (const i of $$('input[type=checkbox]', form)) i.checked = (i.name === 'diet' ? st.diets : st.al).includes(i.value);
      if (q) q.value = st.term || '';
    }
  } catch (e) { /* ignore */ }
  apply();
})();
