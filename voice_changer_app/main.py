import tkinter as tk
from ui.app_window import AppWindow

def main():
    root = tk.Tk()
    app = AppWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
