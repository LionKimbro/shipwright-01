"""Shipwright-01 Command Interface Deck application."""

from __future__ import annotations

import sys
from pathlib import Path
import json


def _load_lionscliapp():
    """Import lionscliapp, falling back to the sibling repo during local development."""
    try:
        import lionscliapp as app
        return app
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[3]
        sibling_src = repo_root / "lionscliapp" / "src"
        if sibling_src.exists():
            sys.path.insert(0, str(sibling_src))
            import lionscliapp as app
            return app
        raise


app = _load_lionscliapp()


def _load_svg2canvasx_flow():
    """Import svg2canvasx.flow, falling back to the sibling repo during local development."""
    try:
        from svg2canvasx import flow
        return flow
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[3]
        sibling_src = repo_root / "svg-to-canvas-extractor" / "src"
        if sibling_src.exists():
            sys.path.insert(0, str(sibling_src))
            from svg2canvasx import flow
            return flow
        raise


svg2canvasx_flow = _load_svg2canvasx_flow()

import tkinter as tk
from tkinter import messagebox


SCHEMA_ID = "shipwright-01.command-interface.v0"
ARGUMENT_TYPES = [
    "string",
    "int",
    "bool",
    "path-cwd",
    "path-proj",
    "path-proj-parent",
]
ARGUMENT_TYPE_TO_FLOW = {
    "string": "string",
    "int": "int",
    "bool": "bool",
    "path-cwd": "path_cwd",
    "path-proj": "path_proj",
    "path-proj-parent": "path_proj_parent",
}
FLOW_TYPE_TO_ARGUMENT = {
    value: key for key, value in ARGUMENT_TYPE_TO_FLOW.items()
}
COMMAND_SLOTS = 6
ARGUMENT_SLOTS = 8

g = {
    "root": None,
    "canvas": None,
    "status_var": None,
    "status_label": None,
    "flow": None,
    "regions": {},
    "bindings": {},
    "widgets": {},
    "dynamic_item_ids": [],
    "command_interface": None,
    "extra_document_fields": {},
    "window_title": "Shipwright-01",
}


def create_default_command_interface():
    """Create the blank 6-by-8 command interface document."""
    commands = []
    arguments = []
    matrix = []
    command_index = 0
    while command_index < COMMAND_SLOTS:
        commands.append(
            {
                "slot": command_index,
                "name": "",
                "description_short": "",
                "description_long": "",
            }
        )
        command_index += 1
    argument_index = 0
    while argument_index < ARGUMENT_SLOTS:
        arguments.append(
            {
                "slot": argument_index,
                "name": "",
                "type": "string",
                "description_short": "",
            }
        )
        argument_index += 1
    command_index = 0
    while command_index < COMMAND_SLOTS:
        row = []
        argument_index = 0
        while argument_index < ARGUMENT_SLOTS:
            row.append(
                {
                    "applicable": False,
                    "required": False,
                }
            )
            argument_index += 1
        matrix.append(row)
        command_index += 1
    return {
        "schema": SCHEMA_ID,
        "title": "Untitled Command Interface",
        "commands": commands,
        "arguments": arguments,
        "matrix": matrix,
    }


def load_flow_document(path):
    """Load the flow JSON file from disk."""
    return svg2canvasx_flow.load_flow_file(path)


def extract_semantic_regions(flow_data):
    """Return semantic regions keyed by region label."""
    regions = {}
    for layer in flow_data.get("layers", []):
        if layer.get("role") != "annotation":
            continue
        for region in layer.get("regions", []):
            label = region.get("label")
            if not label:
                continue
            regions[label] = region
            name = region.get("name")
            if name:
                regions[name] = region
    return regions


