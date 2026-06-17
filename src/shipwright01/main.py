"""Shipwright-01 application."""

from __future__ import annotations

import json
import sys
from datetime import date
from importlib import resources
from pathlib import Path


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


SHIP_SCHEMA_ID = "shipwright-01.ship.v0"
COMMAND_INTERFACE_SCHEMA_ID = "shipwright-01.command-interface.v0"
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
COMMAND_SLOTS = 6
ARGUMENT_SLOTS = 8

g = {
    "ship": None,
    "ship_extra_fields": {},
    "command_extra_fields": {},
    "flows": {},
    "windows": {},
}


def today_iso():
    """Return today's date in YYYY-MM-DD format."""
    return date.today().isoformat()


def create_default_command_interface():
    """Create a blank 6-by-8 command interface document."""
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
            row.append({"applicable": False, "required": False})
            argument_index += 1
        matrix.append(row)
        command_index += 1

    return {
        "schema": COMMAND_INTERFACE_SCHEMA_ID,
        "commands": commands,
        "arguments": arguments,
        "matrix": matrix,
    }


def create_default_ship_document():
    """Create a blank ship document with a nested command interface."""
    today = today_iso()
    return {
        "schema": SHIP_SCHEMA_ID,
        "invocation": "",
        "title": "",
        "project_dir": "",
        "created_date": today,
        "updated_date": today,
        "command_interface": create_default_command_interface(),
    }


def copy_slots(slots):
    """Copy a list of slot dictionaries."""
    copied = []
    for item in slots:
        copied.append(dict(item))
    return copied


def copy_matrix(matrix):
    """Copy a list-of-lists matrix of dictionaries."""
    copied = []
    for row in matrix:
        copied_row = []
        for cell in row:
            copied_row.append(dict(cell))
        copied.append(copied_row)
    return copied


def copy_command_interface_document(document):
    """Copy a command interface document."""
    return {
        "schema": document.get("schema") or COMMAND_INTERFACE_SCHEMA_ID,
        "commands": copy_slots(document.get("commands") or []),
        "arguments": copy_slots(document.get("arguments") or []),
        "matrix": copy_matrix(document.get("matrix") or []),
    }


def load_flow_document(path):
    """Load a flow document from disk."""
    return svg2canvasx_flow.load_flow_file(path)


def load_packaged_flow_document(filename):
    """Load a bundled flow document from package data."""
    resource = resources.files("shipwright01").joinpath("data", filename)
    with resources.as_file(resource) as resolved_path:
        return load_flow_document(resolved_path)


def extract_semantic_regions(flow_data):
    """Return annotation regions keyed by their label."""
    regions = {}
    for layer in flow_data.get("layers", []):
        if layer.get("role") != "annotation":
            continue
        for region in layer.get("regions", []):
            label = region.get("label")
            if label:
                regions[label] = region
            name = region.get("name")
            if name:
                regions[name] = region
    return regions


def extract_presentation_items(flow_data):
    """Return presentation items in drawing order."""
    items = []
    for layer in flow_data.get("layers", []):
        if layer.get("role") != "presentation":
            continue
        for item in layer.get("items", []):
            items.append(item)
    return items


def normalize_imported_command_interface(data):
    """Load what we can from a command-interface JSON document."""
    document = create_default_command_interface()
    extra = {}

    for key, value in data.items():
        if key not in {"schema", "commands", "arguments", "matrix"}:
            extra[key] = value

    document["schema"] = str(data.get("schema") or COMMAND_INTERFACE_SCHEMA_ID)

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


def normalize_imported_ship_document(data):
    """Load what we can from a full ship document."""
    document = create_default_ship_document()
    extra = {}

    for key, value in data.items():
        if key not in {
            "schema",
            "invocation",
            "title",
            "project_dir",
            "created_date",
            "updated_date",
            "command_interface",
        }:
            extra[key] = value

    document["schema"] = str(data.get("schema") or SHIP_SCHEMA_ID)
    document["invocation"] = str(data.get("invocation") or "")
    document["title"] = str(data.get("title") or "")
    document["project_dir"] = str(data.get("project_dir") or "")
    document["created_date"] = str(data.get("created_date") or today_iso())
    document["updated_date"] = str(data.get("updated_date") or document["created_date"])

    imported_command_interface = data.get("command_interface")
    if isinstance(imported_command_interface, dict):
        command_interface, command_extra = normalize_imported_command_interface(
            imported_command_interface
        )
    else:
        command_interface = create_default_command_interface()
        command_extra = {}
    document["command_interface"] = command_interface

    return document, extra, command_extra


