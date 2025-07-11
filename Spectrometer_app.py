import tkinter as tk
import cv2
from tkinter import filedialog
from tkinter import ttk
from matplotlib import pyplot as plt
from PIL import Image, ImageTk

#testing

class SpectrometerApp:

    def __init__(self, window):
        
        self.window = window
        self.window.geometry("800x800")
        self.window.title("Spectrometer App")
        
        # Initialize calibration window references and calibration wavelength values
        self.cal_windows = {} 
        self.cal_wl = {}

        # Now, set up the GUI
        self.GUI_setup()
        
        # Initialize a dictionary to store references to labels in pop-up windows
        self.popup_labels = {} 

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- GUI Setup ---
    def GUI_setup(self):
        # Left panel - Controls
        self.left_panel = ttk.LabelFrame(self.window, text="Controls")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Right panel - video (Main window graph area)
        self.main_graph_panel = ttk.LabelFrame(self.window, text= "Graph")
        self.main_graph_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create the label to display the graph in the main window
        self.main_graph_label = tk.Label(self.main_graph_panel)
        self.main_graph_label.pack(fill=tk.BOTH, expand=True)

        # Calibration buttons now call the unified Calibrate function
        self.Calibrate1_btn = tk.Button(self.left_panel, text="Calibrate 1", command=lambda: self.Calibrate(1))
        self.Calibrate1_btn.pack(padx=5, pady=5)

        self.Calibrate2_btn = tk.Button(self.left_panel, text="Calibrate 2", command=lambda: self.Calibrate(2))
        self.Calibrate2_btn.pack(padx=5, pady=5)

        self.Generate_graph_btn = tk.Button(self.left_panel, text="Generate Graph", command=self.Generate_graph)
        self.Generate_graph_btn.pack(padx=5, pady=5)

    # This is a popup window for now, but the graph should be generated onto the actual window
    def Generate_graph(self):
        self.message_win= tk.Toplevel(self.window)
        self.message_win.geometry("400x50")
        self.message_label = ttk.Label(self.message_win, text="N/A")
        self.message_label.pack(pady=10)

    def Calibrate(self, calibration_index):
        """
        Creates or raises a calibration window based on the calibration_index (1 or 2).
        """
        win_key = f'cal_win_{calibration_index}'
        title = f"Calibrate {calibration_index}"

        # Check if the window already exists and is open
        if win_key in self.cal_windows and self.cal_windows[win_key].winfo_exists():
            self.cal_windows[win_key].lift()
            return

        # Create a new top-level window for calibration
        cal_win = tk.Toplevel(self.window)
        cal_win.title(title)
        cal_win.geometry("600x600")
        
        # Store the reference to the new window
        self.cal_windows[win_key] = cal_win

        # Left panel for controls in the calibration window
        cal_left_panel = ttk.LabelFrame(cal_win, text="Controls")
        cal_left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Right panel for the image display in the calibration window
        cal_graph_panel = ttk.LabelFrame(cal_win, text="Calibration Image")
        cal_graph_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create the label to display the image for calibration
        cal_graph_label = tk.Label(cal_graph_panel)
        cal_graph_label.pack(fill=tk.BOTH, expand=True)

        self.entry_label=tk.Label(cal_left_panel, text="Wavelegnth(nm)")
        self.entry_label.pack(padx=5, pady=5)
        self.entry=tk.Entry(cal_left_panel)
        self.entry.pack(padx=5, pady=5)

        # Button to upload image, passing the specific label to Upload_image
        self.Upload_image_btn = tk.Button(cal_left_panel, text="Upload Image", 
                                          command=lambda: self.Upload_image(cal_graph_label))
        self.Upload_image_btn.pack(padx=5, pady=5)


    def Upload_image(self, target_label):

        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*"), ("All files", "*.*")]
        )

        if file_path:
            # Load image using OpenCV
            uploaded_image_cv = cv2.imread(file_path)

            if uploaded_image_cv is None:
                return

            # Convert OpenCV image to PIL Image for Tkinter display
            image_rgb = cv2.cvtColor(uploaded_image_cv, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)

            # Resize image maintaining aspect ratio
            pil_image.thumbnail((500, 500), Image.Resampling.LANCZOS)
            
            tk_image = ImageTk.PhotoImage(pil_image)

            # Update the target label with the image
            target_label.config(image=tk_image)
            
            # Keep a reference to the PhotoImage object to prevent garbage collection
            target_label.image = tk_image 

    def on_closing(self):
        """
        Handles the application closing event.
        """
        self.window.destroy() 

if __name__ == "__main__":
    window = tk.Tk()
    app = SpectrometerApp(window)
    window.mainloop()