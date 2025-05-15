import tkinter as tk
import tkinterdnd2 as tkdnd
import os
import re
import tkinter.filedialog as filedialog
import logging
from tkinter import scrolledtext
import json
import sys
import magic
import platform
import subprocess

# Global list to hold the dropped file paths
dropped_files = []

# Global configuration dictionary
config = {}

def is_text_file(path):
    """Check if the file is a text file by attempting to read it as UTF-8."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read(1024)  # Read the first 1KB
        return True
    except UnicodeDecodeError:
        return False
    except Exception as e:
        logging.error(f"Error checking file type for {path}: {str(e)}")
        return False

# Configuration Handling
def get_config_path(config_file="config.json"):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        config_path = os.path.join(base_path, config_file)
        if not os.path.isfile(config_path):
            config_path = os.path.join(base_path, '_internal', config_file)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_path, config_file)
    return config_path

def load_config(config_file="config.json"):
    """Load configuration from a JSON file."""
    config_path = get_config_path(config_file)
    if not os.path.isfile(config_path):
        return {}
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in {config_path}.")
        return {}

def save_config(config, config_file="config.json"):
    """Save configuration to a JSON file."""
    config_path = get_config_path(config_file)
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save config: {str(e)}")

def parse_paths(data):
    """Parse the dropped data to extract file paths."""
    paths = re.findall(r'\{.*?\}|[^{}\s]+', data)
    return [p.strip('{}') for p in paths]

def drop_handler(event):
    """Handle the drop event by processing dropped files based on content."""
    paths = parse_paths(event.data)
    added = 0
    ignored = 0
    existing_names = {os.path.basename(path).lower() for path in dropped_files}
    
    for path in paths:
        basename = os.path.basename(path)
        if not os.path.isfile(path):
            logging.error(f"Ignored: {basename} (not a file)")
            ignored += 1
        elif basename.lower() in existing_names:
            logging.error(f"Ignored: {basename} (file with same name already added)")
            ignored += 1
        elif not is_text_file(path):
            logging.error(f"Ignored: {basename} (appears to be a binary file)")
            ignored += 1
        else:
            dropped_files.append(path)
            existing_names.add(basename.lower())
            logging.info(f"Added: {basename}")
            added += 1
    message = f"Summary: Added {added} files, ignored {ignored} files. Current total: {len(dropped_files)} files."
    logging.info(message)
    update_file_count()

def export_combined(output_file):
    """Export the combined content of all dropped files to the specified file and return the content."""
    if not dropped_files:
        logging.info("No files to export.")
        return None
    try:
        combined_content = ""
        for path in dropped_files:
            file_name = os.path.basename(path)
            combined_content += f"File: {file_name}\n\n"
            try:
                with open(path, 'r') as infile:
                    content = infile.read()
                    combined_content += content
            except Exception as e:
                combined_content += f"Error reading file: {str(e)}\n"
            combined_content += "\n\n"
        with open(output_file, 'w') as f:
            f.write(combined_content)
        logging.info(f"Combined file exported to {output_file}")
        dropped_files.clear()
        return combined_content
    except Exception as e:
        logging.error(f"Failed to save combined file: {str(e)}")
        return None

def browse_for_export():
    """Open a directory dialog to select the export folder and update config."""
    initial_dir = os.path.dirname(config.get("default_export_path", os.path.expanduser("~")))
    selected_dir = filedialog.askdirectory(initialdir=initial_dir)
    if selected_dir:
        full_path = os.path.join(selected_dir, "export.txt").replace('/', '\\')
        export_path_var.set(full_path)
        config["default_export_path"] = full_path
        save_config(config)

def handle_export():
    """Handle the export button click, open file if checkbox is checked, and copy to clipboard if selected."""
    output_file = export_path_var.get().strip()
    if not output_file:
        initial_dir = os.path.dirname(config.get("default_export_path", os.path.expanduser("~")))
        output_file = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=initial_dir,
            initialfile="export.txt"
        )
    if output_file:
        if os.path.isdir(output_file):
            output_file = os.path.join(output_file, "export.txt")
            logging.info(f"Export path is a directory, saving to {output_file}")
        combined_content = export_combined(output_file)
        if combined_content:
            config["default_export_path"] = output_file
            save_config(config)
            export_path_var.set(output_file)
            if open_after_export_var.get():
                open_file(output_file)
            if copy_to_clipboard_var.get():
                root.clipboard_clear()
                root.clipboard_append(combined_content)
                logging.info("Combined content copied to clipboard.")
        update_file_count()

def open_file(path):
    """Open the file with the default application based on the OS."""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(['open', path])
        else:  # Linux
            subprocess.call(['xdg-open', path])
    except Exception as e:
        logging.error(f"Failed to open file: {str(e)}")

def save_checkbox_state():
    """Save the state of the checkboxes to config."""
    config["open_after_export"] = open_after_export_var.get()
    config["copy_to_clipboard"] = copy_to_clipboard_var.get()
    save_config(config)

def update_file_count():
    """Update the file count label with the current number of files."""
    file_count_label.config(text=f"Files added: {len(dropped_files)}")

# Custom logging handler to insert logs into Tkinter Text widget
class TkinterLoggingHandler(logging.Handler):
    def __init__(self, widget):
        logging.Handler.__init__(self)
        self.widget = widget

    def emit(self, record):
        msg = self.format(record)
        tag = record.levelname
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, msg + '\n', tag)
        self.widget.configure(state='disabled')
        self.widget.yview(tk.END)

# Create the main window with DnD capabilities
root = tkdnd.Tk()
root.title("Jac Combiner")
root.geometry("600x400")

# Load configuration
config = load_config()

# Create a frame for the drop area and log display
frame = tk.Frame(root)
frame.pack(expand=True, fill="both", padx=10, pady=10)

# Create and configure the drop area label
label = tk.Label(frame, text="Drop files here", font=("Arial", 14), bg="lightgray")
label.pack(expand=True, fill="both", pady=10)

# Create and configure the file count label
file_count_label = tk.Label(frame, text="Files added: 0")
file_count_label.pack(pady=5)

# Create a subframe for export controls
export_frame = tk.Frame(frame)
export_frame.pack(fill="x", pady=5)

# Entry for export path with default or saved value
export_path_var = tk.StringVar()
if "default_export_path" in config:
    export_path_var.set(config["default_export_path"])
else:
    default_path = os.path.join(os.path.expanduser("~"), "export.txt")
    export_path_var.set(default_path)
export_entry = tk.Entry(export_frame, textvariable=export_path_var, width=50)
export_entry.grid(row=0, column=0, sticky="ew")

# Browse button
browse_button = tk.Button(export_frame, text="Browse", command=browse_for_export)
browse_button.grid(row=0, column=1, padx=5)

# Export button
export_button = tk.Button(export_frame, text="Export", command=handle_export)
export_button.grid(row=0, column=2, padx=5)

# Checkbox for opening file after export
open_after_export_var = tk.IntVar(value=config.get("open_after_export", 0))
open_checkbox = tk.Checkbutton(export_frame, text="Open", variable=open_after_export_var, command=save_checkbox_state)
open_checkbox.grid(row=0, column=3, padx=5)

# Checkbox for copying to clipboard
copy_to_clipboard_var = tk.IntVar(value=config.get("copy_to_clipboard", 0))
copy_checkbox = tk.Checkbutton(export_frame, text="Copy", variable=copy_to_clipboard_var, command=save_checkbox_state)
copy_checkbox.grid(row=0, column=4, padx=5)

# Configure the export_frame to make the entry expand
export_frame.columnconfigure(0, weight=1)

# Create a scrolled text widget for logging with fixed height
log_widget = scrolledtext.ScrolledText(frame, height=10, state='disabled')
log_widget.pack(expand=False, fill="x", pady=10)

# Configure tags for log levels
log_widget.tag_configure("ERROR", foreground="red")
log_widget.tag_configure("CRITICAL", foreground="red")
log_widget.tag_configure("WARNING", foreground="orange")
log_widget.tag_configure("INFO", foreground="black")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = TkinterLoggingHandler(log_widget)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Register the root window as a drop target
root.drop_target_register(tkdnd.DND_FILES)
root.dnd_bind('<<Drop>>', drop_handler)

# Start the application
root.mainloop()