def build_region_bindings(regions):
    """Map actual flow region names to conceptual roles used by Shipwright-01."""
    bindings = {}
    missing = []

    command_index = 1
    while command_index <= COMMAND_SLOTS:
        name_role = f"command.{command_index - 1}.name"
        short_role = f"command.{command_index - 1}.description_short"
        long_role = f"command.{command_index - 1}.description_long"
        actual_name = f"command.{command_index}.name"
        actual_short = f"command.{command_index}.description.short"
        actual_long = f"command.{command_index}.description.long"
        if actual_name in regions:
            bindings[name_role] = actual_name
        else:
            missing.append(name_role)
        if actual_short in regions:
            bindings[short_role] = actual_short
        else:
            missing.append(short_role)
        if actual_long in regions:
            bindings[long_role] = actual_long
        else:
            missing.append(long_role)
        command_index += 1

    argument_index = 1
    while argument_index <= ARGUMENT_SLOTS:
        name_role = f"argument.{argument_index - 1}.name"
        description_role = f"argument.{argument_index - 1}.description_short"
        actual_name = f"argument.{argument_index}.name"
        actual_description = f"argument.{argument_index}.description.short"
        if actual_name in regions:
            bindings[name_role] = actual_name
        else:
            missing.append(name_role)
        if actual_description in regions:
            bindings[description_role] = actual_description
        else:
            missing.append(description_role)

        for argument_type in ARGUMENT_TYPES:
            role = f"argument.{argument_index - 1}.type.{argument_type}"
            flow_type = ARGUMENT_TYPE_TO_FLOW[argument_type]
            actual_name = f"argument.{argument_index}.type.{flow_type}"
            if actual_name in regions:
                bindings[role] = actual_name
            else:
                missing.append(role)
        argument_index += 1

    command_index = 1
    while command_index <= COMMAND_SLOTS:
        argument_index = 1
        while argument_index <= ARGUMENT_SLOTS:
            applicable_role = (
                f"matrix.{command_index - 1}.{argument_index - 1}.applicable"
            )
            required_role = (
                f"matrix.{command_index - 1}.{argument_index - 1}.required"
            )
            actual_applicable = (
                f"command.{command_index}.arg.{argument_index}.applicable"
            )
            actual_required = (
                f"command.{command_index}.arg.{argument_index}.required"
            )
            if actual_applicable in regions:
                bindings[applicable_role] = actual_applicable
            else:
                missing.append(applicable_role)
            if actual_required in regions:
                bindings[required_role] = actual_required
            else:
                missing.append(required_role)
            argument_index += 1
        command_index += 1

    button_map = {
        "button.import_json": "region.button.import_json",
        "button.export_json": "region.button.export_json",
        "button.to_ship": "region.button.ship_view",
    }
    for role, actual_name in button_map.items():
        if actual_name in regions:
            bindings[role] = actual_name
        else:
            missing.append(role)

    return bindings, missing


def get_region_box(actual_name):
    """Return the bbox for an actual semantic region name."""
    region = g["regions"][actual_name]
    return region["bbox"]


def get_region_center(actual_name):
    """Return the center point of a semantic region."""
    x0, y0, x1, y1 = get_region_box(actual_name)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


def get_region_size(actual_name):
    """Return width and height of a semantic region."""
    x0, y0, x1, y1 = get_region_box(actual_name)
    return (x1 - x0, y1 - y0)


def set_status(message):
    """Write a short message to the status area."""
    status_var = g.get("status_var")
    if status_var is not None:
        status_var.set(message)


def short_error_message(prefix, exc):
    """Return a short status-line version of an exception message."""
    text = str(exc).strip() or exc.__class__.__name__
    if len(text) > 120:
        text = text[:117] + "..."
    return f"{prefix}: {text}"


