import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, scrolledtext
from tkinter import PhotoImage
from tkinter import ttk
import subprocess
from threading import Thread 
import time
import tempfile
from os import path
import sys

class GuiWindow(ttk.Frame):
    def __init__(self):
        # Initialize the frame, inside the root window (tk.Tk())
        ttk.Frame.__init__(self, master=tk.Tk())

        # Set the name to appear in the title bar
        self.master.title("Script queuer")

        # Set the initial size of the window in pixels
        self.master.geometry("800x400")

        self.master.resizable(False, True)

        # Load the logo to the title bar
        # if _os_type == "windows":
        #     try:
        #         self.master.iconbitmap(
        #             os.path.join(
        #                 os.path.dirname(os.path.dirname(__file__)),
        #                 "artwork",
        #                 "logo.ico",
        #             )
        #         )
        #     except Exception as e:
        #         if _verbose:
        #             print(
        #                 "There has been an error loading the applications icon:\n"
        #                 + str(e)
        #             )

        # Make the frame an expandable grid
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # Populate that grid with the batching frame
        self.bf = BatchingFrame(self.master)

        # Bring the window to the front
        self.master.lift()
        self.master.attributes("-topmost", True)
        self.master.attributes("-topmost", False)
        
        try:
            self.mainloop()
        except UnicodeDecodeError:
            messagebox.showinfo(
                "Oops.. The GUI crashed.\n\n"
            )



