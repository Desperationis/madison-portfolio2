from utils import *


class IndexPage:
    def __init__(self):
        self.header = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Madison Luna - Work</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Playfair+Display:wght@600&display=swap" rel="stylesheet">
  <style>
    :root{
      --bg:#ffffff;
      --ink:#0d0d0d;
      --muted:#6b7280; /* slate-500 */
      --accent:#5AA7FF;
      --grid-gap:42px;
      --maxw:1080px;
    }
    *{box-sizing:border-box}
    html,body{height:100%}
    body{
      margin:0;
      background:var(--bg);
      color:var(--ink);
      font-family:"Montserrat", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
      line-height:1.45;
    }
    a{color:inherit;text-decoration:none}

    /* --- Topbar --- */
    .topbar{
      position:sticky;top:0;z-index:10;
      background:rgba(255,255,255,.85);
      backdrop-filter:saturate(140%) blur(8px);
      border-bottom:1px solid #eaeaea;
    }
    .nav{
      max-width:var(--maxw);
      margin:0 auto;
      padding:18px 24px;
      display:flex;align-items:center;justify-content:space-between;
    }
    .brand{letter-spacing:.35em;font-weight:600}
    .menu{display:flex;gap:26px;align-items:center;font-size:14px;color:var(--muted)}
    .menu a{position:relative}
    .menu a.active{color:var(--ink);font-weight:600}
    .menu a.active::after{
      content:"";position:absolute;right:-10px;top:50%;transform:translateY(-50%) rotate(45deg);
      width:6px;height:6px;border-right:1.5px solid var(--ink);border-bottom:1.5px solid var(--ink);
    }

    /* --- Layout --- */
    .wrap{max-width:var(--maxw);margin:40px auto;padding:0 24px 64px}

    .grid{
      display:grid;gap:var(--grid-gap);
      grid-template-columns:repeat(12,1fr);
    }

    /* Six-up responsive gallery */
    .card{grid-column:span 4; display:flex; flex-direction:column; align-items:center; text-align:center;}
    @media (max-width: 980px){.card{grid-column:span 6}}
    @media (max-width: 640px){.card{grid-column:span 12}}

    .thumb{
      aspect-ratio: 1 / 1; /* perfect square */
      width:100%;
      border-radius:8px;
      overflow:hidden;
      position:relative;
      box-shadow:0 10px 25px rgba(0,0,0,.06);
      background:#f3f4f6;
    }
    .thumb img{width:100%;height:100%;object-fit:cover;display:block;transform:scale(1.02);transition:transform .45s ease, filter .45s ease}
    .thumb::after{ /* subtle inner border */
      content:"";position:absolute;inset:0;border-radius:8px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06);pointer-events:none
    }

    .card:hover .thumb img{transform:scale(1.06);filter:saturate(1.05)}

    .label{
      margin-top:14px;
      letter-spacing:.45em;
      color:var(--muted);
      font-size:13px;
      text-transform:uppercase;
      text-align:center;
      width:100%;
    }

    footer{max-width:var(--maxw);margin:40px auto 56px;padding:0 24px;color:#9aa1ad;font-size:13px;text-align:center;}
  </style>
</head>
<body>
  <!-- Top Navigation -->
  <header class="topbar" role="banner">
    <nav class="nav" aria-label="Primary">
      <div class="brand" aria-label="Site title"><a href="index.html">MADISON</a></div>
      <div class="menu" role="menubar">
        <a href="index.html" role="menuitem">Work</a>
        <a href="resume.pdf" role="menuitem">Resume</a>
      </div>
    </nav>
  </header>

"""


        self.category_code = ""

        self.footer="""
  <footer>© 2025 Madison Luna</footer>
</body>
</html>
"""

    def set_categories(self, categories: list[Category], cwd: Path):
        self.category_code += """
<main class="wrap" id="work">
    <section class="grid" aria-label="Portfolio categories">
"""
        for c in categories:
            self.category_code += f"""
      <a class="card" href="latest/{c.name}.html">
        <figure class="thumb">
          <img src="{dot_relative(cwd, c.thumbnail_p)}"/>
        </figure>
        <div class="label">{c.name}</div>
      </a>
"""
        
        self.category_code += """
    </section>
</main>
"""

        
    def get_content(self):
        return self.header + self.category_code + self.footer



class CategoryPage:
    def __init__(self, category, cwd):
        self.header = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Madison Luna - Sketches</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Playfair+Display:wght@600&display=swap" rel="stylesheet">
  <style>
    :root{
      --bg:#ffffff;
      --ink:#0d0d0d;
      --muted:#6b7280;
      --accent:#5AA7FF;
      --maxw:1120px;
      --gap:18px;
    }
    *{box-sizing:border-box}
    html,body{height:100%}
    body{margin:0;background:var(--bg);color:var(--ink);font-family:"Montserrat",system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;line-height:1.5}
    a{color:inherit;text-decoration:none}

    /* --- Topbar (copied to match index.html) --- */
    .topbar{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.9);backdrop-filter:saturate(140%) blur(8px);border-bottom:1px solid #eaeaea}
    .nav{max-width:var(--maxw);margin:0 auto;padding:18px 24px;display:flex;align-items:center;justify-content:space-between}
    .brand{letter-spacing:.35em;font-weight:600}
    .menu{display:flex;gap:26px;align-items:center;font-size:14px;color:var(--muted)}
    .menu a.active{color:var(--ink);font-weight:600}

    /* Page title */
    .hero{max-width:var(--maxw);margin:24px auto 6px;padding:0 24px}
    .hero h1{font-family:"Playfair Display",serif;font-size:38px;margin:18px 0 6px}
    .hero p{margin:0;color:var(--muted)}

    /* Gallery grid like provided mock */
    .wrap{max-width:var(--maxw);margin:14px auto 80px;padding:0 24px}
    .grid{display:grid;gap:var(--gap);grid-template-columns:repeat(12,1fr)}
    .cell{grid-column:span 4}
    @media (max-width: 980px){.cell{grid-column:span 6}}
    @media (max-width: 640px){.cell{grid-column:span 12}}

    .tile{position:relative;display:block;width:100%;aspect-ratio:1/1;border-radius:10px;overflow:hidden;background:#f3f4f6;box-shadow:0 10px 25px rgba(0,0,0,.06);cursor:pointer;border:none}
    .tile img{width:100%;height:100%;display:block;object-fit:cover;transition:transform .45s ease, filter .45s ease}
    .tile:hover img{transform:scale(1.05);filter:contrast(1.05)}

    /* Lightbox overlay */
    .lightbox{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(15,15,18,.85);backdrop-filter:blur(4px);z-index:50}
    .lightbox.open{display:flex}
    .lightbox__img{max-width:min(92vw,1400px);max-height:86vh;border-radius:8px;box-shadow:0 15px 45px rgba(0,0,0,.45);}
    .lightbox__btn{position:absolute;top:50%;transform:translateY(-50%);border:none;background:rgba(255,255,255,.85);width:48px;height:48px;border-radius:999px;display:grid;place-items:center;cursor:pointer}
    .lightbox__btn:focus{outline:2px solid var(--accent)}
    .lightbox__prev{left:24px}
    .lightbox__next{right:24px}
    .lightbox__close{position:absolute;top:18px;right:18px;border:none;background:rgba(255,255,255,.9);width:42px;height:42px;border-radius:999px;display:grid;place-items:center;cursor:pointer}

    .sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}

    footer{max-width:var(--maxw);margin:24px auto 56px;padding:0 24px;color:#9aa1ad;font-size:13px;text-align:center}
  </style>
</head>
<body>
  <!-- Top Navigation -->
  <header class="topbar" role="banner">
    <nav class="nav" aria-label="Primary">
      <div class="brand" aria-label="Site title"><a href="../index.html">MADISON</a></div>
      <div class="menu" role="menubar">
        <a href="index.html" role="menuitem">Work</a>
        <a href="resume.pdf" role="menuitem">Resume</a>
      </div>
    </nav>
  </header>

  <!-- Header / breadcrumb for category -->
  <section class="hero">
    <h1 id="categoryTitle">Sketches</h1>
  </section>
"""

        self.category = category
        self.cwd = cwd
        self.art_code = ""

        self._gen_art_code()

        self.footer = """

  <footer>
    © <span id="y"></span> Madison Luna
  </footer>

  <!-- Lightbox overlay -->
  <div class="lightbox" id="lightbox">
    <img class="lightbox__img" id="lightboxImg" alt="Expanded artwork" />
    <button class="lightbox__btn lightbox__prev" id="prevBtn">&#10094;</button>
    <button class="lightbox__btn lightbox__next" id="nextBtn">&#10095;</button>
    <button class="lightbox__close" id="closeBtn">&#10005;</button>
  </div>

  <script>
    document.getElementById('y').textContent = new Date().getFullYear();
    const params = new URLSearchParams(location.search);
    const titleParam = params.get('title');
    if (titleParam) document.getElementById('categoryTitle').textContent = decodeURIComponent(titleParam);

    const gallery = Array.from(document.querySelectorAll('.tile'));
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightboxImg');
    let i = 0;
    function openAt(idx){i = (idx + gallery.length) % gallery.length;lightboxImg.src = gallery[i].getAttribute('data-full');lightbox.classList.add('open');document.body.style.overflow = 'hidden';}
    function close(){lightbox.classList.remove('open');document.body.style.overflow = '';lightboxImg.src = ''}
    function next(){openAt(i+1)}
    function prev(){openAt(i-1)}
    gallery.forEach((el, idx)=>{el.addEventListener('click', ()=>openAt(idx));});
    document.getElementById('nextBtn').addEventListener('click', next);
    document.getElementById('prevBtn').addEventListener('click', prev);
    document.getElementById('closeBtn').addEventListener('click', close);
    lightbox.addEventListener('click', (e)=>{ if(e.target===lightbox) close(); });
    window.addEventListener('keydown', (e)=>{if(!lightbox.classList.contains('open')) return;if(e.key==='Escape') close();if(e.key==='ArrowRight') next();if(e.key==='ArrowLeft') prev();});
  </script>
</body>
</html>
"""

    def _gen_art_code(self):
        self.art_code += """
  <main class="wrap">
    <div class="grid" id="gallery">
"""
        for art in self.category.art_pieces:
            self.art_code += f"""
      <button class="cell tile" data-full="{no_dot_relative(self.cwd, art.path)}">
        <img alt="Ballet dancers" src="{no_dot_relative(self.cwd, art.thumbnail_path)}">
      </button>
"""

        self.art_code += """
    </div>
  </main>
"""


    def get_content(self):
        return self.header + self.art_code + self.footer