def normalize_imported_document(data):
    """Load what we can from imported JSON while preserving slots and extras."""
    document = create_default_command_interface()
    extra = {}
    for key, value in data.items():
        if key not in {"schema", "title", "commands", "arguments", "matrix"}:
            extra[key] = value

    document["schema"] = str(data.get("schema") or SCHEMA_ID)
    document["title"] = str(data.get("title") or "Untitled Command Interface")

    imported_commands = data.get("commands")
    if isinstance(imported_commands, list):
        slot = 0
        while slot < COMMAND_SLOTS:
            if slot < len(imported_commands) and isinstance(imported_commands[slot], dict):
                merged = dict(imported_commands[slot])
                merged["slot"] = slot
                merged["name"] = str(imported_commands[slot].get("name") or "")
                merged["description_short"] = str(
                    imported_commands[slot].get("description_short") or ""
                )
                merged["description_long"] = str(
                    imported_commands[slot].get("description_long") or ""
                )
                document["commands"][slot] = merged
            slot += 1

    imported_arguments = data.get("arguments")
    if isinstance(imported_arguments, list):
        slot = 0
        while slot < ARGUMENT_SLOTS:
            if slot < len(imported_arguments) and isinstance(imported_arguments[slot], dict):
                merged = dict(imported_arguments[slot])
                merged["slot"] = slot
                merged["name"] = str(imported_arguments[slot].get("name") or "")
                imported_type = str(imported_arguments[slot].get("type") or "string")
                if imported_type not in ARGUMENT_TYPES:
                    imported_type = "string"
                merged["type"] = imported_type
                merged["description_short"] = str(
                    imported_arguments[slot].get("description_short") or ""
                )
                document["arguments"][slot] = merged
            slot += 1

    imported_matrix = data.get("matrix")
    if isinstance(imported_matrix, list):
        command_index = 0
        while command_index < COMMAND_SLOTS:
            if command_index >= len(imported_matrix):
                break
            row = imported_matrix[command_index]
            if not isinstance(row, list):
                command_index += 1
                continue
            argument_index = 0
            while argument_index < ARGUMENT_SLOTS:
                if argument_index >= len(row):
                    break
                cell = row[argument_index]
                if isinstance(cell, dict):
                    merged = dict(cell)
                    applicable = bool(cell.get("applicable"))
                    required = bool(cell.get("required"))
                    if required:
                        applicable = True
                    if not applicable:
                        required = False
                    merged["applicable"] = applicable
                    merged["required"] = required
                    document["matrix"][command_index][argument_index] = merged
                argument_index += 1
            command_index += 1

    return document, extra


def export_command_interface_document():
    """Return the current command interface plus preserved unknown top-level fields."""
    commit_all_widget_values()
    exported = dict(g["extra_document_fields"])
    exported["schema"] = g["command_interface"]["schema"]
    exported["title"] = g["command_interface"]["title"]
    exported["commands"] = copy_slots(g["command_interface"]["commands"])
    exported["arguments"] = copy_slots(g["command_interface"]["arguments"])
    exported["matrix"] = copy_matrix(g["command_interface"]["matrix"])
    return exported


def copy_slots(slots):
    """Copy a list of slot dictionaries."""
    copied = []
    for item in slots:
        copied.append(dict(item))
    return copied


def copy_matrix(matrix):
    """Copy the command/argument policy matrix."""
    copied = []
    for row in matrix:
        copied_row = []
        for cell in row:
            copied_row.append(dict(cell))
        copied.append(copied_row)
    return copied


def draw_static_flow_items():
    """Draw the non-interactive presentation layer from flow data."""
    svg2canvasx_flow.draw_flow_on_canvas(g["canvas"], g["flow"])


def destroy_widgets():
    """Destroy all embedded widgets and clear the widget registry."""
    for widget_data in g["widgets"].values():
        widget = widget_data.get("widget")
        if widget is not None:
            widget.destroy()
    g["widgets"] = {}


def create_embedded_widgets():
    """Create entry, text, and button widgets inside the canvas."""
    create_command_name_widgets()
    create_argument_name_widgets()
    create_command_description_widgets()
    create_argument_description_widgets()
    create_button_widgets()


def create_command_name_widgets():
    """Create the six command-name entry widgets."""
    slot = 0
    while slot < COMMAND_SLOTS:
        role = f"command.{slot}.name"
        actual_name = g["bindings"][role]
        variable = tk.StringVar(value=g["command_interface"]["commands"][slot]["name"])
        variable.trace_add("write", make_command_name_trace(slot, variable))
        entry = tk.Entry(g["canvas"], textvariable=variable, bd=0, highlightthickness=0)
        place_widget_in_region(role, entry)
        g["widgets"][role] = {"widget": entry, "var": variable}
        slot += 1


def make_command_name_trace(slot, variable):
    """Build a trace callback for a command name entry."""
    def handle(*_args):
        g["command_interface"]["commands"][slot]["name"] = variable.get()
    return handle


def create_argument_name_widgets():
    """Create the eight argument-name entry widgets."""
    slot = 0
    while slot < ARGUMENT_SLOTS:
        role = f"argument.{slot}.name"
        variable = tk.StringVar(value=g["command_interface"]["arguments"][slot]["name"])
        variable.trace_add("write", make_argument_name_trace(slot, variable))
        entry = tk.Entry(g["canvas"], textvariable=variable, bd=0, highlightthickness=0)
        place_widget_in_region(role, entry)
        g["widgets"][role] = {"widget": entry, "var": variable}
        slot += 1


