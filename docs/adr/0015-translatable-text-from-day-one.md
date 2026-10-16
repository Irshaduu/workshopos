# 0015: Translatable text from day one

**Status:** Accepted (2026-10-15)

## Context

- The first client is in Kerala. A Malayalam version may be wanted later;
  it is not asked for now.
- v1 wrote every text straight into its 140 templates and its Python code,
  in English. None of it is marked for translation, so adding a language to
  v1 would mean editing every screen.
- Marking text while writing it costs little. Marking it later means finding
  every text in every file.
- Django has translation built in, so no new library is needed. It already
  ships Malayalam for its own screens, such as the admin.

## Decision

- **English is the source language.** Every text a person sees is written in
  English and marked for translation, from the first app:
  - templates: `{% translate %}`, and `{% blocktranslate %}` for text with
    values inside
  - Python: `gettext_lazy` (imported as `_`) for labels of models, fields and
    forms and for error messages; `gettext` for messages made during a request
  - JavaScript: gets its text from the page (for example a `data-`
    attribute), so the template marks it
- **Text with values inside uses named placeholders** (`%(name)s`), so a
  translation can put the words in a different order.
- **Not translated:** what people type (customer names, part names,
  concerns), numbers and codes, log messages, text only developers see (like
  the start-up error in `config/env.py`), and machine answers (`/health/`).
- **Set up with the first app (Phase 4):** `LANGUAGES` lists only English,
  and `LOCALE_PATHS` points to `locale/`. Nothing more until a second
  language exists.
- **Malayalam comes later**, when the client wants it: fill `locale/ml/`, add
  `LocaleMiddleware`, and let each person choose a language.
- **Indian date and number formats are a separate decision.** Django has no
  Indian English format, so they are set with the dates and money cores
  (Phase 4).

## Consequences

- Each text takes a few more characters to write. It is a code rule in
  `CONTRIBUTING.md`, checked in review; there is no automatic check yet.
- When Malayalam starts, the work is translating a list of texts, not
  editing every screen.
- `makemessages` and `compilemessages` need the GNU gettext tools, which are
  not installed on the laptop. They are installed when the first translation
  starts; the deploy builds the compiled files (Phase 7).
- Malayalam letters need a font that has them, on every device and on
  printed documents. Checked when Malayalam starts.
- Printed bills may need a different language from the screen. Decided with
  the client when Malayalam starts.
