# Bambu Studio: slice, check, hand off

Facts learned on a P2S (0.4 nozzle, AMS, Bambu Studio 2.9, macOS) building an 11-plate project.
Each rule names the failure it prevents. Re-check a version-specific fact before you rely on it.

## Never start a print

Slicing, loading and preparing are yours. Pressing **Print** is the user's. Never click Print or
Print plate and never press `Cmd+Shift+G` (Print plate). Leave the plate sliced and say which one.

## The command line

Binary: `/Applications/BambuStudio.app/Contents/MacOS/BambuStudio`.

```bash
BambuStudio --load-settings "machine.json;process.json" \
  --load-filaments "filament.json;filament.json" --filament-colour "#F2B8C6;#FFFFFF" \
  --load-assemble-list assemble_list.json --arrange 1 --slice 0 \
  --export-3mf /ABSOLUTE/path/project.gcode.3mf
```

- `--slice 0` slices every plate. `--export-3mf` needs an absolute path.
- `--load-assemble-list` takes `{"plates":[{"plate_name","need_arrange","objects":[...]}]}`. Each object has
  `path`, `count`, `filaments` (1-based slot) and `print_params` (any process keys, per object: walls,
  infill, brim). Objects with the same `assemble_index` merge into one object (a two-colour part from two STLs).
  Export both bodies with ONE shared offset so they stay aligned.
- Make the editable project and the sliced one with two runs: `--export-3mf x.3mf` (no `--slice`), then
  the slice run to `x.gcode.3mf`.

### The CLI does not resolve presets: flatten them yourself

A preset file says `inherits` (parent preset) and `include` (G-code templates). The CLI applies neither.
Missing `include` is silent and dangerous: the P2S gets a generic stub start G-code with **no AMS load,
no plate detection, and a fixed 205 C purge**. Flatten in this order: the `inherits` chain, then each
`include` template, then the preset's own keys (own keys win). The system presets live in
`/Applications/BambuStudio.app/Contents/Resources/profiles/BBL/{machine,filament,process}/`.

Check every sliced plate's G-code for the real P2S start:

```bash
unzip -p x.gcode.3mf Metadata/plate_1.gcode | grep -E 'M972 S19|M620 S0A|M109 S205;'
# want M972 S19 (plate detection) and M620 S0A (AMS load); "M109 S205;" alone means the stub ran
```

### The CLI defaults to Cool Plate

With no bed type the CLI slices for **Cool Plate at 35 C**, even on the P2S, whose machine preset lists Cool
Plate under `not_support_bed_type`. Set `curr_bed_type` in the process JSON (`"Textured PEI Plate"`,
`"Engineering Plate"`, ...). The filament's per-plate key then sets the bed (`textured_plate_temp`, `eng_plate_temp`).
Check `; curr_bed_type = ...` and `M190 S<temp>` in each plate's G-code. The printer checks the plate type at
start (`M972`), so the slice must match the plate on the bed.

### Reading the result

- `result.json` is written **only when the slice fails** (`error_string`). Delete it before the run;
  if it exists after, the slice failed. A stale one reads as a failure that did not happen.
- On success read the `.gcode.3mf`: `Metadata/slice_info.config` has one `<plate>` per plate with
  `index`, `prediction` (seconds), `weight` (g) and `<warning msg=...>`; `Metadata/plate_N.gcode` is the G-code;
  `Metadata/model_settings.config` has `plater_name` per plate.
- Heat commands in Bambu start G-code are indented: match `^\s*M10[49] S(\d+)`, not `^M10[49]`.
- "unknown config type" when loading a preset: the file has no `"type"` key. Bambu writes user presets
  without it (the folder says the type). Add `"type": "filament"` to a COPY for a CLI test; never to the original.

## The GUI

- **One instance.** `open -a BambuStudio file.3mf` while Studio runs can start a second instance. Several
  instances hold different loads of the same project, so the user can print a stale one. To reload: quit all
  (`pkill -TERM -x BambuStudio`), wait until `pgrep -x BambuStudio` is empty, then `open`. Error -600 means it
  was still quitting: wait and retry.
