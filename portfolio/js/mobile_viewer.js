/* ============================================================
   Mobile Viewer — Procreate-style pinch / zoom / pan / swipe
   Only activates on touch-capable devices when the lightbox
   is open.  Completely replaces the simple swipe handler.

   Uses default transform-origin (center) so scale(s) zooms
   from the image center, and translate(tx,ty) shifts the
   center by that amount.
   ============================================================ */
(function () {
  if (!('ontouchstart' in window || navigator.maxTouchPoints > 0)) return;

  var lightbox = document.getElementById('lightbox');
  var img      = document.getElementById('lightboxImg');
  var closeBtn = document.getElementById('closeBtn');

  /* ---- transform state ---- */
  var scale = 1, tx = 0, ty = 0;

  /* ---- pinch snapshot (captured once at pinch start) ---- */
  var pinching = false;
  var ps = null; /* { scale, tx, ty, dist, midX, midY, bcx, bcy } */

  /* ---- pan / swipe state ---- */
  var panX = 0, panY = 0;
  var swX0 = 0, swY0 = 0, swT0 = 0;
  var moved = false;

  /* ============ helpers ============ */
  function d2(a, b) {
    return Math.hypot(b.clientX - a.clientX, b.clientY - a.clientY);
  }
  function mid(a, b) {
    return { x: (a.clientX + b.clientX) / 2,
             y: (a.clientY + b.clientY) / 2 };
  }
  function zoomed() { return scale > 1.02; }

  function apply() {
    img.style.transform =
      'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')';
  }

  /* Base center = screen position of image center when tx=ty=0.
     Works regardless of current transform.                       */
  function baseCenter() {
    var r = img.getBoundingClientRect();
    return { x: (r.left + r.right) / 2 - tx,
             y: (r.top + r.bottom) / 2 - ty };
  }

  function clamp() {
    if (scale <= 1) { tx = 0; ty = 0; return; }
    var sw = img.offsetWidth  * scale;
    var sh = img.offsetHeight * scale;
    var vw = window.innerWidth, vh = window.innerHeight;
    var mxT = Math.max(0, (sw - vw) / 2);
    var myT = Math.max(0, (sh - vh) / 2);
    tx = Math.max(-mxT, Math.min(mxT, tx));
    ty = Math.max(-myT, Math.min(myT, ty));
  }

  function snapBack(cb) {
    scale = 1; tx = 0; ty = 0;
    img.style.transition = 'transform .25s cubic-bezier(.25,.46,.45,.94)';
    apply();
    setTimeout(function () { img.style.transition = ''; if (cb) cb(); }, 260);
  }

  function reset() {
    scale = 1; tx = 0; ty = 0;
    img.style.transition = '';
    apply();
  }

  /* ============ disable browser gestures inside lightbox ============ */
  lightbox.style.touchAction = 'none';

  /* ============ TOUCHSTART ============ */
  lightbox.addEventListener('touchstart', function (e) {
    if (!lightbox.classList.contains('open')) return;

    if (e.touches.length === 2) {
      e.preventDefault();
      pinching = true;
      var bc = baseCenter();
      var m  = mid(e.touches[0], e.touches[1]);
      ps = {
        scale: scale, tx: tx, ty: ty,
        dist:  d2(e.touches[0], e.touches[1]),
        midX:  m.x,  midY:  m.y,
        bcx:   bc.x, bcy:   bc.y
      };
    } else if (e.touches.length === 1) {
      pinching = false;
      moved    = false;
      panX = e.touches[0].clientX;
      panY = e.touches[0].clientY;
      swX0 = panX; swY0 = panY; swT0 = Date.now();
    }
  }, { passive: false });

  /* ============ TOUCHMOVE ============ */
  lightbox.addEventListener('touchmove', function (e) {
    if (!lightbox.classList.contains('open')) return;

    /* --- two-finger pinch-to-zoom --- */
    if (e.touches.length === 2 && ps) {
      e.preventDefault();
      var d  = d2(e.touches[0], e.touches[1]);
      var ns = Math.max(0.5, Math.min(10, ps.scale * (d / ps.dist)));
      var r  = ns / ps.scale;           /* ratio vs start-of-pinch */
      var m  = mid(e.touches[0], e.touches[1]);

      /* Focal-point zoom: keep the initial midpoint fixed on the
         same image pixel.  Using transform-origin: center, tx/ty
         represent the offset of the image center from its natural
         flexbox-centered position.

         Formula:  tx_new = tx0 + (1-r) * (focalScreenX - baseCenterX - tx0)
         …plus two-finger pan drift.                                        */
      tx = ps.tx + (1 - r) * (ps.midX - ps.bcx - ps.tx)
                 + (m.x - ps.midX);
      ty = ps.ty + (1 - r) * (ps.midY - ps.bcy - ps.ty)
                 + (m.y - ps.midY);
      scale = ns;
      clamp();
      apply();
      return;
    }

    /* --- single-finger --- */
    if (e.touches.length === 1 && !pinching) {
      var dx = e.touches[0].clientX - panX;
      var dy = e.touches[0].clientY - panY;

      if (Math.abs(e.touches[0].clientX - swX0) > 8 ||
          Math.abs(e.touches[0].clientY - swY0) > 8) {
        moved = true;
      }

      if (zoomed()) {
        /* Panning */
        e.preventDefault();
        tx += dx; ty += dy;
        panX = e.touches[0].clientX;
        panY = e.touches[0].clientY;
        clamp();
        apply();
      } else {
        /* Track for swipe detection — don't preventDefault so the
           browser can still do its own scroll if we bail.          */
        panX = e.touches[0].clientX;
        panY = e.touches[0].clientY;
      }
    }
  }, { passive: false });

  /* ============ TOUCHEND ============ */
  lightbox.addEventListener('touchend', function (e) {
    if (!lightbox.classList.contains('open')) return;

    /* Went from two fingers to one → transition to pan */
    if (e.touches.length === 1) {
      pinching = false;
      ps = null;
      panX = e.touches[0].clientX;
      panY = e.touches[0].clientY;
      return;
    }
    if (e.touches.length > 0) return;

    /* All fingers lifted */
    pinching = false;
    ps = null;

    /* Below 1× → snap back, but check for swipe first */
    if (scale < 1.02) {
      var sdx = e.changedTouches[0].clientX - swX0;
      var sdy = e.changedTouches[0].clientY - swY0;
      var dt  = Date.now() - swT0;
      if (Math.abs(sdx) > 50 &&
          Math.abs(sdx) > Math.abs(sdy) * 1.3 &&
          dt < 500) {
        reset();
        if (sdx < 0) next(); else prev();
      } else {
        snapBack();
      }
      return;
    }

    /* Still zoomed — animate to clamped position */
    clamp();
    img.style.transition = 'transform .15s ease-out';
    apply();
    setTimeout(function () { img.style.transition = ''; }, 160);
  }, { passive: true });

  /* ============ Hook into lightbox navigation ============ */
  var origOpenAt = openAt;
  openAt = function (idx) { reset(); origOpenAt(idx); };

  var origClose = close;
  close = function () { reset(); origClose(); };

  /* ============ Close button always tappable ============ */
  closeBtn.style.zIndex = '60';
  closeBtn.addEventListener('touchend', function (e) {
    e.preventDefault();
    e.stopPropagation();
    reset();
    origClose();
  }, { passive: false });

  /* Prevent accidental lightbox-background-close after pan / zoom */
  img.addEventListener('click', function (e) {
    if (zoomed() || moved) e.stopPropagation();
  }, true);

})();
