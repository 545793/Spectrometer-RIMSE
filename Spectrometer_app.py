import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import RectangleSelector


class SpectrometerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spectrometer")
        self.root.geometry("800x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)


        self.init_state()
        self.build_ui()


    def init_state(self):
        self.roi = None
        self.cal_model = None
        self.cal_pts = []
        self.img_handle = None
        self.line_handle = None
        self.label_handle = None
        self.line_drag = False
        self.cid = []


        self.background_img = None
        self.background_intensity = None
        self.background_wavelengths = None
        self.background_path = None


        self.fig_main, self.ax_main = plt.subplots(figsize=(6, 6))
        self.ax_main.axis('off')
        self.canvas_main = FigureCanvasTkAgg(self.fig_main, master=self.root)
       
        self.canvas_main.mpl_connect('button_press_event', self.drag_line_main)
        self.canvas_main.mpl_connect('motion_notify_event', self.drag_line_main)
        self.canvas_main.mpl_connect('button_release_event', self.drag_line_main)


    def build_ui(self):
        ctrl = ttk.LabelFrame(self.root, text="Controls")
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)


        for text, cmd in [
            ("Choose ROI", self.open_roi),
            ("Calibrate", self.open_cal),
            ("Upload Image", lambda: self.upload(main=True)),
            ("Generate Intensity vs Wavelength", self.plot_intensity_vs_wavelength),
            ("Clear All Data", self.clear_all_data)
        ]:
            ttk.Button(ctrl, text=text, command=cmd).pack(padx=5, pady=5)


        self.canvas_main.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.fig_main.tight_layout()


    def apply_roi(self, img):
        h, w = img.shape[:2]
        if self.roi:
            x, y, w_, h_ = [int(r * d) for r, d in zip(self.roi, (w, h, w, h))]
            return img[y:y + h_, x:x + w_]
        return img


    def upload(self, main=False, roi_win=None, calib_panel=None):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Error", "Cannot read image.")
            return
        img_rgb = cv2.cvtColor(self.apply_roi(img), cv2.COLOR_BGR2RGB)


        if main:
            self.ax_main.cla()
            self.img_handle = self.ax_main.imshow(img_rgb)
            h = img_rgb.shape[0]
            if self.cal_model is not None:
                slope, intercept = self.cal_model
                wav_min, wav_max = sorted([self.pixel_to_wav(0), self.pixel_to_wav(h)])
                step = max(1, int((wav_max - wav_min) / 10))
                wav_ticks = list(range(int(np.floor(wav_min)), int(np.ceil(wav_max)) + 1, step))
                y_ticks = [(wav - intercept) / slope for wav in wav_ticks]
                self.ax_main.set_yticks(y_ticks)
                self.ax_main.set_yticklabels([str(w) for w in wav_ticks])
                self.ax_main.set_ylabel("Wavelength (nm)")
            else:
                self.ax_main.set_yticks([])
                self.ax_main.set_ylabel("")
            self.ax_main.set_xticks([])
            self.ax_main.set_ylim(h, 0)
            self.ax_main.set_xlim(0, img_rgb.shape[1])
            self.draw_line()
            self.canvas_main.draw_idle()


        elif roi_win:
            self.background_path = path
            roi_win.lift()
            h, w = img_rgb.shape[:2]
            roi_win.orig = (w, h)
            self.ax_roi.cla()
            self.ax_roi.imshow(img_rgb)
            self.ax_roi.set_ylim(h, 0)
            self.ax_roi.set_xlim(0, w)
            self.ax_roi.axis('off')
            if hasattr(roi_win, 'rs'):
                roi_win.rs.set_active(False)
            roi_win.rs = RectangleSelector(self.ax_roi, self.set_roi, interactive=True, button=[1], minspanx=5)
            self.canvas_roi.draw_idle()


        elif calib_panel:
            self.cal_win.lift()
            panel = getattr(self, f"panel{calib_panel}")
            ax, can = panel['ax'], panel['canvas']
            ax.cla()
            ax.imshow(img_rgb)
            ax.set_ylim(img_rgb.shape[0], 0)
            ax.set_xlim(0, img_rgb.shape[1])
            ax.axis('off')
            y = img_rgb.shape[0] / 2
            panel['line'] = ax.axhline(y=y, color='black', linewidth=0.8)
            panel['text'] = ax.text(
                0.95 * ax.get_xlim()[1], y, '', color='r',
                ha='right', va='center',
                bbox=dict(facecolor='white', alpha=0.7, pad=1)
            )
            for ev in ('button_press_event', 'button_release_event', 'motion_notify_event'):
                can.mpl_connect(ev, lambda e, p=panel: self.drag_line(e, p))
            panel['val'] = None
            can.draw_idle()


    def process_background(self):
        """Processes the background image using the selected ROI."""
        if not self.background_path or not self.roi:
            return
        img = cv2.imread(self.background_path)
        if img is None:
            return
        img_rgb = cv2.cvtColor(self.apply_roi(img), cv2.COLOR_BGR2RGB)
        self.background_img = img_rgb
        gray_bg = cv2.cvtColor(self.background_img, cv2.COLOR_RGB2GRAY)
        self.background_intensity = np.mean(gray_bg, axis=1)
        if self.cal_model is not None:
            ys = np.arange(len(self.background_intensity))
            self.background_wavelengths = self.pixel_to_wav(ys)


    def set_roi(self, e1, e2):
        x0, y0, x1, y1 = e1.xdata, e1.ydata, e2.xdata, e2.ydata
        w0, h0 = self.roi_win.orig
        self.roi = (min(x0, x1) / w0, min(y0, y1) / h0,
                     abs(x1 - x0) / w0, abs(y1 - y0) / h0)
        self.process_background()


    def open_roi(self):
        if hasattr(self, 'roi_win') and self.roi_win.winfo_exists():
            self.roi_win.lift()
            return
        self.roi_win = tk.Toplevel(self.root)
        self.roi_win.title("Select ROI")
        frame = ttk.LabelFrame(self.roi_win, text="ROI Selector")
        frame.pack(fill=tk.BOTH, expand=True)
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.axis('off')
        ax.set_aspect('equal')
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        fig.tight_layout()
        self.ax_roi, self.canvas_roi = ax, canvas
        ttk.Button(self.roi_win, text="Upload Image", command=lambda: self.upload(roi_win=self.roi_win)).pack(pady=5)
        ttk.Button(self.roi_win, text="Save ROI", command=self.save_roi).pack(pady=5)


    def save_roi(self):
        if self.roi is not None:
            self.roi_win.destroy()
            messagebox.showinfo("Saved", "ROI and background processed.")
        else:
            messagebox.showerror("Error", "No ROI selected.")


    def open_cal(self):
        if hasattr(self, 'cal_win') and self.cal_win.winfo_exists():
            self.cal_win.lift()
            return
        self.cal_win = tk.Toplevel(self.root)
        self.cal_win.title("Calibration")
        for i in (1, 2):
            frame = ttk.LabelFrame(self.cal_win, text=f"Cal {i}")
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ttk.Button(frame, text=f"Upload {i}", command=lambda p=i: self.upload(calib_panel=p)).pack(pady=5)
            ttk.Label(frame, text="Wavelength (nm)").pack()
            entry = ttk.Entry(frame)
            entry.pack(pady=5)
            fig, ax = plt.subplots(figsize=(4, 4))
            ax.axis('off')
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            fig.tight_layout()
            panel = {'ax': ax, 'canvas': canvas, 'line': None, 'text': None, 'val': None}
            setattr(self, f"panel{i}", panel)
            entry.bind("<Return>", lambda e, p=panel, ent=entry: self.set_cal_val(e, p, ent))
        ttk.Button(self.cal_win, text="Save Calibration", command=self.save_cal).pack(pady=10)


    def set_cal_val(self, event, panel, entry):
        try:
            val = float(entry.get())
            panel['val'] = val
            y = panel['line'].get_ydata()[0]
            panel['text'].set_text(f"{val:.1f} nm")
            panel['canvas'].draw_idle()
        except:
            pass
        entry.delete(0, tk.END)


    def save_cal(self):
        pts = []
        for p in (self.panel1, self.panel2):
            if p['val'] is None:
                messagebox.showwarning("Error", "Need two calibration points")
                return
            pts.append((p['line'].get_ydata()[0], p['val']))
        ys, ws = zip(*pts)
        self.cal_model = np.polyfit(ys, ws, 1)
        messagebox.showinfo("OK", "Calibration saved")
        if self.img_handle is not None:
            self.upload(main=True)
        self.process_background()


    def pixel_to_wav(self, y):
        return np.poly1d(self.cal_model)(y) if self.cal_model is not None else None


    def draw_line(self):
        if self.img_handle is None:
            return
        img_h = self.img_handle.get_array().shape[0]
        y = img_h / 2
        if self.line_handle:
            self.line_handle.remove()
        self.line_handle = self.ax_main.axhline(y=y, color='black', linewidth=1.0)
        label = self.pixel_to_wav(y)
        txt = f"{label:.1f} nm" if label else "N/A"
        if self.label_handle:
            self.label_handle.remove()
        self.label_handle = self.ax_main.text(
            0.95 * self.ax_main.get_xlim()[1], y, txt,
            color='red', ha='right', va='center',
            bbox=dict(facecolor='white', alpha=0.7, pad=1)
        )
        self.canvas_main.draw_idle()


    def drag_line_main(self, event):
        ax = self.ax_main
        line = self.line_handle
        if event.inaxes != ax or line is None:
            return


        if event.name == 'button_press_event' and abs(event.ydata - line.get_ydata()[0]) < 10:
            self.line_drag = True
        elif event.name == 'motion_notify_event' and self.line_drag and event.ydata is not None:
            y = max(0, min(event.ydata, ax.get_ylim()[0]))
            line.set_ydata([y, y])
            if self.label_handle:
                self.label_handle.remove()
            label = self.pixel_to_wav(y)
            txt = f"{label:.1f} nm" if label is not None else "N/A"
            self.label_handle = ax.text(
                0.95 * ax.get_xlim()[1], y, txt,
                color='red', ha='right', va='center',
                bbox=dict(facecolor='white', alpha=0.7, pad=1)
            )
            self.canvas_main.draw_idle()
        elif event.name == 'button_release_event':
            self.line_drag = False


    def drag_line(self, event, panel):
        ax = panel['ax']
        line = panel['line']
        if event.inaxes != ax or line is None:
            return
        if event.name == 'button_press_event' and abs(event.ydata - line.get_ydata()[0]) < 10:
            panel['drag'] = True
        elif event.name == 'motion_notify_event' and panel.get('drag') and event.ydata is not None:
            y = max(0, min(event.ydata, ax.get_ylim()[0]))
            line.set_ydata([y, y])
            panel['text'].set_position((0.95 * ax.get_xlim()[1], y))
            panel['canvas'].draw_idle()
        elif event.name == 'button_release_event':
            panel['drag'] = False


    def plot_intensity_vs_wavelength(self):
        if self.img_handle is None:
            messagebox.showerror("Error", "Please upload an image first.")
            return
        if self.cal_model is None:
            messagebox.showerror("Error", "Please calibrate first.")
            return
        img_rgb = self.img_handle.get_array()
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        avg_intensity = np.mean(gray, axis=1)
        if self.background_intensity is not None and len(self.background_intensity) == len(avg_intensity):
            avg_intensity = avg_intensity - self.background_intensity
            # Normalize the subtracted data so the lowest value is zero
            min_val = np.min(avg_intensity)
            avg_intensity = avg_intensity - min_val
        ys = np.arange(len(avg_intensity))
        wavelengths = self.pixel_to_wav(ys)
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(wavelengths, avg_intensity, color='blue')
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Intensity")
        ax.set_title("Intensity vs. Wavelength")
        ax.set_yticks([])
        ax.set_ylabel("Intensity (Normalized)" if self.background_intensity is not None else "Intensity")
        ax.grid(True)
        fig.tight_layout()
        popup = tk.Toplevel(self.root)
        popup.title("Intensity vs. Wavelength")
        canvas = FigureCanvasTkAgg(fig, master=popup)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()


    def clear_all_data(self):
        self.init_state()
        self.ax_main.cla()
        self.ax_main.axis('off')
        self.canvas_main.draw_idle()
        messagebox.showinfo("Cleared")


    def on_exit(self):
        plt.close('all')
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SpectrometerApp(root)
    root.mainloop()
