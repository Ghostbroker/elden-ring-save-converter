#!/usr/bin/env python3
"""
Elden Ring Save Converter - GUI Version

A graphical interface for converting Elden Ring save files between Steam accounts.
Supports both vanilla saves (.sl2) and Seamless Coop saves (.co2).
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading

# Try to import drag and drop support (optional)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# Import the conversion logic
from convert_save import convert_save, validate_steam_id, detect_save_type, get_primary_steam_id


class EldenRingSaveConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Elden Ring Save Converter")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        self.root.minsize(500, 400)

        # Variables
        self.source_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.steam_id = tk.StringVar()
        self.detected_info = tk.StringVar(value="No file selected")

        self.setup_ui()

    def setup_ui(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Elden Ring Save Converter",
            font=('Helvetica', 16, 'bold')
        )
        title_label.grid(row=row, column=0, columnspan=3, pady=(0, 5))
        row += 1

        subtitle_label = ttk.Label(
            main_frame,
            text="Convert saves between Steam accounts (.sl2 and .co2)",
            font=('Helvetica', 10)
        )
        subtitle_label.grid(row=row, column=0, columnspan=3, pady=(0, 15))
        row += 1

        # Source file section
        source_label = ttk.Label(main_frame, text="Source Save File:")
        source_label.grid(row=row, column=0, sticky="w", pady=(10, 0))
        row += 1

        # Drop zone / file display
        self.drop_frame = ttk.LabelFrame(main_frame, text="", padding="10")
        self.drop_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(5, 0))
        self.drop_frame.columnconfigure(0, weight=1)

        if HAS_DND:
            drop_text = "Drag and drop save file here\nor click Browse to select"
        else:
            drop_text = "Click Browse to select a save file"

        self.drop_label = ttk.Label(
            self.drop_frame,
            text=drop_text,
            anchor="center",
            font=('Helvetica', 10)
        )
        self.drop_label.grid(row=0, column=0, sticky="ew", pady=10)

        # File path display
        self.source_entry = ttk.Entry(
            self.drop_frame,
            textvariable=self.source_path,
            state='readonly'
        )
        self.source_entry.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        browse_source_btn = ttk.Button(
            self.drop_frame,
            text="Browse...",
            command=self.browse_source
        )
        browse_source_btn.grid(row=1, column=1, padx=(5, 0), pady=(5, 0))

        # Set up drag and drop if available
        if HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind('<<Drop>>', self.on_drop)

        row += 1

        # Detected info
        self.info_label = ttk.Label(
            main_frame,
            textvariable=self.detected_info,
            font=('Helvetica', 9, 'italic')
        )
        self.info_label.grid(row=row, column=0, columnspan=3, sticky="w", pady=(5, 10))
        row += 1

        # Steam ID section
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10
        )
        row += 1

        steam_label = ttk.Label(main_frame, text="Your Steam ID:")
        steam_label.grid(row=row, column=0, sticky="w")

        steam_entry = ttk.Entry(main_frame, textvariable=self.steam_id, width=25)
        steam_entry.grid(row=row, column=1, sticky="w", padx=(10, 0))

        steam_help = ttk.Label(
            main_frame,
            text="(17-digit number, e.g., 76561198012345678)",
            font=('Helvetica', 8)
        )
        steam_help.grid(row=row, column=2, sticky="w", padx=(10, 0))
        row += 1

        # Destination section
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10
        )
        row += 1

        dest_label = ttk.Label(main_frame, text="Destination:")
        dest_label.grid(row=row, column=0, sticky="w")

        dest_entry = ttk.Entry(main_frame, textvariable=self.dest_path)
        dest_entry.grid(row=row, column=1, sticky="ew", padx=(10, 0))

        browse_dest_btn = ttk.Button(
            main_frame,
            text="Browse...",
            command=self.browse_dest
        )
        browse_dest_btn.grid(row=row, column=2, padx=(5, 0))
        row += 1

        # Convert button
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=10
        )
        row += 1

        self.convert_btn = ttk.Button(
            main_frame,
            text="Convert Save",
            command=self.convert,
            style='Accent.TButton'
        )
        self.convert_btn.grid(row=row, column=0, columnspan=3, pady=10, ipadx=20, ipady=5)
        row += 1

        # Log section
        log_label = ttk.Label(main_frame, text="Log:")
        log_label.grid(row=row, column=0, sticky="w")
        row += 1

        # Log text area with scrollbar
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=(5, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(row, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=8,
            width=50,
            state='disabled',
            font=('Consolas', 9)
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def log(self, message):
        """Add a message to the log."""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        self.root.update_idletasks()

    def clear_log(self):
        """Clear the log."""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

    def on_drop(self, event):
        """Handle file drop."""
        # Parse the dropped file path
        file_path = event.data
        # Handle paths with curly braces (Windows) or spaces
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]
        self.set_source_file(file_path)

    def browse_source(self):
        """Open file dialog to select source file."""
        file_path = filedialog.askopenfilename(
            title="Select Elden Ring Save File",
            filetypes=[
                ("Elden Ring Saves", "*.sl2 *.co2"),
                ("Vanilla Saves", "*.sl2"),
                ("Seamless Coop Saves", "*.co2"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.set_source_file(file_path)

    def set_source_file(self, file_path):
        """Set the source file and update UI."""
        self.source_path.set(file_path)

        # Auto-set destination if not already set
        if not self.dest_path.get():
            source = Path(file_path)
            dest = source.parent / f"{source.stem}_converted{source.suffix}"
            self.dest_path.set(str(dest))

        # Analyze the file
        try:
            with open(file_path, 'rb') as f:
                data = f.read()

            save_type = detect_save_type(data, Path(file_path))
            steam_id = get_primary_steam_id(data, save_type)

            if steam_id:
                self.detected_info.set(
                    f"Detected: {save_type.value} save | Current Steam ID: {steam_id}"
                )
            else:
                self.detected_info.set(
                    f"Detected: {save_type.value} save | Steam ID: Not found"
                )
        except Exception as e:
            self.detected_info.set(f"Error reading file: {e}")

    def browse_dest(self):
        """Open file dialog to select destination."""
        source = self.source_path.get()
        if source:
            initial_dir = str(Path(source).parent)
            initial_file = Path(source).name
        else:
            initial_dir = str(Path.home())
            initial_file = "ER0000.co2"

        file_path = filedialog.asksaveasfilename(
            title="Save Converted File As",
            initialdir=initial_dir,
            initialfile=initial_file,
            filetypes=[
                ("Elden Ring Saves", "*.sl2 *.co2"),
                ("Vanilla Saves", "*.sl2"),
                ("Seamless Coop Saves", "*.co2"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.dest_path.set(file_path)

    def convert(self):
        """Perform the conversion."""
        # Validate inputs
        source = self.source_path.get()
        dest = self.dest_path.get()
        steam_id_str = self.steam_id.get()

        if not source:
            messagebox.showerror("Error", "Please select a source save file.")
            return

        if not Path(source).exists():
            messagebox.showerror("Error", f"Source file not found:\n{source}")
            return

        if not dest:
            messagebox.showerror("Error", "Please specify a destination path.")
            return

        if not steam_id_str:
            messagebox.showerror("Error", "Please enter your Steam ID.")
            return

        try:
            new_steam_id = validate_steam_id(steam_id_str)
        except ValueError as e:
            messagebox.showerror("Invalid Steam ID", str(e))
            return

        # Confirm if overwriting
        if Path(dest).exists() and dest != source:
            if not messagebox.askyesno(
                "Confirm Overwrite",
                f"The destination file already exists:\n{dest}\n\nOverwrite?"
            ):
                return

        # Disable button during conversion
        self.convert_btn.configure(state='disabled')
        self.clear_log()
        self.log("Starting conversion...")

        # Run conversion in background thread
        def do_convert():
            try:
                result = convert_save(
                    Path(source),
                    new_steam_id,
                    Path(dest),
                    callback=lambda msg: self.root.after(0, lambda: self.log(msg))
                )

                def on_success():
                    self.log("")
                    self.log("=" * 40)
                    self.log("Conversion completed successfully!")
                    self.log(f"Output: {result['output_path']}")
                    messagebox.showinfo(
                        "Success",
                        f"Save converted successfully!\n\n"
                        f"Steam ID: {result['old_steam_id']} → {result['new_steam_id']}\n"
                        f"Output: {result['output_path']}"
                    )
                    self.convert_btn.configure(state='normal')

                self.root.after(0, on_success)

            except Exception as e:
                def on_error():
                    self.log("")
                    self.log(f"ERROR: {e}")
                    messagebox.showerror("Conversion Failed", str(e))
                    self.convert_btn.configure(state='normal')

                self.root.after(0, on_error)

        thread = threading.Thread(target=do_convert, daemon=True)
        thread.start()


def main():
    # Use TkinterDnD if available, otherwise regular Tk
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    # Set up styles
    style = ttk.Style()
    try:
        # Try to use a modern theme
        if 'clam' in style.theme_names():
            style.theme_use('clam')
    except Exception:
        pass

    app = EldenRingSaveConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