def export_command_interface_document():
    """Return the current command-interface document plus preserved extras."""
    commit_command_long_descriptions()
    command_interface = g["ship"]["command_interface"]
    exported = dict(g["command_extra_fields"])
    exported["schema"] = command_interface["schema"]
    exported["commands"] = copy_slots(command_interface["commands"])
    exported["arguments"] = copy_slots(command_interface["arguments"])
    exported["matrix"] = copy_matrix(command_interface["matrix"])
    return exported


def export_ship_document():
    """Return the full ship document plus preserved extras."""
    exported = dict(g["ship_extra_fields"])
    exported["schema"] = g["ship"]["schema"]
    exported["invocation"] = g["ship"]["invocation"]
    exported["title"] = g["ship"]["title"]
    exported["project_dir"] = g["ship"]["project_dir"]
    exported["created_date"] = g["ship"]["created_date"]
    exported["updated_date"] = g["ship"]["updated_date"]
    exported["command_interface"] = export_command_interface_document()
    return exported


def build_command_bindings(regions):
    """Map command-deck annotation names to conceptual roles."""
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
            required_role = f"matrix.{command_index - 1}.{argument_index - 1}.required"
            actual_applicable = f"command.{command_index}.arg.{argument_index}.applicable"
            actual_required = f"command.{command_index}.arg.{argument_index}.required"
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


def box_area(bbox):
    """Return the area of a bbox."""
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def bbox_contains(outer, inner):
    """Return True if outer fully contains inner."""
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def point_in_box(x, y, bbox):
    """Return True if x,y is inside bbox."""
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def find_smallest_rect_containing_point(items, point, text_value=None):
    """Find the smallest rect whose bbox contains a point."""
    matched = None
    matched_area = None
    for item in items:
        if item.get("kind") != "rect":
            continue
        bbox = item.get("bbox")
        if not bbox:
            continue
        if not point_in_box(point[0], point[1], bbox):
            continue
        area = box_area(bbox)
        if matched is None or area < matched_area:
            matched = bbox
            matched_area = area
    return matched


def infer_ship_button_box(items, button_text):
    """Infer a ship button bbox by matching the text inside it."""
    for item in items:
        if item.get("kind") != "text":
            continue
        if item.get("text") != button_text:
            continue
        point = item.get("point")
        if point is None:
            continue
        bbox = find_smallest_rect_containing_point(items, point, button_text)
        if bbox is not None:
            return bbox
    return None


def infer_ship_command_slot_boxes(items):
    """Infer the six command slot bboxes from the ship flow."""
    boxes = []
    slot = 1
    while slot <= COMMAND_SLOTS:
        label = f"cmd.{slot}"
        found = None
        for item in items:
            if item.get("label") == label and item.get("bbox"):
                found = item.get("bbox")
                break
        boxes.append(found)
        slot += 1
    return boxes


def infer_ship_command_group_box(items, slot_boxes):
    """Infer the overall command-interface group bbox."""
    required = [bbox for bbox in slot_boxes if bbox is not None]
    if len(required) != COMMAND_SLOTS:
        return None
    matched = None
    matched_area = None
    for item in items:
        if item.get("kind") != "rect":
            continue
        bbox = item.get("bbox")
        if not bbox:
            continue
        contains_all = True
        for inner in required:
            if not bbox_contains(bbox, inner):
                contains_all = False
                break
        if not contains_all:
            continue
        area = box_area(bbox)
        if matched is None or area < matched_area:
            matched = bbox
            matched_area = area
    return matched