class BatchingFrame(tk.Canvas):
    def __init__(self,master,**kwargs):
        self.master = master
        self.latest_searched_directory = None
        self.running_script = None

        self.build_gridframe()
        self.build_menubar()
        self.build_scrollbars()
        self.build_canvas()
        self.configure_scrollbars()

        self.output_window_visible = False
        self.build_output_window()

        self.t_output_monitoring = 100 #ms
        self.bind("<MouseWheel>", self.scroll_y_wheel)

        self.canvas_content = tk.Frame(self)
        self.create_window((0, 0), 
            window=self.canvas_content, 
            anchor='nw', 
            width = 800)
        self.master.columnconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas_content.columnconfigure(0, weight=1)

        self.state = 'stopped' # other option: 'running'

        # # Default opening screen
        # self.scripts = []

        # Custom opening screen for debugging
        self.scripts = [
            ScriptWidget(self, script_path = '-2', state = 'ended', success = 'failed'),
            ScriptWidget(self, script_path = '-1', state = 'ended', success = 'done'),
            ScriptWidget(self, script_path = '1', state = 'queued'),
            ScriptWidget(self, script_path = '2', state = 'queued')
            ]

        self.update_script_widgets()



        self.update()
        self.config(scrollregion=self.bbox("all"))


    
    def build_output_window(self):
        if self.output_window_visible:
            # Has already been built
            self.output_window.lift()
            self.output_window.attributes("-topmost", True)
            self.output_window.attributes("-topmost", False)
            return

        self.output_window_visible = True

        # Open up the output window
        self.output_window = tk.Toplevel(self.master)
        self.output_window.title("Script queuer | Output")   
        self.output_window.geometry("400x400")
        self.output_window.minsize(200,150)
        self.output_window.protocol("WM_DELETE_WINDOW", self.on_closing_output_window)

        # Put a scrollable text region in it
        self.output_text_widget = ScrolledLabel(self.output_window)
        self.output_text_widget.grid(column = 0, row=0, sticky = 'news')
        self.output_window.rowconfigure(0, weight=1)
        self.output_window.columnconfigure(0, weight=1)

        # Add a button to toggle following the output
        b = ToggleFollowButton(self.output_window, 
          text='Autoscroll')
        b.grid(column = 0,row=1, sticky = 'nws')

        if self.running_script is not None:
            self.output_text_widget.insert(self.running_script.log)
            self.output_text_widget.see("end")

    def on_closing_output_window(self):
        self.output_window_visible = False
        self.output_window.destroy()

    def insert(self, position):

        # Prompt user for file name
        if self.latest_searched_directory == None:
            script_path = filedialog.askopenfilename()
        else:
            script_path = filedialog.askopenfilename(initialdir=self.latest_searched_directory)

        

        if script_path == "":
            # User cancelled
            return

        self.latest_searched_directory = path.dirname(script_path)

        sw = ScriptWidget(self, script_path = script_path, state = 'queued')

        self.scripts.insert(position+1,sw)
        self.update_script_widgets()

    def move(self, position):
        if self.state == 'running':
            message = " 1 = place below row 1\n etc...\n-1 = place at end"
            minvalue = 0
        else:
            message = " 0 = place first \n 1 = place below row 1\n etc...\n-1 = place at end"
            minvalue = -1

        new_position = tk.simpledialog.askinteger("Move to", message,
                                parent=self.master,
                                 minvalue=minvalue, maxvalue=len(self.scripts))
        if new_position is None:
            # User cancelled
            return
        elif new_position == -1:
            new_position = len(self.scripts)
        else:
            new_position += self.position_0

        self.scripts.insert(new_position,self.scripts[position])
        if new_position > position:
            self.scripts.pop(position)
        else:
            self.scripts.pop(position + 1)

        self.update_script_widgets()

    def remove(self, position):

        self.scripts[position].destroy()
        self.scripts.pop(position)
        self.update_script_widgets()

    def run(self, position):

        self.running_script = self.scripts[position]
        self.running_script_position = position

        # Start the script and setup the communication
        # with subprocess
        self.start_script_process(self.scripts[position].script_path)

        # Delete the contents of the output window
        if self.output_window_visible:
            self.output_text_widget.delete("1.0","end")

        # Start the periodic monitoring of the script, 
        # to capture the output, but also detect the end/error
        self.after(
                self.t_output_monitoring, 
                self.manage_script_process)

        self.state = 'running'
        self.scripts[position].run()
        self.update_script_widgets()

    def start_script_process(self, script):

        # Start the script subprocess
        self.script_process = subprocess.Popen(['python','-u','test.py'],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE, 
            bufsize=1)
        self.line_buffer = []
        '''
        Populated with contents of process
        stdout by the reader function in a 
        seperate thread.
        '''
        self.buffer_filling_thread =Thread(target=reader,
            args=(
                    self.script_process.stdout,
                    self.line_buffer
                    ))
        self.buffer_filling_thread.daemon=True
        self.buffer_filling_thread.start()

    def write_to_output(self, to_write):
        if self.output_window_visible:
            self.output_text_widget.insert(to_write)
        self.running_script.log += to_write

    def manage_script_process(self):

        while self.line_buffer:
            self.write_to_output(self.line_buffer.pop(0).decode("utf-8"))

        if self.output_window.follow and self.output_window_visible:
            self.output_text_widget.see("end")

        poll =self.script_process.poll()
        if poll in [0,1]:
            if poll == 0:
                pass
                # Successfully finished script
            elif poll == 1:
                # Something went wrong

                # Get Error Log
                while True:
                    line = self.script_process.stderr.readline()
                    if not line:
                        break
                    else:
                        self.write_to_output(line.decode("utf-8"))
                if self.output_window_visible:
                    self.output_text_widget.see("end")

                if self.state == 'stopped':
                    self.write_to_output('INTERRUPTED BY SCRIPT QUEUER')
                    if self.output_window_visible:
                        self.output_text_widget.see("end")


            if poll==1 and self.state == 'stopped':
                # User interrupted the script

                self.running_script.stop()

                stopped = self.running_script
                duplicate = ScriptWidget(self, 
                    script_path = stopped.script_path, 
                    state = 'ended')
                duplicate.success = 'stopped'
                duplicate.log = stopped.log

                self.scripts.insert(self.running_script_position, duplicate)
                self.update_script_widgets()

            else:
                if poll==1:
                    # Script stopped because of an error
                    self.running_script.end(success = 'failed')
                elif poll==0:
                    # Script successfully ended
                    self.running_script.end(success = 'done')
                

                if self.running_script_position+1<len(self.scripts):
                    # more scripts are queued
                    self.run(position = self.running_script_position+1)
                else:
                    # no more scripts to be run, update visual information
                    self.update_script_widgets()

        else:   
            self.after(
                self.t_output_monitoring, 
                self.manage_script_process)



    def stop(self, position):
        self.state = 'stopped'

        # Interrupt process
        self.script_process.kill()

    def update_script_widgets(self):
        if len(self.scripts) == 0:
            self.scripts = [ScriptWidget(self)]

        id = 1
        for i,s in enumerate(self.scripts):
            s.position = i
            if s.state != 'ended' and s.state != None:
                # We passed all the ended scripts
                if id==1:
                    self.position_0 = i
                    # topmost non-run scipt
                    # if was just move there, we should
                    # adjust its state
                    if self.state == 'running':
                        s.run()
                    elif self.state == 'stopped':
                        s.stop()

                    # give zero and negative ids to all the ended scripts
                    neg_id = 0
                    for position in range(i-1,-1,-1):
                        self.scripts[position].id = neg_id
                        neg_id -= 1

                elif id>1:
                    # scripts lower down the queue:
                    # if they were just moved, we should
                    # adjust their state
                    s.queue()

                s.id = id
                id+=1


        for i,s in enumerate(self.scripts):
            s.grid(row=i, column=0, sticky='news')
            s.add_widgets()

    def build_gridframe(self):
        """
        Builds the main area of the window (called a frame),
        which should stick to the edges of the window and
        expand as a user expands the window.

        This frame will be divided into a grid hosting the
        canvas, menubar, scrollbars
        """

        # Builds a new frame, which will be divided into a grid
        # hosting the canvas, menubar, scrollbars
        self.frame = ttk.Frame()

        # Places the Frame widget self.frame in the parent
        # widget (MainWindow) in a grid
        self.frame.grid()

        # Configure the frames grid
        self.frame.grid(sticky="nswe")  # make frame container sticky
        self.frame.rowconfigure(0, weight=1)  # make canvas expandable in x
        self.frame.columnconfigure(0, weight=1)  # make canvas expandable in y

    def build_menubar(self):
        """
        Builds the File, Edit, ... menu bar situated at the top of
        the window.
        """

        # initialize the menubar object
        self.menubar = tk.Menu(self.frame)

        ####################################
        # FILE cascade menu build
        ####################################

        # add new item to the menubar
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=menu)

        ####################################
        # VIEW cascade menu build
        ####################################

        # add new item to the menubar
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=menu)

        # add cascade menu items
        menu.add_command(
            label="Output",
            command=self.build_output_window)


        # Add the menubar to the application
        self.master.config(menu=self.menubar)

    def build_scrollbars(self):
        """
        Builds horizontal and vertical scrollbars and places
        them in the window
        """
        self.vbar = ttk.Scrollbar(
            self.frame, orient="vertical")
        self.vbar.grid(row=0, column=1, sticky="ns")

    def build_canvas(self):
        """
        Initializes the canvas from which this object inherits and
        places it in the grid of our window

        Actually in the previously called build_* functions, we have
        defined frames, menubars, etc.. which are seperate from the canvas.
        It is however convinient to do so since most of these definied buttons
        or scrollbars will be acting on the canvas itself.
        """
        tk.Canvas.__init__(
            self,
            self.frame,
            bd=0,
            highlightthickness=0,
            yscrollcommand=self.vbar.set,
            confine=False,
            bg="white",
        )

        self.grid(row=0, column=0, sticky="nswe")

    def configure_scrollbars(self):
        """
        Define what functions the scrollbars should call
        when we interact with them.
        """
        self.vbar.configure(command=self.scroll_y)

    def scroll_y(self, *args, **kwargs):
        """
        Is called when the user interacts with the vertical scroll bar
        """
        # shift canvas vertically

        # stop from scolling up
        if float(args[1])<0:
            args = (args[0], "0")
        self.yview(*args)
        time.sleep(0.01)
        self.update()
        self.config(scrollregion=self.bbox("all"))

    def scroll_y_wheel(self, event):
        """
        Triggered by the user scrolling (in combination with no particular key presses).
        """

        # Determine which direction the user is scrolling
        # if using windows, then event.delta has also a different
        # amplitude depending on how fast the user is scrolling,
        # but we ignore that
        if event.num == 5 or event.delta < 0:
            direction = 1
        if event.num == 4 or event.delta > 0:
            direction = -1

        # Move the canvas appropriately
        if direction == 1:
            if self.canvasy(self.winfo_height()) < 2*self.bbox("all")[3]:
                self.yview_scroll(direction, tk.UNITS)
        elif direction == -1:
            if self.canvasy(0) > self.bbox("all")[1]:
                self.yview_scroll(direction, tk.UNITS)
                self.update()
            # if we scroll above the top row, move a little down..
            if self.canvasy(0) < self.bbox("all")[1]:
                self.yview_moveto(0)

        self.update()
        self.config(scrollregion=self.bbox("all"))

