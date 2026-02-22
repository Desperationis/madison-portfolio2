# Madison's Art Portfolio

This is the source for [lunaportfolio.me](https://lunaportfolio.me). Everything updates automatically — just add your art files and push to GitHub. The website rebuilds itself.

---

## How Your Folders Work

Every folder you create at the top level becomes a **category** on your website. For example, right now you have:

```
Character works/
Finished Pieces/
Line Art/
sketches/
The Guardian Press Works/
Volition Wingspan Works/
```

Each of these shows up as its own gallery page on the site. **The folder name becomes the category name visitors see**, so name them however you want your categories to appear (capitalization and spacing matter!).

---

## Adding Art

### Step 1: Pick a category folder (or make a new one)

To create a new category, just make a new folder. For example, if you want a "Portraits" section, create a folder called `Portraits/`.

To add art to an existing category, just open that folder.

### Step 2: Drop your images in

Put your image files directly inside the category folder. That's it!

**Supported file types:** JPG, JPEG, PNG, GIF, BMP, TIFF, WebP, HEIC, HEIF

Example — adding art to "Finished Pieces":
```
Finished Pieces/
    Witch Oc Final.jpg
    WINGSPAN COVER 2.0.jpg
    Lucas Eve. Illustration.jpg
    (any new images you add go here)
```

### Step 3 (optional but recommended): Add thumbnails

Thumbnails are smaller versions of your images. They make the gallery load **way faster** because visitors see the small version first, then the full-size version only when they click on it.

Inside your category folder, create a folder called **exactly** `thumbnails/` (lowercase!), then put smaller copies of your images in there **with the exact same filename**.

```
Finished Pieces/
    Witch Oc Final.jpg              <-- full size
    WINGSPAN COVER 2.0.jpg          <-- full size
    thumbnails/
        Witch Oc Final.jpg          <-- smaller version, SAME name
        WINGSPAN COVER 2.0.jpg      <-- smaller version, SAME name
```

**The filenames must match exactly** between the main folder and the `thumbnails/` folder — same name, same extension. That's how the site knows which thumbnail goes with which image.

**How to make a thumbnail:** Open your image in any image editor (or even Preview on Mac), resize it to something smaller (around 500-800 pixels wide is good), and save it with the same filename into the `thumbnails/` folder.

> If you skip thumbnails, the site still works — it just uses the full-size images everywhere, which can make pages slower to load.

---

## Controlling the Order of Images

If you want your images to appear in a specific order, put a **number at the end of the filename** (before the extension):

```
Wingspan Inks 1.jpg      <-- shows first
Wingspan Inks 2.jpg      <-- shows second
Wingspan Inks 4.jpg      <-- shows third
Wingspan Inks 8.jpg      <-- shows fourth
```

Images with numbers are shown first (in order), then images without numbers come after.

---

## Removing Art

Just delete the image file from the folder. If it had a thumbnail, delete that too.

To remove an entire category, delete the whole folder.

---

## Quick Summary

| What you want to do | What to do |
|---|---|
| Add a new category | Create a new folder at the top level |
| Add art to a category | Drop image files into that folder |
| Make pages load faster | Add a `thumbnails/` folder with smaller copies (same filenames) |
| Control image order | Put a number at the end of the filename |
| Remove art | Delete the image (and its thumbnail if it has one) |
| Remove a category | Delete the whole folder |

---

## The config.yaml File

This file controls a few things about the site. You can open it in any text editor:

- **site_name** — The name shown in the top-left corner of the site (currently "MADISON")
- **navigation** — The menu links at the top
- **footer > copyright** — The name shown in the copyright at the bottom

You probably won't need to change this often, but it's there if you want to.

---

## What NOT to Touch

- The `latest/` folder — this is where the website files get generated automatically. Don't edit anything in here.
- The `.github/` folder — this is what makes the automatic updates work.
- `utils.py`, `CLAUDE.md`, `.gitignore`, `CNAME` — boring technical files, leave them alone.

Everything else (your art folders, `config.yaml`) is yours to change freely!
