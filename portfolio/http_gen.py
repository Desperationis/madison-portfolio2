from .utils import *
import html
import urllib.parse
import yaml
from pathlib import Path

_CSS_DIR = Path(__file__).parent / "css"


def _read_css(name: str) -> str:
    """Read a shared CSS file from portfolio/css/."""
    return (_CSS_DIR / name).read_text()


def _og_image_url(site_url, cwd, image_path):
    """Build an absolute URL for an image, for use in OG meta tags."""
    if not image_path or not site_url:
        return None
    try:
        rel = image_path.relative_to(cwd)
    except ValueError:
        return None
    return site_url.rstrip('/') + '/' + urllib.parse.quote(rel.as_posix(), safe='/')


def _meta_tags(*, title, description, url=None, image_url=None, site_name=None):
    """Build OG and Twitter Card meta tag block."""
    t = f'  <meta name="description" content="{html.escape(description)}">\n'
    t += f'  <meta property="og:title" content="{html.escape(title)}">\n'
    t += f'  <meta property="og:description" content="{html.escape(description)}">\n'
    t += f'  <meta property="og:type" content="website">\n'
    if url:
        t += f'  <meta property="og:url" content="{html.escape(url)}">\n'
    if image_url:
        t += f'  <meta property="og:image" content="{html.escape(image_url)}">\n'
    if site_name:
        t += f'  <meta property="og:site_name" content="{html.escape(site_name)}">\n'
    t += f'  <meta name="twitter:card" content="summary_large_image">\n'
    t += f'  <meta name="twitter:title" content="{html.escape(title)}">\n'
    t += f'  <meta name="twitter:description" content="{html.escape(description)}">\n'
    if image_url:
        t += f'  <meta name="twitter:image" content="{html.escape(image_url)}">\n'
    return t


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse {config_path}: {e}") from e

    if not isinstance(config, dict):
        raise ValueError(f"Config file must contain a YAML mapping, got {type(config).__name__}")

    required_keys = ['site_name', 'navigation', 'footer']
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"Config missing required keys: {', '.join(missing)}")

    if not isinstance(config['navigation'], list):
        raise ValueError("Config 'navigation' must be a list of items")

    if not isinstance(config['footer'], dict) or 'copyright' not in config['footer']:
        raise ValueError("Config 'footer' must contain a 'copyright' key")

    return config


class IndexPage:
    def __init__(self, config):
        self.config = config
        self._og_image_url = None

        # Build navigation HTML
        nav_items_html = ""
        for item in self.config['navigation']:
            nav_items_html += f'<a href="{html.escape(item["url"])}" role="menuitem">{html.escape(item["label"])}</a>\n        '

        index_css = _read_css("index.css")
        self.header = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(self.config['site_name'])} - Work</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Playfair+Display:wght@600&display=swap" rel="stylesheet">
  <style>
{index_css}  </style>
</head>
<body>
  <!-- Top Navigation -->
  <header class="topbar" role="banner">
    <nav class="nav" aria-label="Primary">
      <div class="brand" aria-label="Site title"><a href="index.html">{html.escape(self.config['site_name'])}</a></div>
      <div class="menu" role="menubar">
        {nav_items_html}
      </div>
    </nav>
  </header>

"""


        self.category_code = ""

        self.footer=f"""
  <footer>© <span id="y"></span> {html.escape(self.config['footer']['copyright'])}</footer>

  <script>
    document.getElementById('y').textContent = new Date().getFullYear();
  </script>
</body>
</html>
"""

    def set_categories(self, categories: list[Category], cwd: Path):
        # Capture OG image from first category's full-size preview
        if categories and getattr(categories[0], 'preview_path', None):
            site_url = self.config.get('site_url', '')
            self._og_image_url = _og_image_url(site_url, cwd, categories[0].preview_path)

        self.category_code += """
<main class="wrap" id="work">
    <section class="grid" aria-label="Portfolio categories">
"""
        for c in categories:
            category_thumb = c.thumbnail_p
            thumb_src = dot_relative(cwd, category_thumb)
            if thumb_src is None:
                continue
            self.category_code += f"""
      <a class="card" href="latest/{html.escape(c.name)}.html">
        <figure class="thumb">
          <img src="{html.escape(thumb_src)}" alt="{html.escape(c.name)}" loading="lazy"/>
        </figure>
        <div class="label">{html.escape(c.name)}</div>
      </a>
"""

        self.category_code += """
    </section>
