import tkinter as tk
import cv2
from tkinter import filedialog
from tkinter import ttk
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

class SpectrometerApp:

    def __init__(self, window):
        self.window = window
        self.window.geometry("800x800")
        self.window.title("Spectrometer App")
        
        self.roi_window = None
        self.calibrate_window = None # This will now house two image panels
        self.upload_image_window = None

        self.roi_rectangles = {}
        self.roi_corrdinates = {}

        self.GUI_setup()

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- GUI Setup ---
    def GUI_setup(self):
        self.left_panel = ttk.LabelFrame(self.window, text="Controls")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.main_graph_panel = ttk.LabelFrame(self.window, text="Graph")
        self.main_graph_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.main_graph_label = tk.Label(self.main_graph_panel)
        self.main_graph_label.pack(fill=tk.BOTH, expand=True)

        self.Choose_ROI_btn = tk.Button(self.left_panel, text="Choose ROI", command=self.open_roi_window)
        self.Choose_ROI_btn.pack(padx=5, pady=5)

        self.Calibrate_btn = tk.Button(self.left_panel, text="Calibrate", command=self.open_calibrate_window)
        self.Calibrate_btn.pack(padx=5, pady=5)

        self.Upload_Actual_Image_btn = tk.Button(self.left_panel, text="Upload Image", command=self.open_upload_image_window)
        self.Upload_Actual_Image_btn.pack(padx=5, pady=5)

        self.Generate_graph_btn = tk.Button(self.left_panel, text="Generate Graph", command=self.Generate_graph)
        self.Generate_graph_btn.pack(padx=5, pady=5)

    def Generate_graph(self):
        self.message_win = tk.Toplevel(self.window)
        self.message_win.geometry("400x50")
        self.message_label = ttk.Label(self.message_win, text="N/A")
        self.message_label.pack(pady=10)

    def _create_basic_image_panel(self, parent_frame, panel_name, include_wavelength_entry=False):
        """
        Creates and configures a single image display panel within a parent frame.
        Returns the ax, canvas, line, and controls frame for that panel.
        """
        panel_container = ttk.Frame(parent_frame)
        panel_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Controls for this panel
        controls_frame = ttk.LabelFrame(panel_container, text="Controls")
        controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Matplotlib Graph for this panel
        graph_frame = ttk.LabelFrame(panel_container, text=f"Calibration Image - {panel_name}")
        graph_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        fig, ax = plt.subplots(figsize=(4, 4)) # Adjust size for two panels
        ax.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Store references on a panel-specific object or dict if needed,
        # but for now, we'll return them and store on the main window's calibration window object.
        
        # Wavelength entry
        entry = None
        if include_wavelength_entry:
            entry_label = tk.Label(controls_frame, text="Wavelength (nm)")
            entry_label.pack(padx=5, pady=2)
            entry = tk.Entry(controls_frame)
            entry.pack(padx=5, pady=2)
            
        # Initialize line and dragging state for this panel
        line = None
        dragging = False

        return {
            'ax': ax, 
            'canvas': canvas, 
            'fig': fig, # Store fig for closing later if needed
            'line': line, 
            'dragging': dragging,
            'wavelength_entry': entry,
            'controls_frame': controls_frame # Return controls_frame to add upload button
        }

    def _setup_single_calibration_window(self, parent_win, title, graph_panel_name, include_wavelength_entry=False):
        """
        Helper to set up a single calibration window's content (for ROI and Upload Image).
        """
        cal_left_panel = ttk.LabelFrame(parent_win, text="Controls")
        cal_left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        cal_graph_panel = ttk.LabelFrame(parent_win, text=graph_panel_name)
        cal_graph_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        fig, ax = plt.subplots(figsize=(5, 5))
        ax.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=cal_graph_panel)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        parent_win.fig = fig
        parent_win.ax = ax
        parent_win.canvas = canvas

        # Draggable line setup (only for Calibrate 2 and similar, but kept here for general template)
        parent_win.line = None
        parent_win.dragging = False

        if include_wavelength_entry:
            entry_label = tk.Label(cal_left_panel, text="Wavelength (nm)")
            entry_label.pack(padx=5, pady=5)
            entry = tk.Entry(cal_left_panel)
            entry.pack(padx=5, pady=5)
            parent_win.wavelength_entry = entry
        else:
            parent_win.wavelength_entry = None

        return ax, canvas, cal_left_panel

    def open_roi_window(self):
        if self.roi_window and self.roi_window.winfo_exists():
            self.roi_window.lift()
            return

        self.roi_window = tk.Toplevel(self.window)
        self.roi_window.title("Choose Region of Interest")
        self.roi_window.geometry("600x600")

        ax, canvas, left_panel = self._setup_single_calibration_window(
            self.roi_window, 
            "Choose Region of Interest", 
            "Drag Region of Interest",
            include_wavelength_entry=False
        )
        
        upload_btn = tk.Button(left_panel, text="Upload Image", 
                               command=lambda: self.upload_image_to_panel(self.roi_window)) # Changed to panel for consistency
        upload_btn.pack(padx=5, pady=5)

    def open_calibrate_window(self):
        if self.calibrate_window and self.calibrate_window.winfo_exists():
            self.calibrate_window.lift()
            return

        self.calibrate_window = tk.Toplevel(self.window)
        self.calibrate_window.title("Calibrate 2")
        self.calibrate_window.geometry("1200x600") # Wider for two images

        # Create a main frame to hold the two image panels side-by-side
        main_cal_frame = ttk.Frame(self.calibrate_window)
        main_cal_frame.pack(fill=tk.BOTH, expand=True)

        # Left Image Panel Setup
        self.calibrate_left_panel_data = self._create_basic_image_panel(
            main_cal_frame, "Left", include_wavelength_entry=True
        )
        left_upload_btn = tk.Button(self.calibrate_left_panel_data['controls_frame'], text="Upload Image 1", 
                                     command=lambda: self.upload_image_to_panel(self.calibrate_left_panel_data))
        left_upload_btn.pack(padx=5, pady=5)
        
        # Right Image Panel Setup
        self.calibrate_right_panel_data = self._create_basic_image_panel(
            main_cal_frame, "Right", include_wavelength_entry=True
        )
        right_upload_btn = tk.Button(self.calibrate_right_panel_data['controls_frame'], text="Upload Image 2", 
                                      command=lambda: self.upload_image_to_panel(self.calibrate_right_panel_data))
        right_upload_btn.pack(padx=5, pady=5)

    def open_upload_image_window(self):
        if self.upload_image_window and self.upload_image_window.winfo_exists():
            self.upload_image_window.lift()
            return

        self.upload_image_window = tk.Toplevel(self.window)
        self.upload_image_window.title("Upload Image")
        self.upload_image_window.geometry("600x600")

        ax, canvas, left_panel = self._setup_single_calibration_window(
            self.upload_image_window, 
            "Upload Image", 
            "Image",
            include_wavelength_entry=False
        )
        
        upload_btn = tk.Button(left_panel, text="Upload Image", 
                               command=lambda: self.upload_image_to_panel(self.upload_image_window)) # Changed to panel for consistency
        upload_btn.pack(padx=5, pady=5)

    def upload_image_to_panel(self, panel_data_or_window):
        """
        Uploads an image to the specified panel or single window.
        panel_data_or_window can be a window object (for ROI/Upload Image)
        or a dictionary of panel data (for Calibrate 2's left/right panels).
        """
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        # Determine if we're dealing with a direct window object or a panel data dictionary
        if isinstance(panel_data_or_window, dict):
            ax = panel_data_or_window['ax']
            canvas = panel_data_or_window['canvas']
            line_ref = panel_data_or_window # Pass the dictionary for dragging handlers
            # For this specific case, lift the parent calibrate_window
            if hasattr(self, 'calibrate_window') and self.calibrate_window.winfo_exists():
                self.calibrate_window.lift()
        else: # It's a direct Toplevel window object (ROI or Upload Image)
            ax = panel_data_or_window.ax
            canvas = panel_data_or_window.canvas
            line_ref = panel_data_or_window # Pass the window for dragging handlers
            panel_data_or_window.lift()


        uploaded_image_cv = cv2.imread(file_path)

        if uploaded_image_cv is None:
            return

        image_rgb = cv2.cvtColor(uploaded_image_cv, cv2.COLOR_BGR2RGB)

        ax.cla() 
        ax.imshow(image_rgb)
        
        ax.axis('off')
        ax.set_aspect('auto')
        
        # Draggable line logic
        if isinstance(line_ref, dict): # For Calibrate 2's left/right panels
            if line_ref['line'] is None:     
                line = ax.axhline(y=image_rgb.shape[0] / 2.0, color='r', linestyle='-', linewidth=0.5)
                line_ref['line'] = line # Store line reference in the dictionary

                canvas.mpl_connect('button_press_event', lambda event: self.on_press(event, line_ref))
                canvas.mpl_connect('button_release_event', lambda event: self.on_release(event, line_ref))
                canvas.mpl_connect('motion_notify_event', lambda event: self.on_motion(event, line_ref))
            else:
                line_ref['line'].set_visible(True)
        elif hasattr(line_ref, 'line') and line_ref.line is not None: # For single windows (ROI, Upload Image) if they ever get a line
            line_ref.line.set_visible(True)
        elif hasattr(line_ref, 'line') and line_ref.line is None: # For single windows that *might* have a line, but haven't created one yet
             # This means it's not calibrate 2. ROI and Upload image windows don't have draggable lines by default.
             # If you add draggable line to them, this part needs a similar logic as above for dict.
             pass


        canvas.draw()
    
    # --- Matplotlib Dragging Handlers ---

    def on_press(self, event, target_panel_data_or_window):
        """Handles mouse button press event on the matplotlib canvas."""
        # Determine if we're dealing with a dict (Calibrate 2 panel) or a window object (ROI/Upload Image)
        if isinstance(target_panel_data_or_window, dict):
            ax = target_panel_data_or_window['ax']
            line = target_panel_data_or_window['line']
            if event.inaxes != ax or line is None:
                return
            if line.contains(event)[0]:
                target_panel_data_or_window['dragging'] = True
        else: # It's a direct Toplevel window object
            ax = target_panel_data_or_window.ax
            line = target_panel_data_or_window.line
            if event.inaxes != ax or line is None:
                return
            if line.contains(event)[0]:
                target_panel_data_or_window.dragging = True
            
    def on_release(self, event, target_panel_data_or_window):
        """Handles mouse button release event."""
        if isinstance(target_panel_data_or_window, dict):
            target_panel_data_or_window['dragging'] = False
        else:
            target_panel_data_or_window.dragging = False

    def on_motion(self, event, target_panel_data_or_window):
        """Handles mouse motion while dragging."""
        if isinstance(target_panel_data_or_window, dict):
            if target_panel_data_or_window['dragging'] and event.inaxes == target_panel_data_or_window['ax']:
                new_y = event.ydata          
                target_panel_data_or_window['line'].set_ydata([new_y, new_y]) 
                target_panel_data_or_window['canvas'].draw()
        else:
            if target_panel_data_or_window.dragging and event.inaxes == target_panel_data_or_window.ax:
                new_y = event.ydata          
                target_panel_data_or_window.line.set_ydata([new_y, new_y]) 
                target_panel_data_or_window.canvas.draw()
            
    def on_closing(self):
        plt.close('all') 
        self.window.destroy() 

if __name__ == "__main__":
    window = tk.Tk()
    app = SpectrometerApp(window)
    window.mainloop()