def build_ship_bindings(regions, flow_data):
    """Build ship-page bindings from annotation regions and inferred boxes."""
    bindings = {"regions": {}, "command_slot_boxes": [], "command_group_box": None}
    missing = []

    ship_roles = [
        "ship.invocation",
        "ship.title",
        "ship.project_dir",
        "ship.created_date",
        "ship.updated_date",
    ]
    for role in ship_roles:
        if role in regions:
            bindings["regions"][role] = role
        else:
            missing.append(role)

    items = extract_presentation_items(flow_data)
    bindings["button_import_box"] = infer_ship_button_box(items, "Import JSON")
    bindings["button_export_box"] = infer_ship_button_box(items, "Export JSON")
    if bindings["button_import_box"] is None:
        missing.append("button.import_json")
    if bindings["button_export_box"] is None:
        missing.append("button.export_json")

    bindings["command_slot_boxes"] = infer_ship_command_slot_boxes(items)
    slot_index = 0
    while slot_index < COMMAND_SLOTS:
        if bindings["command_slot_boxes"][slot_index] is None:
            missing.append(f"command_slot.{slot_index}")
        slot_index += 1

    bindings["command_group_box"] = infer_ship_command_group_box(
        items, bindings["command_slot_boxes"]
    )
    if bindings["command_group_box"] is None:
        missing.append("ship.command_interface_group")

    return bindings, missing


def short_error_message(prefix, exc):
    """Build a short status-line error."""
    text = str(exc).strip() or exc.__class__.__name__
    if len(text) > 120:
        text = text[:117] + "..."
    return f"{prefix}: {text}"


def get_window_context(page):
    """Return the context for a page if it exists."""
    return g["windows"].get(page)


def set_status(page, message):
    """Write a message into a page's status area."""
    context = get_window_context(page)
    if context is None:
        return
    context["status_var"].set(message)


def build_window_title(page):
    """Return the title text for a window."""
    ship_title = g["ship"]["title"].strip()
    if page == "ship":
        if ship_title:
            return f"Shipwright-01 - Ship - {ship_title}"
        return "Shipwright-01 - Ship"
    if ship_title:
        return f"Shipwright-01 - Command Interface Deck - {ship_title}"
    return "Shipwright-01 - Command Interface Deck"


def update_window_titles():
    """Update open window titles from current ship state."""
    for page, context in g["windows"].items():
        context["window"].title(build_window_title(page))


def make_window_context(page, window, flow_data, bindings):
    """Create a UI context for one page window."""
    canvas_data = flow_data.get("canvas") or {}
    width = int(round(canvas_data.get("width") or 1000))
    height = int(round(canvas_data.get("height") or 800))

    canvas = tk.Canvas(window, width=width, height=height, bg="white", highlightthickness=0)
    canvas.grid(row=0, column=0, sticky="nsew")

    status_var = tk.StringVar(value="Ready.")
    status_label = tk.Label(
        window,
        textvariable=status_var,
        anchor="w",
        padx=8,
        pady=4,
        relief="sunken",
        borderwidth=1,
    )
    status_label.grid(row=1, column=0, sticky="ew")

    window.grid_rowconfigure(0, weight=1)
    window.grid_columnconfigure(0, weight=1)
    window.title(build_window_title(page))

    return {
        "page": page,
        "window": window,
        "canvas": canvas,
        "status_var": status_var,
        "status_label": status_label,
        "flow": flow_data,
        "bindings": bindings,
        "regions": extract_semantic_regions(flow_data),
        "widgets": {},
        "dynamic_item_ids": [],
    }


def get_region_box(context, role):
    """Return the bbox for a conceptual role backed by an annotation region."""
    bindings = context["bindings"]
    if "regions" in bindings:
        actual_name = bindings["regions"].get(role) or bindings.get(role)
    else:
        actual_name = bindings.get(role)
    region = context["regions"][actual_name]
    return region["bbox"]


def place_widget_in_box(context, bbox, widget):
    """Embed a widget inside a bbox on the canvas."""
    width = max(int(bbox[2] - bbox[0]) - 4, 10)
    height = max(int(bbox[3] - bbox[1]) - 4, 10)
    context["canvas"].create_window(
        bbox[0] + 2,
        bbox[1] + 2,
        anchor="nw",
        width=width,
        height=height,
        window=widget,
    )