- **Startup prompts:** "New version" -> Cancel (the update is the user's call). "Restore unsaved project" ->
  Cancel when you just opened the file you want.
- Opening a `.gcode.3mf` loads the project but drops the slice: re-slice in the GUI before Print.
- After a GUI slice, compare one plate's total time and grams with the CLI's `slice_info.config`
  (`prediction`, `weight`). A match shows the GUI used the same settings; a gap means a preset or plate type differs.
- **Slice a plate:** select the plate (object list or the plate strip), `Cmd+R`. The top-right Slice all /
  Print buttons can be blocked for screen control; `Cmd+R` per plate works. Help > Keyboard Shortcuts lists the rest.
- A locked Mac returns empty screenshots: check `ioreg -n Root -d1 -a | grep -A1 IOConsoleLocked`.
- If the user brings another app forward, stop. Do not fight for focus.
- Never read or print the printer access code in `BambuStudio.conf`.

## Filament presets for third-party brands

The installed P2S profiles cover only **Bambu** and **Generic** filaments. Many brands (Inland, CookieCad)
publish no Bambu profile, only settings on product pages.

1. **Create New** (Filament gear > Custom Filaments > Create New) is the only route the AMS can use: it writes
   a full preset with its own `filament_id` (`P` + hex). "Save as" presets and imported JSON that only
   `inherits` a system preset have no own id, so the AMS cannot select them (Bambu wiki, maintainers on GitHub).
   - Vendor: pick from the list (it has INLAND, Polymaker, eSUN...), else tick "Can't find vendor I want" and type it.
   - Type: scroll the list. Serial: e.g. Basic, Plus, Matte.
   - Base preset: the list shows only filaments that are visible in System Filaments. Tick the Generic base
     (e.g. Generic PETG) there first, or the list stays grey.
   - Tick the printer (Bambu Lab P2S 0.4 nozzle). Re-read the base before Create: the list order shifts as
     you add filaments.
2. Set the values in **Studio's editor**, not in the file. Studio syncs user presets with the Bambu account and
   overwrites local file edits on the next start. Route: Custom Filaments > pencil > Edit Preset, change, save icon.
   - Nozzle temperature is per nozzle variant (tabs: Direct Drive Standard / High Flow / E3D High Flow). The
     P2S stock nozzle is Standard; set all three so a nozzle swap stays in the vendor range.
   - Density shows only with **Advanced** on. The search popup can stick: click the editor title bar.
3. Prove it: restart Studio, re-read the files in
   `~/Library/Application Support/BambuStudio/user/<uid>/filament/base/`, and slice a test part with a copy of
   each (add `"type"`); check `M109`/`M190` match.
4. The user assigns AMS slots on the Device page and runs Flow Dynamics per spool.

**Values:** start from Bambu's Generic preset for the printer. Nozzle and bed temperatures and the part fan:
keep the Generic value if it is inside the vendor's published range, else clamp to the nearest end. Keep the
machine-specific values (speeds, retraction, max volumetric speed, flow ratio, pressure advance): calibration
sets those per spool. Log each change with its source page. Unofficial presets (MakerWorld uploads, forum
JSON): compare, do not adopt without a stated reason.

## Plates and materials (Bambu wiki)

- PLA: Textured PEI 45-65 C without glue. Engineering Plate: glue required for PLA. Cool Plate 35-45 C
  (not supported by the P2S).
- With PLA and a bed above 45 C, open the door or lift the top glass: chamber heat softens PLA in the extruder.

## Is there an MCP? (checked 2026-11-27)

- **Official: no.** An open pull request adds a native, loopback-only MCP server to Bambu Studio (Preferences >
  Other, default off, port 27183; tools for profiles, params, load, slice, AMS painting):
  `bambulab/BambuStudio#12481`. Check its state before you rely on it: `gh pr view 12481 -R bambulab/BambuStudio`.
- **Community, unofficial:** `slicewise-mcp` (flattens inherits and G-code templates, audits overrides, writes
  user presets), `danielefinocchiaro/unofficial-bambu-mcp` (projects, slicing, printer status; P2S slicing tested),
  `MoraesGil/bambu-studio-mcp`, `bambu-printer-mcp` (LAN printer control). Vet any of them before install:
  source, pinned version, what it writes.
- **Printer control:** Bambu firmware accepts third-party commands only in LAN-only mode with Developer Mode
  (cloud and Bambu Handy off). In cloud mode a tool can read status, but the user starts prints.
