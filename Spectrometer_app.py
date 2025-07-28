import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import RectangleSelector

class SpectrometerApp:
    def __init__(self, root):
        self.root = root; self.root.title("Spectrometer")
        self.root.geometry("800x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.init_state(); self.build_ui()

    def init_state(self):
        self.roi = None  # (x_ratio, y, w_ratio, h_ratio)
        self.cal_pts = []  # list of (y_pixel, wavelength)
        self.cal_model = None
        self.fig_main, self.ax_main = plt.subplots(figsize=(6,6))
        self.ax_main.axis('off')
        self.canvas_main = FigureCanvasTkAgg(self.fig_main, master=self.root)
        self.img_handle = None
        self.line_handle = None
        self.line_drag = False
        self.cid = []

    def build_ui(self):
        ctrl = ttk.LabelFrame(self.root, text="Controls")
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        for text, cmd in [("Choose ROI", self.open_roi),
                          ("Calibrate", self.open_cal),
                          ("Upload Image", lambda:self.upload(main=True))]:
            ttk.Button(ctrl, text=text, command=cmd).pack(padx=5,pady=5)
        self.canvas_main.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.fig_main.tight_layout()

    def apply_roi(self, img):
        h, w = img.shape[:2]
        if self.roi:
            x,y,w_,h_ = [int(r*d) for r,d in zip(self.roi, (w,h,w,h))]
            return img[y:y+h_, x:x+w_]
        return img

    def upload(self, main=False, roi_win=None, calib_panel=None):
        path = filedialog.askopenfilename(filetypes=[("Image files","*.png;*.jpg;*.jpeg;*.bmp")])
        if not path: return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Error","Cannot read image."); return
        img = cv2.cvtColor(self.apply_roi(img), cv2.COLOR_BGR2RGB)
        if main:
            self.ax_main.cla()
            self.img_handle = self.ax_main.imshow(img)
            h = img.shape[0]
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
                self.ax_main.set_yticklabels([])
                self.ax_main.set_ylabel("")
            self.ax_main.set_xticks([])
            self.ax_main.set_ylim(h, 0)
            self.ax_main.set_xlim(0, img.shape[1])
            self.draw_line();self.canvas_main.draw_idle()  # <-- Make sure this runs EVERY time after drawing!
        elif roi_win:
            roi_win.lift()
            h,w=img.shape[:2]; roi_win.orig = (w,h)
            self.ax_roi.cla(); self.ax_roi.imshow(img)
            self.ax_roi.set_ylim(h,0); self.ax_roi.set_xlim(0,w)
            self.ax_roi.axis('off')
            if hasattr(roi_win,'rs'): roi_win.rs.set_active(False)
            roi_win.rs = RectangleSelector(self.ax_roi, self.set_roi, interactive=True, button=[1], minspanx=5)
            self.canvas_roi.draw_idle()
        elif calib_panel:
            self.cal_win.lift()
            panel = getattr(self, f"panel{calib_panel}")
            ax, can = panel['ax'], panel['canvas']
            ax.cla()
            ax.imshow(img)
            ax.set_ylim(img.shape[0], 0)
            ax.set_xlim(0, img.shape[1])
            ax.axis('off')
            y = img.shape[0] / 2
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

    def set_roi(self, e1,e2):
        x0,y0,x1,y1 = e1.xdata,e1.ydata,e2.xdata,e2.ydata
        w0,h0 = self.roi_win.orig; self.roi = (min(x0,x1)/w0, min(y0,y1)/h0,
                                               abs(x1-x0)/w0, abs(y1-y0)/h0)

    def open_roi(self):
        if hasattr(self, 'roi_win') and self.roi_win.winfo_exists():
            self.roi_win.lift()
            return
        self.roi_win = tk.Toplevel(self.root); self.roi_win.title("Select ROI")
        frame = ttk.LabelFrame(self.roi_win, text="ROI Selector"); frame.pack(fill=tk.BOTH, expand=True)
        fig, ax = plt.subplots(figsize=(5,5))
        ax.axis('off'); ax.set_aspect('equal')
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        fig.tight_layout()
        self.ax_roi, self.canvas_roi = ax, canvas
        ttk.Button(self.roi_win, text="Upload Image", command=lambda:self.upload(roi_win=self.roi_win)).pack(pady=5)
        ttk.Button(self.roi_win, text="Save ROI", command=self.save_roi).pack(pady=5)


    def open_cal(self):
        if hasattr(self, 'cal_win') and self.cal_win.winfo_exists():
            self.cal_win.lift()
            return
        self.cal_win = tk.Toplevel(self.root); self.cal_win.title("Calibration")
        self.canvas_cal = {}
        for i in (1, 2):
            frame = ttk.LabelFrame(self.cal_win, text=f"Cal {i}")
            frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ttk.Button(frame, text=f"Upload {i}", command=lambda p=i: self.upload(calib_panel=p)).pack(pady=(5, 2))
            ttk.Label(frame, text="Wavelength (nm)").pack()
            entry = ttk.Entry(frame); entry.pack(pady=(0, 5))
            fig, ax = plt.subplots(figsize=(4, 4)); ax.axis('off'); ax.set_aspect('equal')
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True); fig.tight_layout()
            panel = {'ax': ax, 'canvas': canvas, 'line': None, 'text': None, 'val': None}
            setattr(self, f"panel{i}", panel); self.canvas_cal[i] = canvas
            entry.bind("<Return>", lambda e, p=panel, ent=entry: self.set_cal_val(e, p, ent))
        ttk.Button(self.cal_win, text="Save Calibration", command=self.save_cal).pack(pady=10)

    def save_roi(self):
        messagebox.showinfo("Saved", "ROI saved")
        if self.img_handle is not None:
            self.upload(main=True)  

    def drag_line(self, event, panel):
        ax = panel['ax']
        line = panel['line']
        if event.inaxes != ax or line is None:
            return
        y0 = line.get_ydata()[0]
        if event.name == 'button_press_event' and abs(event.ydata - y0) < 10:
            panel['drag'] = True
        elif event.name == 'motion_notify_event' and panel.get('drag') and event.ydata is not None:
            y = max(0, min(event.ydata, ax.get_ylim()[0]))  
            line.set_ydata([y, y])
            panel['text'].set_position((0.95 * ax.get_xlim()[1], y))
            panel['canvas'].draw_idle()
        elif event.name == 'button_release_event':
            panel['drag'] = False

    def set_cal_val(self, event, panel, entry):
        try:
            val=float(entry.get()); panel['val']=val
            y=panel['line'].get_ydata()[0]
            panel['text'].set_text(f"{val:.1f} nm"); panel['canvas'].draw_idle()
        except: pass
        entry.delete(0,tk.END)

    def save_cal(self):
        pts = []
        for p in (self.panel1, self.panel2):
            if p['val'] is None or p['line'] is None:
                messagebox.showwarning("Error","Need two calibration points"); return
            pts.append((p['line'].get_ydata()[0], p['val']))
        ys, ws = zip(*pts)
        self.cal_model = np.polyfit(ys, ws, 1)
        messagebox.showinfo("OK","Calibration saved")
        if self.img_handle is not None: self.upload(main=True)

    def pixel_to_wav(self, y):
        return np.poly1d(self.cal_model)(y) if self.cal_model is not None else None

    def draw_line(self, force=False):
        if self.img_handle is None: return
        img_h = self.img_handle.get_array().shape[0]
        if not force and self.line_handle and self.line_handle in self.ax_main.lines:
            return
        if self.cal_model is None:
            self.remove_line()
            return
        if self.line_handle:
            self.line_handle.remove()
        y = img_h/2
        self.line_handle = self.ax_main.axhline(y=y, color='black', linewidth=1.0)
        label = self.pixel_to_wav(y)
        txt = f"{label:.1f} nm" if label else "N/A"
        if hasattr(self, 'label_handle'):
            self.label_handle.remove()
        self.label_handle = self.ax_main.text(0.95*self.ax_main.get_xlim()[1], y, txt,
                                              color='red', ha='right', va='center',
                                              bbox=dict(facecolor='white',alpha=0.7,pad=1))
        self.canvas_main.draw_idle()
        self.cid = [
            self.canvas_main.mpl_connect('button_press_event', self.on_main_press),
            self.canvas_main.mpl_connect('motion_notify_event', self.on_main_move),
            self.canvas_main.mpl_connect('button_release_event', self.on_main_release),
        ]

    def on_main_press(self,event):
        if self.line_handle and event.inaxes==self.ax_main:
            if abs(event.ydata-self.line_handle.get_ydata()[0])<10:
                self.line_drag=True

    def on_main_move(self,event):
        if self.line_drag and event.inaxes==self.ax_main:
            y = max(0, min(event.ydata, self.img_handle.get_array().shape[0]))
            self.line_handle.set_ydata([y,y]); wav = self.pixel_to_wav(y)
            txt = f"{wav:.1f} nm" if wav else "N/A"
            self.label_handle.set_position((0.95*self.ax_main.get_xlim()[1],y)); self.label_handle.set_text(txt)
            self.canvas_main.draw_idle()

    def on_main_release(self,event):
        self.line_drag=False; wav = self.pixel_to_wav(self.line_handle.get_ydata()[0]) if self.cal_model else None

    def remove_line(self):
        if self.line_handle: self.line_handle.remove(); self.line_handle=None
        if hasattr(self, 'label_handle'): self.label_handle.remove()
        for c in self.cid: self.canvas_main.mpl_disconnect(c)
        self.cid = []
        self.line_drag=False

    def on_exit(self):
        plt.close('all'); self.root.destroy()

if __name__=="__main__":
    app = SpectrometerApp(tk.Tk())
    tk.mainloop()