def place_widget_in_role(context, role, widget):
    """Embed a widget inside the bbox for a conceptual role."""
    place_widget_in_box(context, get_region_box(context, role), widget)


def destroy_widgets(context):
    """Destroy embedded widgets for a window context."""
    for widget_data in context["widgets"].values():
        widget = widget_data.get("widget")
        if widget is not None:
            widget.destroy()
    context["widgets"] = {}


def clear_dynamic_items(context):
    """Delete dynamic canvas marks for a window context."""
    for item_id in context["dynamic_item_ids"]:
        context["canvas"].delete(item_id)
    context["dynamic_item_ids"] = []


def draw_window(page):
    """Redraw one page window from state."""
    context = get_window_context(page)
    if context is None:
        return
    destroy_widgets(context)
    clear_dynamic_items(context)
    context["canvas"].delete("all")
    svg2canvasx_flow.draw_flow_on_canvas(context["canvas"], context["flow"])
    if page == "ship":
        create_ship_widgets(context)
        draw_ship_dynamic(context)
    else:
        create_command_widgets(context)
        draw_command_dynamic(context)


def create_ship_widgets(context):
    """Create ship-page widgets."""
    ship = g["ship"]

    invocation_var = tk.StringVar(value=ship["invocation"])
    invocation_var.trace_add("write", make_ship_field_trace("invocation", invocation_var))
    invocation_entry = tk.Entry(context["canvas"], textvariable=invocation_var, bd=0, highlightthickness=0)
    place_widget_in_role(context, "ship.invocation", invocation_entry)
    context["widgets"]["ship.invocation"] = {"widget": invocation_entry, "var": invocation_var}

    title_var = tk.StringVar(value=ship["title"])
    title_var.trace_add("write", make_ship_field_trace("title", title_var))
    title_entry = tk.Entry(context["canvas"], textvariable=title_var, bd=0, highlightthickness=0)
    place_widget_in_role(context, "ship.title", title_entry)
    context["widgets"]["ship.title"] = {"widget": title_entry, "var": title_var}

    project_dir_var = tk.StringVar(value=ship["project_dir"])
    project_dir_var.trace_add("write", make_ship_field_trace("project_dir", project_dir_var))
    project_dir_entry = tk.Entry(context["canvas"], textvariable=project_dir_var, bd=0, highlightthickness=0)
    place_widget_in_role(context, "ship.project_dir", project_dir_entry)
    context["widgets"]["ship.project_dir"] = {"widget": project_dir_entry, "var": project_dir_var}

    created_var = tk.StringVar(value=ship["created_date"])
    created_label = tk.Label(context["canvas"], textvariable=created_var, anchor="w")
    place_widget_in_role(context, "ship.created_date", created_label)
    context["widgets"]["ship.created_date"] = {"widget": created_label, "var": created_var}

    updated_var = tk.StringVar(value=ship["updated_date"])
    updated_label = tk.Label(context["canvas"], textvariable=updated_var, anchor="w")
    place_widget_in_role(context, "ship.updated_date", updated_label)
    context["widgets"]["ship.updated_date"] = {"widget": updated_label, "var": updated_var}

    import_button = tk.Button(context["canvas"], text="Import JSON", command=handle_ship_import_json)
    place_widget_in_box(context, context["bindings"]["button_import_box"], import_button)
    context["widgets"]["button.import_json"] = {"widget": import_button}

    export_button = tk.Button(context["canvas"], text="Export JSON", command=handle_ship_export_json)
    place_widget_in_box(context, context["bindings"]["button_export_box"], export_button)
    context["widgets"]["button.export_json"] = {"widget": export_button}


def create_command_widgets(context):
    """Create command-deck widgets."""
    create_command_name_widgets(context)
    create_argument_name_widgets(context)
    create_command_description_widgets(context)
    create_argument_description_widgets(context)
    create_command_buttons(context)


def make_ship_field_trace(field, variable):
    """Build a trace callback for a ship-level entry field."""
    def handle(*_args):
        g["ship"][field] = variable.get()
        mark_ship_updated()
        update_window_titles()
    return handle


