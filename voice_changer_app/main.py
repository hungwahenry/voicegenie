import customtkinter as ctk
from ui.app_window import AppWindow

def main():
    root = ctk.CTk()
    app = AppWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