def make_argument_name_trace(slot, variable):
    """Build a trace callback for an argument name entry."""
    def handle(*_args):
        g["command_interface"]["arguments"][slot]["name"] = variable.get()
    return handle


def make_argument_description_trace(slot, variable):
    """Build a trace callback for an argument short-description entry."""
    def handle(*_args):
        g["command_interface"]["arguments"][slot]["description_short"] = variable.get()
    return handle


def create_command_description_widgets():
    """Create widgets for short and long command descriptions."""
    slot = 0
    while slot < COMMAND_SLOTS:
        short_role = f"command.{slot}.description_short"
        short_variable = tk.StringVar(
            value=g["command_interface"]["commands"][slot]["description_short"]
        )
        short_variable.trace_add("write", make_command_short_trace(slot, short_variable))
        short_entry = tk.Entry(
            g["canvas"],
            textvariable=short_variable,
            bd=0,
            highlightthickness=0,
        )
        place_widget_in_region(short_role, short_entry)
        g["widgets"][short_role] = {"widget": short_entry, "var": short_variable}

        long_role = f"command.{slot}.description_long"
        long_text = tk.Text(
            g["canvas"],
            bd=0,
            highlightthickness=0,
            wrap="word",
        )
        long_text.insert("1.0", g["command_interface"]["commands"][slot]["description_long"])
        long_text.bind("<KeyRelease>", make_command_long_handler(slot, long_text))
        place_widget_in_region(long_role, long_text)
        g["widgets"][long_role] = {"widget": long_text}
        slot += 1


def create_argument_description_widgets():
    """Create the eight short argument-description entry widgets."""
    slot = 0
    while slot < ARGUMENT_SLOTS:
        role = f"argument.{slot}.description_short"
        variable = tk.StringVar(
            value=g["command_interface"]["arguments"][slot]["description_short"]
        )
        variable.trace_add("write", make_argument_description_trace(slot, variable))
        entry = tk.Entry(
            g["canvas"],
            textvariable=variable,
            bd=0,
            highlightthickness=0,
        )
        place_widget_in_region(role, entry)
        g["widgets"][role] = {"widget": entry, "var": variable}
        slot += 1


def make_command_short_trace(slot, variable):
    """Build a trace callback for short descriptions."""
    def handle(*_args):
        g["command_interface"]["commands"][slot]["description_short"] = variable.get()
    return handle


def make_command_long_handler(slot, widget):
    """Build a key handler for long descriptions."""
    def handle(_event):
        value = widget.get("1.0", "end-1c")
        g["command_interface"]["commands"][slot]["description_long"] = value
    return handle


def create_button_widgets():
    """Create the Import, Export, and to Ship buttons."""
    button_specs = [
        ("button.import_json", "Import JSON", handle_import_json),
        ("button.export_json", "Export JSON", handle_export_json),
        ("button.to_ship", "Ship View", go_to_ship_view),
    ]
    for role, label, command in button_specs:
        button = tk.Button(g["canvas"], text=label, command=command)
        place_widget_in_region(role, button)
        g["widgets"][role] = {"widget": button}


def place_widget_in_region(role, widget):
    """Place a widget inside the conceptual region role."""
    actual_name = g["bindings"][role]
    x0, y0, x1, y1 = get_region_box(actual_name)
    width = max(int(x1 - x0) - 4, 10)
    height = max(int(y1 - y0) - 4, 10)
    g["canvas"].create_window(
        x0 + 2,
        y0 + 2,
        anchor="nw",
        width=width,
        height=height,
        window=widget,
    )


def draw_page():
    """Redraw the full page from current flow and command-interface state."""
    destroy_widgets()
    g["canvas"].delete("all")
    draw_static_flow_items()
    create_embedded_widgets()
    draw_dynamic_marks()


def clear_dynamic_marks():
    """Remove previously drawn X marks."""
    for item_id in g["dynamic_item_ids"]:
        g["canvas"].delete(item_id)
    g["dynamic_item_ids"] = []


def draw_dynamic_marks():
    """Draw selected argument types and matrix policies from state."""
    clear_dynamic_marks()
    draw_argument_type_marks()
    draw_matrix_marks()