def refresh_ship_date_labels():
    """Refresh the created/updated date labels if the ship window is open."""
    context = get_window_context("ship")
    if context is None:
        return
    created = context["widgets"].get("ship.created_date")
    updated = context["widgets"].get("ship.updated_date")
    if created is not None:
        created["var"].set(g["ship"]["created_date"])
    if updated is not None:
        updated["var"].set(g["ship"]["updated_date"])


def mark_ship_updated():
    """Update the ship's updated_date and refresh related UI."""
    g["ship"]["updated_date"] = today_iso()
    refresh_ship_date_labels()


def create_command_name_widgets(context):
    """Create the six command-name entry widgets."""
    slot = 0
    while slot < COMMAND_SLOTS:
        role = f"command.{slot}.name"
        variable = tk.StringVar(
            value=g["ship"]["command_interface"]["commands"][slot]["name"]
        )
        variable.trace_add("write", make_command_name_trace(slot, variable))
        entry = tk.Entry(context["canvas"], textvariable=variable, bd=0, highlightthickness=0)
        place_widget_in_role(context, role, entry)
        context["widgets"][role] = {"widget": entry, "var": variable}
        slot += 1


def make_command_name_trace(slot, variable):
    """Build a trace callback for a command name entry."""
    def handle(*_args):
        g["ship"]["command_interface"]["commands"][slot]["name"] = variable.get()
        mark_ship_updated()
        refresh_ship_command_slots()
    return handle


def create_argument_name_widgets(context):
    """Create the eight argument-name entry widgets."""
    slot = 0
    while slot < ARGUMENT_SLOTS:
        role = f"argument.{slot}.name"
        variable = tk.StringVar(
            value=g["ship"]["command_interface"]["arguments"][slot]["name"]
        )
        variable.trace_add("write", make_argument_name_trace(slot, variable))
        entry = tk.Entry(context["canvas"], textvariable=variable, bd=0, highlightthickness=0)
        place_widget_in_role(context, role, entry)
        context["widgets"][role] = {"widget": entry, "var": variable}
        slot += 1


def make_argument_name_trace(slot, variable):
    """Build a trace callback for an argument name entry."""
    def handle(*_args):
        g["ship"]["command_interface"]["arguments"][slot]["name"] = variable.get()
        mark_ship_updated()
    return handle


def create_command_description_widgets(context):
    """Create short and long command-description widgets."""
    slot = 0
    while slot < COMMAND_SLOTS:
        short_role = f"command.{slot}.description_short"
        short_var = tk.StringVar(
            value=g["ship"]["command_interface"]["commands"][slot]["description_short"]
        )
        short_var.trace_add("write", make_command_short_trace(slot, short_var))
        short_entry = tk.Entry(context["canvas"], textvariable=short_var, bd=0, highlightthickness=0)
        place_widget_in_role(context, short_role, short_entry)
        context["widgets"][short_role] = {"widget": short_entry, "var": short_var}

        long_role = f"command.{slot}.description_long"
        long_text = tk.Text(context["canvas"], bd=0, highlightthickness=0, wrap="word")
        long_text.insert("1.0", g["ship"]["command_interface"]["commands"][slot]["description_long"])
        long_text.bind("<KeyRelease>", make_command_long_handler(slot, long_text))
        place_widget_in_role(context, long_role, long_text)
        context["widgets"][long_role] = {"widget": long_text}
        slot += 1


def make_command_short_trace(slot, variable):
    """Build a trace callback for a command short description."""
    def handle(*_args):
        g["ship"]["command_interface"]["commands"][slot]["description_short"] = variable.get()
        mark_ship_updated()
    return handle


def make_command_long_handler(slot, widget):
    """Build a key handler for a command long description."""
    def handle(_event):
        g["ship"]["command_interface"]["commands"][slot]["description_long"] = widget.get("1.0", "end-1c")
        mark_ship_updated()
    return handle


def create_argument_description_widgets(context):
    """Create the eight short argument-description widgets."""
    slot = 0
    while slot < ARGUMENT_SLOTS:
        role = f"argument.{slot}.description_short"
        variable = tk.StringVar(
            value=g["ship"]["command_interface"]["arguments"][slot]["description_short"]
        )
        variable.trace_add("write", make_argument_description_trace(slot, variable))
        entry = tk.Entry(context["canvas"], textvariable=variable, bd=0, highlightthickness=0)
        place_widget_in_role(context, role, entry)
        context["widgets"][role] = {"widget": entry, "var": variable}
        slot += 1