</main>
"""


    def get_content(self):
        site_url = self.config.get('site_url', '')
        description = self.config.get('site_description', '')
        title = f"{self.config['site_name']} - Work"
        meta = _meta_tags(
            title=title,
            description=description,
            url=site_url,
            image_url=self._og_image_url,
            site_name=self.config['site_name'],
        )
        header = self.header.replace('</head>', f'{meta}</head>', 1)
        return header + self.category_code + self.footer



class CategoryPage:
    def __init__(self, category, cwd, config):
        self.config = config

        # Build navigation HTML with adjusted paths for category pages (in /latest/ folder)
        # We need to go up one directory from /latest/ to reach root
        nav_items_html = ""
        for item in self.config['navigation']:
            # Adjust URL for relative paths
            url = item['url']
            if url.startswith('/'):
                # Remove leading slash and add ../ for relative path from /latest/
                url = '../' + url.lstrip('/')
            elif not url.startswith(('http://', 'https://', '#', 'mailto:')):
                # Relative path needs ../ since category pages live in /latest/
                url = '../' + url
            nav_items_html += f'<a href="{html.escape(url)}" role="menuitem">{html.escape(item["label"])}</a>\n        '

        category_css = _read_css("category.css")
        self.header = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(self.config['site_name'])} - CATEGORYNAME</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Playfair+Display:wght@600&display=swap" rel="stylesheet">
  <style>
{category_css}  </style>
</head>
<body>
  <!-- Top Navigation -->
  <header class="topbar" role="banner">
    <nav class="nav" aria-label="Primary">
      <div class="brand" aria-label="Site title"><a href="../index.html">{html.escape(self.config['site_name'])}</a></div>
      <div class="menu" role="menubar">
        {nav_items_html}
      </div>
    </nav>
  </header>

  <!-- Header / breadcrumb for category -->
  <section class="hero">
    <h1 id="categoryTitle">CATEGORYNAME</h1>
  </section>
""".replace("CATEGORYNAME", html.escape(category.name))

        self.category = category
        self.cwd = cwd
        self.art_code = ""

        # Build OG meta tags for this category
        site_url = self.config.get('site_url', '')
        description = self.config.get('site_description', '')
        cat_description = f"{category.name} — {description}" if description else category.name
        cat_url = f"{site_url.rstrip('/')}/latest/{urllib.parse.quote(category.name)}.html" if site_url else ''
        og_img = _og_image_url(site_url, cwd, getattr(category, 'preview_path', None))
        self._meta = _meta_tags(
            title=f"{self.config['site_name']} - {category.name}",
            description=cat_description,
            url=cat_url,
            image_url=og_img,
            site_name=self.config['site_name'],
        )

        self._gen_art_code()

        self.footer = f"""

  <footer>
    © <span id="y"></span> {html.escape(self.config['footer']['copyright'])}
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
    function preloadAdj(){{[-1,1].forEach(d=>{{const el=gallery[(i+d+gallery.length)%gallery.length];if(el)new Image().src=el.getAttribute('data-full');}})}}
    function openAt(idx){{i = (idx + gallery.length) % gallery.length;lightboxImg.src = gallery[i].getAttribute('data-full');lightbox.classList.add('open');document.body.style.overflow = 'hidden';preloadAdj();}}
    function close(){{lightbox.classList.remove('open');document.body.style.overflow = '';lightboxImg.src = ''}}
    function next(){{openAt(i+1)}}
    function prev(){{openAt(i-1)}}
    gallery.forEach((el, idx)=>{{el.addEventListener('click', ()=>openAt(idx));}});
    document.getElementById('nextBtn').addEventListener('click', next);
    document.getElementById('prevBtn').addEventListener('click', prev);
    document.getElementById('closeBtn').addEventListener('click', close);
    lightbox.addEventListener('click', (e)=>{{ if(e.target===lightbox) close(); }});
    window.addEventListener('keydown', (e)=>{{if(!lightbox.classList.contains('open')) return;if(e.key==='Escape') close();if(e.key==='ArrowRight') next();if(e.key==='ArrowLeft') prev();}});

    /* Touch swipe support for lightbox */
    let touchX0=null;
    lightbox.addEventListener('touchstart',(e)=>{{touchX0=e.changedTouches[0].clientX;}},{{passive:true}});
    lightbox.addEventListener('touchend',(e)=>{{
      if(touchX0===null) return;
      const dx=e.changedTouches[0].clientX-touchX0;
      touchX0=null;
      if(Math.abs(dx)<50) return;
      if(dx<0) next(); else prev();
    }});
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
            full_path = no_dot_relative(self.cwd, art.path)
            thumb_path = no_dot_relative(self.cwd, art.get_thumbnail_p())
            if full_path is None or thumb_path is None:
                continue
            self.art_code += f"""
      <button class="cell tile" data-full="{html.escape(full_path)}">
        <img alt="{html.escape(art.path.stem)}" src="{html.escape(thumb_path)}" loading="lazy">
      </button>
"""

        self.art_code += """
    </div>
  </main>
"""


    def get_content(self):
        header = self.header.replace('</head>', f'{self._meta}</head>', 1)
        return header + self.art_code + self.footer