def draw_argument_type_marks():
    """Draw an X in the selected type cell for each argument."""
    argument_index = 0
    while argument_index < ARGUMENT_SLOTS:
        selected_type = g["command_interface"]["arguments"][argument_index]["type"]
        role = f"argument.{argument_index}.type.{selected_type}"
        draw_x_mark_in_role(role)
        argument_index += 1


def draw_matrix_marks():
    """Draw policy marks in the applicable/required matrix cells."""
    command_index = 0
    while command_index < COMMAND_SLOTS:
        argument_index = 0
        while argument_index < ARGUMENT_SLOTS:
            cell = g["command_interface"]["matrix"][command_index][argument_index]
            if cell["applicable"]:
                draw_x_mark_in_role(
                    f"matrix.{command_index}.{argument_index}.applicable"
                )
            if cell["required"]:
                draw_x_mark_in_role(
                    f"matrix.{command_index}.{argument_index}.required"
                )
            argument_index += 1
        command_index += 1


def draw_x_mark_in_role(role):
    """Draw an X mark centered inside a conceptual region."""
    actual_name = g["bindings"][role]
    x0, y0, x1, y1 = get_region_box(actual_name)
    pad = min((x1 - x0), (y1 - y0)) * 0.25
    first = g["canvas"].create_line(
        x0 + pad,
        y0 + pad,
        x1 - pad,
        y1 - pad,
        fill="#000000",
        width=2,
    )
    second = g["canvas"].create_line(
        x0 + pad,
        y1 - pad,
        x1 - pad,
        y0 + pad,
        fill="#000000",
        width=2,
    )
    g["dynamic_item_ids"].append(first)
    g["dynamic_item_ids"].append(second)


def install_canvas_bindings():
    """Bind canvas clicks for type and policy toggles."""
    g["canvas"].bind("<Button-1>", handle_canvas_click)


def handle_canvas_click(event):
    """Dispatch canvas clicks into type and matrix behaviors."""
    if click_hits_widget_window(event.x, event.y):
        return
    role = find_click_role(event.x, event.y)
    if role is None:
        return
    if ".type." in role:
        handle_type_cell_click(role)
    elif role.endswith(".applicable") or role.endswith(".required"):
        handle_matrix_cell_click(role)


def click_hits_widget_window(x, y):
    """Return True when the click is inside an embedded widget window."""
    for item_id in g["canvas"].find_overlapping(x, y, x, y):
        if g["canvas"].type(item_id) == "window":
            return True
    return False


def find_click_role(x, y):
    """Find the first clickable conceptual role containing the point."""
    for role in iter_clickable_roles():
        actual_name = g["bindings"].get(role)
        if actual_name is None:
            continue
        if point_in_box(x, y, get_region_box(actual_name)):
            return role
    return None


def iter_clickable_roles():
    """Yield clickable type and matrix roles."""
    argument_index = 0
    while argument_index < ARGUMENT_SLOTS:
        for argument_type in ARGUMENT_TYPES:
            yield f"argument.{argument_index}.type.{argument_type}"
        argument_index += 1

    command_index = 0
    while command_index < COMMAND_SLOTS:
        argument_index = 0
        while argument_index < ARGUMENT_SLOTS:
            yield f"matrix.{command_index}.{argument_index}.applicable"
            yield f"matrix.{command_index}.{argument_index}.required"
            argument_index += 1
        command_index += 1


def point_in_box(x, y, bbox):
    """Return True when x,y is inside the bbox."""
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def handle_type_cell_click(role):
    """Select exactly one argument type for the clicked argument row."""
    parts = role.split(".")
    argument_index = int(parts[1])
    argument_type = ".".join(parts[3:])
    g["command_interface"]["arguments"][argument_index]["type"] = argument_type
    draw_dynamic_marks()


def handle_matrix_cell_click(role):
    """Toggle applicable/required while preserving the implication rules."""
    parts = role.split(".")
    command_index = int(parts[1])
    argument_index = int(parts[2])
    field = parts[3]
    cell = g["command_interface"]["matrix"][command_index][argument_index]

    if field == "required":
        new_required = not cell["required"]
        cell["required"] = new_required
        if new_required:
            cell["applicable"] = True
    else:
        new_applicable = not cell["applicable"]
        cell["applicable"] = new_applicable
        if not new_applicable:
            cell["required"] = False

    draw_dynamic_marks()