def make_argument_description_trace(slot, variable):
    """Build a trace callback for an argument short description."""
    def handle(*_args):
        g["ship"]["command_interface"]["arguments"][slot]["description_short"] = variable.get()
        mark_ship_updated()
    return handle


def create_command_buttons(context):
    """Create Import/Export/to-Ship buttons for the command deck."""
    button_specs = [
        ("button.import_json", "Import JSON", handle_command_import_json),
        ("button.export_json", "Export JSON", handle_command_export_json),
        ("button.to_ship", "Ship View", raise_ship_window),
    ]
    for role, label, command in button_specs:
        button = tk.Button(context["canvas"], text=label, command=command)
        place_widget_in_role(context, role, button)
        context["widgets"][role] = {"widget": button}


def draw_ship_dynamic(context):
    """Draw ship-page dynamic marks."""
    slot_index = 0
    while slot_index < COMMAND_SLOTS:
        bbox = context["bindings"]["command_slot_boxes"][slot_index]
        if bbox is not None:
            command_name = g["ship"]["command_interface"]["commands"][slot_index]["name"].strip()
            if command_name:
                item_id = context["canvas"].create_rectangle(
                    bbox[0] + 1,
                    bbox[1] + 1,
                    bbox[2] - 1,
                    bbox[3] - 1,
                    outline="",
                    fill="#5b8def",
                )
                context["dynamic_item_ids"].append(item_id)
        slot_index += 1


def draw_command_dynamic(context):
    """Draw command-page dynamic marks."""
    draw_argument_type_marks(context)
    draw_matrix_marks(context)


def draw_argument_type_marks(context):
    """Draw selected type marks."""
    argument_index = 0
    while argument_index < ARGUMENT_SLOTS:
        selected_type = g["ship"]["command_interface"]["arguments"][argument_index]["type"]
        role = f"argument.{argument_index}.type.{selected_type}"
        draw_x_mark_in_role(context, role)
        argument_index += 1


def draw_matrix_marks(context):
    """Draw applicable/required marks."""
    command_index = 0
    while command_index < COMMAND_SLOTS:
        argument_index = 0
        while argument_index < ARGUMENT_SLOTS:
            cell = g["ship"]["command_interface"]["matrix"][command_index][argument_index]
            if cell["applicable"]:
                draw_x_mark_in_role(context, f"matrix.{command_index}.{argument_index}.applicable")
            if cell["required"]:
                draw_x_mark_in_role(context, f"matrix.{command_index}.{argument_index}.required")
            argument_index += 1
        command_index += 1


def draw_x_mark_in_role(context, role):
    """Draw an X mark inside a command-deck annotation region."""
    x0, y0, x1, y1 = get_region_box(context, role)
    pad = min((x1 - x0), (y1 - y0)) * 0.25
    first = context["canvas"].create_line(
        x0 + pad,
        y0 + pad,
        x1 - pad,
        y1 - pad,
        fill="#000000",
        width=2,
    )
    second = context["canvas"].create_line(
        x0 + pad,
        y1 - pad,
        x1 - pad,
        y0 + pad,
        fill="#000000",
        width=2,
    )
    context["dynamic_item_ids"].append(first)
    context["dynamic_item_ids"].append(second)


def refresh_ship_command_slots():
    """Refresh the ship page's command-slot occupancy marks."""
    context = get_window_context("ship")
    if context is None:
        return
    draw_window("ship")


def commit_command_long_descriptions():
    """Flush open command-window Text widgets into state."""
    context = get_window_context("command_interface")
    if context is None:
        return
    slot = 0
    while slot < COMMAND_SLOTS:
        role = f"command.{slot}.description_long"
        widget_data = context["widgets"].get(role)
        if widget_data is not None:
            widget = widget_data["widget"]
            g["ship"]["command_interface"]["commands"][slot]["description_long"] = widget.get("1.0", "end-1c")
        slot += 1


