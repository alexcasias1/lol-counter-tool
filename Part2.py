import tkinter as tk

window = tk.Tk()
window.title("OP.GG meta analysis")
window.configure(bg = "green")

label_tp = tk.Label(window, text = "League of Legends Meta Counters", height = 7, width = 50)

label_tp.pack()
window.geometry("900x900")

#label_tp = tk.Label(window, text="Top Lane")
#label_tp.pack()

#label_jg = tk.Label(window, text="Jungle")
#label_jg.pack()

#label_md = tk.Label(window, text="Mid")
#label_md.pack()

#label_bt = tk.Label(window, text="Bot Lane")
#label_bt.pack()

#label_sp = tk.Label(window, text="Support")
#label_sp.pack()

button_tp = tk.Button(window, text="Top Lane", height = 2, width = 20, command=lambda: print("Button clicked!"))
button_tp.config(bg = "yellow")
button_tp.pack()

button_jg = tk.Button(window, text="Jungle", height = 2, width = 20, command=lambda: print("Button clicked!"))
button_jg.config(bg = "yellow")
button_jg.pack()

button_md = tk.Button(window, text="Mid", height = 2, width = 20, command=lambda: print("Button clicked!"))
button_md.config(bg = "yellow")
button_md.pack()

button_bt = tk.Button(window, text="Bot Lane", height = 2, width = 20, command=lambda: print("Button clicked!"))
button_bt.config(bg = "yellow")
button_bt.pack()

button_sp = tk.Button(window, text="Support", height = 2, width = 20, command=lambda: print("Button clicked!"))
button_sp.config(bg = "yellow")
button_sp.pack()

print(window.mainloop())