class ScriptWidget(ttk.Frame):
    def __init__(self, parent, script_path = None, state = None, success = None):
        super(ScriptWidget, self).__init__(parent.canvas_content)
        self.parent = parent
        self.state = state
        self.script_path = script_path
        self.id = None 
        self.position = None
        self.success = success

        self.pady = (1,1)#(5,20)
        self.width_number_text = 2
        self.width_state_text = 10


    def add_widgets(self):


        if self.state == None:
            b = ImageButton(self,image = 'insert.gif', command = self.insert)
            b.grid(row=0, column=0, sticky='swe', padx = (5,0))
            self.columnconfigure(7, weight=1)
            return

        if self.state == 'ended':
            l = ttk.Label(self,text = '', width= self.width_number_text)
        else:
            l = ttk.Label(self,text = self.id, width= self.width_number_text, anchor="center")
        l.grid(row=0, column=1,sticky='news')

        if self.state == 'ended':
            b = ttk.Label(self,text = self.success, width= self.width_state_text, anchor="center")
        elif self.state == 'stopped':
            b = ttk.Label(self,text = 'ready', width= self.width_state_text, anchor="center", background="green")
        else:
            b = ttk.Label(self,text = self.state, width= self.width_state_text, anchor="center")
        b.grid(row=0, column=5, sticky='news')

        try:
            next_script_state = self.parent.scripts[self.position+1].state
        except IndexError:
            # This script is last in line
            next_script_state = None

        if (self.state == 'ended' and next_script_state == 'ended' and self.parent.state == 'stopped')\
                 or (self.state == 'ended' and self.parent.state == 'running'):
            b = ImageButton(self,image = 'half_blank.gif')
            b.config(state=tk.DISABLED)
        else:
            b = ImageButton(self,image = 'insert.gif', 
                command = (lambda: self.parent.insert(self.position)))
        b.grid(row=0, column=0, sticky='swe', padx = (5,0))

        if self.state == 'running':
            b = ImageButton(self,image = 'blank.gif')
            b.config(state=tk.DISABLED)
        else:
            b = ImageButton(self,image = 'remove.gif', 
                command = (lambda: self.parent.remove(self.position)))
        b.grid(row=0, column=2, sticky='news', pady=self.pady)

        if self.state in ['queued','stopped'] :
            b = ImageButton(self,image = 'move.gif', 
                command = (lambda: self.parent.move(self.position)))
        else:
            b = ImageButton(self,image = 'blank.gif')
            b.config(state=tk.DISABLED)
        b.grid(row=0, column=3, sticky='news', pady=self.pady)

        if self.state == 'running':
            b = ImageButton(self,image = 'stop.gif', 
            command = (lambda: self.parent.stop(self.position)))
        elif self.state == 'stopped':
            b = ImageButton(self,image = 'run.gif',
                command = (lambda: self.parent.run(self.position)))
        else:
            b = ImageButton(self,image = 'blank.gif')
            b.config(state=tk.DISABLED)
        b.grid(row=0, column=4, sticky='news', pady=self.pady)
        
        if self.state == 'ended':

            b = ttk.Button(self,text = "view log", command = self.view_log)
            b.grid(row=0, column=6, sticky='nes', pady=self.pady)
            
            b = ttk.Button(self,text = self.script_path,compound = 'left')
            b.grid(row=0, column=7, sticky='news', pady=self.pady, padx = (0,40))
        else:
            b = ttk.Button(self,text = self.script_path)
            b.grid(row=0, column=6,columnspan=2, sticky='news', pady=self.pady, padx = (0,40))
        
        self.columnconfigure(7, weight=1)

    def view_log(self):

        # Open up the output window
        self.log_window = tk.Toplevel(self.parent.master)
        self.log_window.title("Script queuer | Log | "+self.script_path)   
        self.log_window.geometry("400x400")
        self.log_window.minsize(200,150)

        # Put a scrollable text region in it
        self.log_text_widget = ScrolledLabel(self.log_window)
        self.log_text_widget.grid(column = 0, row=0, sticky = 'news')
        self.log_text_widget.insert(self.log)
        self.log_window.rowconfigure(0, weight=1)
        self.log_window.columnconfigure(0, weight=1)

    def queue(self):
        self.state = 'queued'
        self.add_widgets()

    def end(self, success):

        self.success = success
        self.state = 'ended'
        self.add_widgets()

    def run(self):

        self.state = 'running'
        self.log = ''
        self.add_widgets()

    def stop(self):
        self.state = 'stopped'
        self.add_widgets()