def click_hits_widget_window(context, x, y):
    """Return True if a click overlaps an embedded window item."""
    for item_id in context["canvas"].find_overlapping(x, y, x, y):
        if context["canvas"].type(item_id) == "window":
            return True
    return False


def install_ship_bindings(context):
    """Bind ship-page clicks."""
    context["canvas"].bind("<Button-1>", handle_ship_canvas_click)


def handle_ship_canvas_click(event):
    """Open the command deck when clicking inside its ship-page group."""
    context = get_window_context("ship")
    if context is None:
        return
    if click_hits_widget_window(context, event.x, event.y):
        return
    bbox = context["bindings"]["command_group_box"]
    if bbox is not None and point_in_box(event.x, event.y, bbox):
        open_or_raise_command_window()


def install_command_bindings(context):
    """Bind command-page clicks."""
    context["canvas"].bind("<Button-1>", handle_command_canvas_click)


def iter_clickable_command_roles():
    """Yield all clickable command-deck toggle roles."""
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


def find_command_click_role(context, x, y):
    """Return the clicked command-deck toggle role."""
    for role in iter_clickable_command_roles():
        bbox = get_region_box(context, role)
        if point_in_box(x, y, bbox):
            return role
    return None


def handle_command_canvas_click(event):
    """Handle type/matrix toggles in the command deck."""
    context = get_window_context("command_interface")
    if context is None:
        return
    if click_hits_widget_window(context, event.x, event.y):
        return
    role = find_command_click_role(context, event.x, event.y)
    if role is None:
        return
    if ".type." in role:
        handle_type_cell_click(context, role)
    elif role.endswith(".applicable") or role.endswith(".required"):
        handle_matrix_cell_click(context, role)


def handle_type_cell_click(context, role):
    """Select exactly one type for one argument."""
    parts = role.split(".")
    argument_index = int(parts[1])
    argument_type = ".".join(parts[3:])
    g["ship"]["command_interface"]["arguments"][argument_index]["type"] = argument_type
    mark_ship_updated()
    clear_dynamic_items(context)
    draw_command_dynamic(context)


def handle_matrix_cell_click(context, role):
    """Toggle applicable/required with the implication rules."""
    parts = role.split(".")
    command_index = int(parts[1])
    argument_index = int(parts[2])
    field = parts[3]
    cell = g["ship"]["command_interface"]["matrix"][command_index][argument_index]

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

    mark_ship_updated()
    clear_dynamic_items(context)
    draw_command_dynamic(context)


def raise_ship_window():
    """Raise the ship window."""
    context = get_window_context("ship")
    if context is None:
        return
    context["window"].deiconify()
    context["window"].lift()
    context["window"].focus_force()
    set_status("command_interface", "Raised Ship view.")
    set_status("ship", "Ship view ready.")


def open_or_raise_command_window():
    """Open the command deck in one reusable toplevel window."""
    existing = get_window_context("command_interface")
    if existing is not None and existing["window"].winfo_exists():
        existing["window"].deiconify()
        existing["window"].lift()
        existing["window"].focus_force()
        set_status("ship", "Raised Command Interface Deck.")
        return

    ship_context = get_window_context("ship")
    window = tk.Toplevel(ship_context["window"])
    context = make_window_context(
        "command_interface",
        window,
        g["flows"]["command_interface"],
        g["command_bindings"],
    )
    g["windows"]["command_interface"] = context
    window.protocol("WM_DELETE_WINDOW", close_command_window)
    draw_window("command_interface")
    install_command_bindings(context)
    set_status("ship", "Opened Command Interface Deck.")


def close_command_window():
    """Close the command deck window and forget its context."""
    context = get_window_context("command_interface")
    if context is None:
        return
    window = context["window"]
    g["windows"].pop("command_interface", None)
    window.destroy()
    set_status("ship", "Closed Command Interface Deck.")


