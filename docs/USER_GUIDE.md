# User guide

How the restaurant owner (or whoever sets up the menu) uses QR Menu Studio.

## Using the editor

Typical 10-minute session in front of the owner:

1. **Sign in** at `/admin/` (the account comes from `ADMIN_USERNAME` / `ADMIN_PASSWORD`).
2. **New restaurant**: type the name and pick a theme. Sensible defaults are applied (FR+EN, footer note "Prix nets, service compris."). You land in the menu editor.
3. **Fill the menu**: either *Import from photo* (see below), or type it in:
   - Add a category, type a dish name, press Enter, type the price (`12,50`, `12.5`, `12€50` all work) and press Enter again for the next dish.
   - Tap a dish to open it: description, extra sizes, allergen and diet chips, photo (the phone camera works), sold-out, visibility, duplicate, delete (with Undo).
   - Drag the ⋮⋮ handles to reorder categories and dishes, or use the *Category* select inside a dish to move it.
   - The **Editing: FR | EN** switch shows English fields with the French text as a hint; *Translate missing with AI* fills every empty English field.
4. **Aujourd'hui panel**: add a *Plat du jour* or *Formule* in one tap, with several labelled prices if needed. The *Active* toggle hides it from the public menu without deleting it.
5. **Preview**: on desktop it sits next to the editor; on a phone tap **Preview**. The theme, light/dark and photos toggles only change the preview, so you can show the owner options. *Use this theme* saves the choice.
6. **Settings**: logo, brand and accent colours, colour mode, address, phone, hours (one line per row, e.g. `Mardi – Samedi : 12h – 14h, 19h – 22h`), footer note, English on/off.
7. **Publish**. From this moment the menu is live and **its address can never change**, because printed QR codes point to it. Every later edit is saved and live immediately.

## Printing QR codes

Open **Print & QR** from the editor or dashboard (`/admin/r/<id>/print/`):

- **QR code** as SVG (vector, for print shops) or PNG (512–2048 px), in the brand colour or black. A pale brand colour is automatically darkened so the code stays scannable.
- **Table stickers** (A4 sheet): 5, 7 or 10 cm, square or round, with cut marks. 7 cm or more is recommended for tables.
- **Chevalets (table tents)**:
  - *A5 tent*: one A4 sheet, fold in the middle.
  - *A6 tent*: two tents per A4 sheet, cut and fold marks included.
  - Each tent carries the logo or name, the QR code, "Scannez pour voir le menu · Scan for the menu", the short URL and an optional line such as "Plat du jour à l'ardoise".
- Print at **100 % / actual size**. The QR always encodes the permanent URL `PUBLIC_BASE_URL/m/<slug>/`, so set `PUBLIC_BASE_URL` to the real domain **before** printing anything. If the restaurant is not published yet, the page warns you, because the code works but diners would see a 404.

## AI import & translation

- Set `ANTHROPIC_API_KEY` in `.env` to enable the AI features. The model is `claude-opus-5-5` unless you set `ANTHROPIC_MODEL`.
- **Import from photo** (`/admin/r/<id>/import/`):
  - Take or choose up to 6 photos (one per page, flat, good light).
  - Claude extracts categories, dishes, descriptions, prices as printed, and allergens or diets only when the menu marks them. Reading takes about 20–60 s.
  - On the **review screen** you fix anything flagged, such as an unreadable price, untick items, and rename categories. You can also merge into existing categories, import the specials and fill empty restaurant info (phone, address, hours).
  - Nothing is saved until you press **Save**. Imported text goes into French; tick *Also translate to English* to translate at the same time.
- **Translate missing**: in the editor, one call fills every empty English field (restaurant texts, categories, dishes, specials, price labels) from the French. There is also a per-field *Translate* button.
- **Without a key** the AI buttons are hidden and the import page explains how to enable it; everything else works normally. `AI_FAKE=1` returns a canned sample menu and fake translations, for demos and automated tests, without calling the API.
- Photos are resized to at most 2000 px before being sent. The API key is only read from the environment and is never logged.