class ImageButton(ttk.Button):
    """docstring for ImageButton"""
    def __init__(self, *args, image=None, **kwargs):
        image = PhotoImage(file=image)
        image = image.subsample(2, 2)
        super(ImageButton, self).__init__(*args, image=image, **kwargs)
        self.image = image

class ToggleFollowButton(tk.Radiobutton):
    """docstring for ToggleFollowButton"""
    def __init__(self, parent, text):
        self.state = tk.BooleanVar()
        self.parent = parent
        self.parent.follow = True
        self.state.set(True)
        super(ToggleFollowButton, self).__init__(parent, text = text, variable = self.state, value = True, command = self.click)

    def click(self):
        if self.state.get():
            self.config(value = False)
            self.parent.follow = False
        else:
            # TODO: add l.see("end")
            self.config(value = True)   
            self.state.set(True)    
            self.parent.follow = True

class ScrolledLabel(scrolledtext.ScrolledText):
    """docstring for ScrolledLabel"""
    def __init__(self, *args, **kwargs):
        super(ScrolledLabel, self).__init__(*args, **kwargs)

    def insert(self, text):
        self.configure(state='normal')
        super(ScrolledLabel, self).insert(tk.INSERT, text)
        self.configure(state='disabled')

def reader(f,buffer):
    '''Utility function runing in a thread
    which transfers any lines from f into a buffer
    '''
    while True:
        line=f.readline()
        if line:
            buffer.append(line)
        else:
            break

GuiWindow()