def handle_ship_import_json():
    """Import a full ship document from the clipboard."""
    try:
        ship_text = get_window_context("ship")["window"].clipboard_get()
        data = json.loads(ship_text)
        ship_document, ship_extra, command_extra = normalize_imported_ship_document(data)
    except Exception as exc:
        set_status("ship", short_error_message("Import failed", exc))
        messagebox.showerror("Import Failed", str(exc))
        return

    g["ship"] = ship_document
    g["ship_extra_fields"] = ship_extra
    g["command_extra_fields"] = command_extra
    update_window_titles()
    draw_window("ship")
    if get_window_context("command_interface") is not None:
        draw_window("command_interface")
    set_status("ship", "Imported full ship JSON from clipboard.")


def handle_ship_export_json():
    """Export the full ship document to the clipboard."""
    try:
        text = json.dumps(export_ship_document(), indent=2)
        ship_window = get_window_context("ship")["window"]
        ship_window.clipboard_clear()
        ship_window.clipboard_append(text)
        ship_window.update()
    except Exception as exc:
        set_status("ship", short_error_message("Export failed", exc))
        messagebox.showerror("Export Failed", str(exc))
        return
    set_status("ship", "Exported full ship JSON to clipboard.")


def handle_command_import_json():
    """Import only the command interface document from the clipboard."""
    try:
        command_window = get_window_context("command_interface")["window"]
        text = command_window.clipboard_get()
        data = json.loads(text)
        command_interface, command_extra = normalize_imported_command_interface(data)
    except Exception as exc:
        set_status("command_interface", short_error_message("Import failed", exc))
        messagebox.showerror("Import Failed", str(exc))
        return

    g["ship"]["command_interface"] = command_interface
    g["command_extra_fields"] = command_extra
    mark_ship_updated()
    refresh_ship_date_labels()
    draw_window("command_interface")
    refresh_ship_command_slots()
    set_status("command_interface", "Imported command interface JSON from clipboard.")
    set_status("ship", "Command Interface Deck updated from clipboard.")


def handle_command_export_json():
    """Export only the command interface document to the clipboard."""
    try:
        text = json.dumps(export_command_interface_document(), indent=2)
        command_window = get_window_context("command_interface")["window"]
        command_window.clipboard_clear()
        command_window.clipboard_append(text)
        command_window.update()
    except Exception as exc:
        set_status("command_interface", short_error_message("Export failed", exc))
        messagebox.showerror("Export Failed", str(exc))
        return
    set_status("command_interface", "Exported command interface JSON to clipboard.")


def initialize_runtime():
    """Load flows, build bindings, and create default ship state."""
    g["flows"]["ship"] = load_packaged_flow_document("ship.flow.json")
    g["flows"]["command_interface"] = load_packaged_flow_document(
        "command-interface-deck.flow.json"
    )

    ship_regions = extract_semantic_regions(g["flows"]["ship"])
    command_regions = extract_semantic_regions(g["flows"]["command_interface"])

    g["ship_bindings"], ship_missing = build_ship_bindings(ship_regions, g["flows"]["ship"])
    g["command_bindings"], command_missing = build_command_bindings(command_regions)

    missing = []
    for item in ship_missing:
        missing.append(f"ship: {item}")
    for item in command_missing:
        missing.append(f"command_interface: {item}")
    if missing:
        raise RuntimeError("Missing semantic bindings:\n" + "\n".join(missing))

    g["ship"] = create_default_ship_document()
    g["ship_extra_fields"] = {}
    g["command_extra_fields"] = {}


def create_ship_root_window():
    """Create the main ship root window and render it."""
    root = tk.Tk()
    context = make_window_context("ship", root, g["flows"]["ship"], g["ship_bindings"])
    g["windows"]["ship"] = context
    draw_window("ship")
    install_ship_bindings(context)
    return root


def run_deck():
    """Launch the Ship page as the main application window."""
    try:
        initialize_runtime()
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Shipwright-01 Startup Error", str(exc))
        root.destroy()
        raise

    root = create_ship_root_window()
    root.mainloop()


def declare_application():
    """Declare the LionsCliApp application and commands."""
    app.declare_app("shipwright01", "0.1.0")
    app.describe_app("Visual editor for Shipwright-01.")
    app.declare_projectdir(".shipwright01")
    app.declare_cmd("", run_deck)
    app.declare_cmd("open", run_deck)
    app.describe_cmd("open", "Open the Ship page.")


def main():
    """Application entrypoint."""
    declare_application()
    app.main()
