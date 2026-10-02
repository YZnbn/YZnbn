@echo off
cd /d "%~dp0"
echo Testing Tkinter window...
python -c "import tkinter as tk; root=tk.Tk(); root.title('test'); root.geometry('300x200'); tk.Label(root,text='If you see this, Tkinter works').pack(); root.mainloop()" > tk_test.log 2>&1
echo Exit: %errorlevel%
type tk_test.log
pause