def commit_all_widget_values():
    """Flush embedded widget text into the command-interface state."""
    slot = 0
    while slot < COMMAND_SLOTS:
        long_role = f"command.{slot}.description_long"
        widget_data = g["widgets"].get(long_role)
        if widget_data is not None:
            text_widget = widget_data["widget"]
            g["command_interface"]["commands"][slot]["description_long"] = (
                text_widget.get("1.0", "end-1c")
            )
        slot += 1


def handle_import_json():
    """Import a command-interface JSON document from the clipboard."""
    try:
        text = g["root"].clipboard_get()
        data = json.loads(text)
        command_interface, extra = normalize_imported_document(data)
    except Exception as exc:
        set_status(short_error_message("Import failed", exc))
        messagebox.showerror("Import Failed", str(exc))
        return

    g["command_interface"] = command_interface
    g["extra_document_fields"] = extra
    g["window_title"] = command_interface.get("title") or "Shipwright-01"
    update_window_title()
    draw_page()
    set_status("Imported command interface JSON from clipboard.")


def handle_export_json():
    """Export the current command-interface document to the clipboard."""
    try:
        data = export_command_interface_document()
        text = json.dumps(data, indent=2)
        g["root"].clipboard_clear()
        g["root"].clipboard_append(text)
        g["root"].update()
    except Exception as exc:
        set_status(short_error_message("Export failed", exc))
        messagebox.showerror("Export Failed", str(exc))
        return
    set_status("Exported command interface JSON to clipboard.")


def go_to_ship_view():
    """Stub navigation target for a future whole-ship view."""
    set_status("Ship view not implemented yet.")


def create_root_window():
    """Create the Tk root and canvas sized to the flow document."""
    root = tk.Tk()
    canvas_data = g["flow"].get("canvas") or {}
    width = int(round(canvas_data.get("width") or 1000))
    height = int(round(canvas_data.get("height") or 800))
    title = g["command_interface"].get("title") or "Shipwright-01"
    g["window_title"] = title
    root.title(f"Shipwright-01 - {title}")
    canvas = tk.Canvas(root, width=width, height=height, bg="white", highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")
    status_var = tk.StringVar(value="Ready.")
    status_label = tk.Label(
        root,
        textvariable=status_var,
        anchor="w",
        padx=8,
        pady=4,
        relief="sunken",
        borderwidth=1,
    )
    status_label.grid(row=1, column=0, sticky="ew")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    g["root"] = root
    g["canvas"] = canvas
    g["status_var"] = status_var
    g["status_label"] = status_label


def update_window_title():
    """Update the window title from the current command-interface title."""
    if g["root"] is None:
        return
    title = g["window_title"] or "Shipwright-01"
    g["root"].title(f"Shipwright-01 - {title}")


def initialize_runtime():
    """Load flow, regions, bindings, and blank state."""
    g["flow"] = load_flow_document(app.ctx["path.flow"])
    g["regions"] = extract_semantic_regions(g["flow"])
    g["bindings"], missing = build_region_bindings(g["regions"])
    if missing:
        names = "\n".join(missing)
        raise RuntimeError(f"Missing semantic bindings:\n{names}")
    g["command_interface"] = create_default_command_interface()
    g["extra_document_fields"] = {}


def run_deck():
    """Launch the Command Interface Deck window."""
    try:
        initialize_runtime()
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Shipwright-01 Startup Error", str(exc))
        root.destroy()
        raise

    create_root_window()
    draw_page()
    install_canvas_bindings()
    g["root"].mainloop()


def declare_application():
    """Declare the LionsCliApp application and commands."""
    repo_root = Path(__file__).resolve().parents[2]
    default_flow_path = repo_root / "data" / "command-interface-deck.flow.json"

    app.declare_app("shipwright01", "0.1.0")
    app.describe_app("Visual editor for the Shipwright-01 Command Interface Deck.")
    app.declare_projectdir(".shipwright01")
    app.declare_key("path.flow", str(default_flow_path))
    app.describe_key("path.flow", "Flow JSON file for the Command Interface Deck.")
    app.declare_cmd("", run_deck)
    app.declare_cmd("open", run_deck)
    app.describe_cmd("open", "Open the Shipwright-01 Command Interface Deck.")


def main():
    """Application entrypoint."""
    declare_application()
    app.main()
