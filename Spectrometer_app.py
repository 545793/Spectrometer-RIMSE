import tkinter as tk
import cv2
from tkinter import filedialog
from tkinter import ttk
from matplotlib import pyplot as plt
# Add the missing import for FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

class SpectrometerApp:

    def __init__(self, window):
        
        self.window = window
        self.window.geometry("800x800")
        self.window.title("Spectrometer App")
        
        self.cal_windows = {}
        self.cal_wl = {}
        self.Actual_Image_Window = None

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

        self.Upload_Actual_Image_btn = tk.Button(self.left_panel, text="Upload Image", command=lambda: self.Calibrate(3))
        self.Upload_Actual_Image_btn.pack(padx=5, pady=5)

        self.Generate_graph_btn = tk.Button(self.left_panel, text="Generate Graph", command=self.Generate_graph)
        self.Generate_graph_btn.pack(padx=5, pady=5)

    def Generate_graph(self):
        # This is a placeholder function from the original code
        self.message_win= tk.Toplevel(self.window)
        self.message_win.geometry("400x50")
        self.message_label = ttk.Label(self.message_win, text="N/A")
        self.message_label.pack(pady=10)

    def Calibrate(self, calibration_index):
        """
        Creates or raises a calibration window and prepares the matplotlib environment for image display and dragging.
        """
        # Check if the window already exists and is open
        if calibration_index in self.cal_windows and self.cal_windows[calibration_index].winfo_exists():
            self.cal_windows[calibration_index].lift()
            return
        
        if calibration_index==3:
            title="Upload Image"
        else:
            title=f'Calibrate {calibration_index}'

        # Create a new top-level window for calibration
        cal_win = tk.Toplevel(self.window)
        cal_win.title(title)
        cal_win.geometry("600x600")
        
        # Store the reference to the new window
        self.cal_windows[calibration_index] = cal_win

        # Left panel for controls in the calibration window
        cal_left_panel = ttk.LabelFrame(cal_win, text="Controls")
        cal_left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # --- Matplotlib Integration Panel ---
        if calibration_index==3:
            name='Image'
        else:
            name=f"Calibration Image {calibration_index}"

        cal_graph_panel = ttk.LabelFrame(cal_win, text=name)
        cal_graph_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create a matplotlib figure and axes
        fig, ax = plt.subplots(figsize=(5, 5))
        
        ax.axis('off')

        # Embed the matplotlib figure into the Tkinter window
        canvas = FigureCanvasTkAgg(fig, master=cal_graph_panel)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Store references to matplotlib objects in the calibration window dictionary to make them accessible later
        self.cal_windows[calibration_index].fig = fig
        self.cal_windows[calibration_index].ax = ax
        self.cal_windows[calibration_index].canvas = canvas
        
        # Initialize references for the draggable line and dragging state
        if calibration_index==1 or calibration_index==2:
            self.cal_windows[calibration_index].line = None
            self.cal_windows[calibration_index].dragging = False

        # --- Controls ---
        self.entry_label=tk.Label(cal_left_panel, text="Wavelength (nm)")
        self.entry_label.pack(padx=5, pady=5)
        self.entry=tk.Entry(cal_left_panel)
        self.entry.pack(padx=5, pady=5)

        # Button to upload image, passing the specific window key
        self.Upload_image_btn = tk.Button(cal_left_panel, text="Upload Image", 
                                         command=lambda: self.Upload_image(calibration_index))
        self.Upload_image_btn.pack(padx=5, pady=5)

    def Upload_image(self, calibration_index):
        
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        self.cal_windows[calibration_index].lift()

        # Load image using OpenCV
        uploaded_image_cv = cv2.imread(file_path)

        if uploaded_image_cv is None:
            return

        # Convert OpenCV image to RGB for matplotlib display
        image_rgb = cv2.cvtColor(uploaded_image_cv, cv2.COLOR_BGR2RGB)

        # Get the axes and canvas for the current calibration window
        ax = self.cal_windows[calibration_index].ax
        canvas = self.cal_windows[calibration_index].canvas
        
        # Clear existing axes content and display the image
        ax.cla() 
        ax.imshow(image_rgb)
        
        # Ensure axes are off again after clearing (just in case)
        ax.axis('off')

        # Set aspect ratio to auto for correct image display
        ax.set_aspect('auto')
        
        # --- Add Draggable Horizontal Line ---
        
        if calibration_index==1 or calibration_index==2:
            # Check if a line already exists for this window
            if self.cal_windows[calibration_index].line is None:        
                # Create the horizontal line
                line = ax.axhline(y=image_rgb.shape[0] / 2.0, color='r', linestyle='-', linewidth=0.5)
                self.cal_windows[calibration_index].line = line

                # Set up event handlers for dragging on the matplotlib canvas
                canvas.mpl_connect('button_press_event', lambda event: self.on_press(event, calibration_index))
                canvas.mpl_connect('button_release_event', lambda event: self.on_release(event, calibration_index))
                canvas.mpl_connect('motion_notify_event', lambda event: self.on_motion(event, calibration_index))
            else:
                # If the line already exists, just make sure it's visible if the image changed
                self.cal_windows[calibration_index].line.set_visible(True)

        # Redraw the canvas
        canvas.draw()
    
    # --- Matplotlib Dragging Handlers ---

    def on_press(self, event, calibration_index):
        """Handles mouse button press event on the matplotlib canvas."""
        if event.inaxes != self.cal_windows[calibration_index].ax or self.cal_windows[calibration_index].line is None:
            return
        if self.cal_windows[calibration_index].line.contains(event)[0]:
            self.cal_windows[calibration_index].dragging = True
            
    def on_release(self, event, calibration_index):
        """Handles mouse button release event."""
        self.cal_windows[calibration_index].dragging = False

    def on_motion(self, event, calibration_index):
        """Handles mouse motion while dragging."""
        if self.cal_windows[calibration_index].dragging and event.inaxes == self.cal_windows[calibration_index].ax:
            new_y = event.ydata           
            self.cal_windows[calibration_index].line.set_ydata([new_y, new_y]) 
            
            # Redraw the canvas to update the line position visually
            self.cal_windows[calibration_index].canvas.draw()
            
    def on_closing(self):
        plt.close('all') 
        self.window.destroy() 

if __name__ == "__main__":
    window = tk.Tk()
    app = SpectrometerApp(window)
    window.mainloop()