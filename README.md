# shipwright-01

Shipwright-01 is the first Shipwright deck editor. This version opens the
Command Interface Deck from the flow JSON layout, lets you edit commands and
arguments, toggles type/applicability/requiredness, and imports or exports the
preserved-slot command-interface JSON document.

## Run

```bash
python -m shipwright01 help
python -m shipwright01
```

If `lionscliapp` is not installed into the active environment, the app will
also try to load it from the sibling repo at `F:\repo\lionscliapp\src` during
local development.
