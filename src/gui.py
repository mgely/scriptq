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
import settings

# Contains the graphics featured on the buttons
graphics_directory = path.join(path.dirname(__file__), "graphics")

'''
Hiearchy of Tkinter frames:
    GuiWindow.master = tk.Tk()
        GuiWindow(ttk.Frame)
            BatchingFrame.frame(ttk.Frame)
                BatchingFrame.vbar(ttk.Scrollbar)
                BatchingFrame(tk.Canvas)
                    BatchingFrame.canvas_content(tk.Frame)

Note: this is an amalgamation of code from different projects.
It could probably be simplified dramatically.
'''


class GuiWindow(ttk.Frame):
    '''
    Highest level window and frame. 
    Here we set the name and size of the window, 
    and prepare for hosting the actual content of the program.

    If unittest is set to True, we don't start the 
    mainloop, but wait for a script to trigger
    events and manually update the GUI.
    '''
    def __init__(self, unittesting = False):
        # Initialize the frame, inside the root window (tk.Tk())
        ttk.Frame.__init__(self, master=tk.Tk())

        # Set the name to appear in the title bar
        self.master.title("Script queuer")

        # Set the initial size of the window in pixels
        self.master.geometry("1000x400")

        # Only resizable in the y direction
        self.master.resizable(False, True)

        # Make the frame an expandable grid
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # Populate that grid with the batching frame
        self.bf = BatchingFrame(self.master)

        # Bring scriptq to the front
        self.master.lift()
        self.master.attributes("-topmost", True)
        self.master.attributes("-topmost", False)
        
        if unittesting:
            self.update()
        else:
            try:
                self.mainloop()
            except Error as e:
                messagebox.showinfo(
                    "Oops.. The script queuer crashed with error\n"+str(e)
                )


class BatchingFrame(tk.Canvas):
    '''
        This is the place where the widgets corresponding
        to scripts live. 

        It is also the brain of the program, and controls
        the state of the different scripts, the launching of 
        scripts, etc...
    '''

    def __init__(self,master,**kwargs):

        # Master is the highest level, 
        # root window here tk.Tk()
        self.master = master

        # When opening a script, this is
        # where the window will open to by default
        self.latest_searched_directory = None

        # currently or latest running ScriptWidget
        self.running_script = None

        # Build another frame, which will contain 
        # the canvas and the scrollbar
        self.build_gridframe()

        # We may want to have a menubar to add functionality
        # in the future, so I'm keeping this commented out.
        # self.build_menubar()

        # Add the vertical scrollbar
        self.build_scrollbars()

        # Add the canvas which will host the
        # Frame containing the script widgets
        # Note: a canvas is necessary here to make the 
        # whole GUI scrollable. 
        # (there's probably a simpler alternative though..)
        self.build_canvas()

        # configure vertical scrollbar
        self.configure_scrollbars()

        # build a window in the canvas which 
        # will contain the ScriptWidgets
        self.build_canvas_content()

        # if True, the output window is built and visible
        self.output_window_visible = False

        # Build the output window
        self.build_output_window()

        # This determines how oftem we collect and display 
        # the output of a running script
        self.t_output_monitoring = 100 #ms

        # Either 'stopped' or 'running'
        self.state = 'stopped' 

        # When we press stop, this message is appended
        # to the log of the script output
        self.interrupted_error_message = 'INTERRUPTED BY SCRIPT QUEUER'

        # Default opening screen
        # We start just with the insertion widget
        self.scripts = [
            InsertWidget(self),
            ]

        # Useful function which goes through the list 
        # self.scripts, and displays the corresponding graphical content
        self.update_script_widgets()


    def remove_all(self):
        '''
        Removes all the Scripts, from the last to the first, 
        excluding the topmost InsertWidget 
        '''
        for position in range(len(self.scripts)-1,0,-1):
            self.remove(position)

    def build_output_window(self):
        '''
        Shows the output window which contains the
        continuously updated output of the currently 
        running script (stdout and stderr).
        Or, if no script is running, contains
        the content of the latest run script.
        '''
        if self.output_window_visible:
            # the output is already visible
            # in this case bring the window to the top
            self.output_window.lift()
            self.output_window.attributes("-topmost", True)
            self.output_window.attributes("-topmost", False)
            return

        # Open up the output window
        self.output_window = tk.Toplevel(self.master)
        self.output_window.title("Script queuer | Output")   
        self.output_window.geometry("400x400")

        # Keep track of the window being visible
        self.output_window_visible = True

        # Window size cannot be reduced beyond
        # a certain size
        self.output_window.minsize(200,150)

        # When closing the window run self.on_closing_output_window
        self.output_window.protocol("WM_DELETE_WINDOW", self.on_closing_output_window)

        # Put a scrollable text region in it, and make is stretchable
        self.output_text_widget = ScrolledLabel(self.output_window)
        self.output_text_widget.grid(column = 0, row=0, sticky = 'news')
        self.output_window.rowconfigure(0, weight=1)
        self.output_window.columnconfigure(0, weight=1)

        # Add a button to toggle following the output / autoscrolling
        b = ToggleAutoscrollButton(self.output_window, 
          text='Autoscroll')
        b.grid(column = 0,row=1, sticky = 'nws')

        if self.running_script is not None:
            # Is there is no running script, 
            # show the log of the last run script
            self.output_text_widget.insert(self.running_script.log)
            self.scroll_output_window_down()


    def on_closing_output_window(self):
        '''
        Function called when the output window is closed
        '''

        # Keep track of the window state
        self.output_window_visible = False

        # Close the window
        self.output_window.destroy()

    def insert(self, position, script_path = None):
        '''
        Will insert a new script after the row indicated by 
        the input integer `position`. 
        Optionally one can specify the script path (for 
        unittesting purposes).
        '''

        if script_path is None:
            # If no script path was provided
            # prompt user for file name
            if self.latest_searched_directory == None:
                script_path = filedialog.askopenfilename()
            else:
                # If a script was already inserted,
                # open the file prompt at the same directory
                script_path = filedialog.askopenfilename(initialdir=self.latest_searched_directory)
            if script_path == "":
                # User cancelled
                return

            # keep track of the directory the user navigated to
            self.latest_searched_directory = path.dirname(script_path)

        # Creates a new script widget, by default it will be queued
        sw = ScriptWidget(self, script_path = script_path, state = 'queued')

        # add it to the list of scripts
        self.scripts.insert(position+1,sw)

        # update the scripts states and graphical information
        self.update_script_widgets()

    def move(self, position, new_position = None):
        '''
        Move a script from a position (row `position`) to a 
        new position (after row `new_position`).
        The new position will be chosen in a popup window
        by the user, or given as a kwarg (for unittesting purposes).
        '''


        if new_position is None:
            # No postion was given: prompt user
            # with a popup window

            # Determine message to be displayed in popup
            if self.state == 'running':
                # If running, do not allow script to be placed in first postion
                # (above the script which is running)
                message = " 1 = place below row 1\n etc...\n-1 = place at end"
                minvalue = 0
            else:
                # If stopped
                message = " 0 = place first \n 1 = place below row 1\n etc...\n-1 = place at end"
                minvalue = -1

            # Open popup window
            new_position = tk.simpledialog.askinteger("Move to", message,
                                    parent=self.master,
                                     minvalue=minvalue, maxvalue=len(self.scripts))

            if new_position is None:
                # User cancelled
                return

        if new_position == -1:
            # -1 is code for "at the end"
            new_position = len(self.scripts)
        else:
            # the position the user sees does not
            # take into account the rows of "done" scripts
            # position_0 is the position of the first "not done"
            # script.
            new_position += self.position_0

        # Insert the script at the new position
        self.scripts.insert(new_position,self.scripts[position])

        # Remove the script at the old position
        if new_position > position:
            self.scripts.pop(position)
        else:
            # If the script is moved up, then 
            # the old position is actually +1
            self.scripts.pop(position + 1)

        # Update script states and graphical information
        self.update_script_widgets()

    def remove(self, position):
        '''
        Remove a script from a position.
        '''

        # Destroy the ScriptWidget object
        self.scripts[position].destroy()

        # Remove it from the self.scripts list
        self.scripts.pop(position)

        # Update script states and graphical information
        self.update_script_widgets()

    def run(self, position):
        '''
        Run the script located at row `position`
        '''

        # Useful information about the script to be run
        self.running_script = self.scripts[position]
        script_path = self.scripts[position].script_path
        self.running_script_position = position
        self.running_script.log = ''

        # Delete the contents of the output window
        if self.output_window_visible:
            self.output_text_widget.clear()

        # Start the script and 
        # setup the communication
        # with subprocess
        self.start_script_process(script_path)

        # Start the periodic monitoring of the script, 
        # to capture the output, but also detect the end/error
        self.after(
                self.t_output_monitoring, 
                self.monitor_script_process)

        # Update the states of this object and the script
        self.state = 'running'
        self.running_script.state = 'running'

        # Update script states and graphical information
        self.update_script_widgets()

    def start_script_process(self, script):

        '''
        Start the script subprocess
         --- the -u option foces stdout, stderr streams to be 
        unbuffered, which allows us to collect these outputs in real tim, 
        rather than wait to the end of the scripts
         --- the cwd is chosen to be the folder in which 
         the script is located
        '''
        self.script_process = subprocess.Popen(
            ['python','-u',script], 
            cwd = path.dirname(script),
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE, 
            bufsize=1)

        '''
        This list will be populated
        with contents of the subprocess
        `stdout` by the `reader` function in a 
        seperate thread.
        It's the bridge between the subprocess
        and the log file and output window.
        '''
        self.line_buffer = []

        # in a seperate thread, collect the output
        # of the subprocess and load it into
        # line_buffer list
        self.buffer_filling_thread =Thread(target=reader,
            args=(
                    self.script_process.stdout,
                    self.line_buffer
                    ))
        self.buffer_filling_thread.daemon=True
        self.buffer_filling_thread.start()

    def write_to_output(self, to_write):
        '''
        write `to_write` both to the output window
        and to the log file of the running scripts
        '''
        if self.output_window_visible:
            self.output_text_widget.insert(to_write)
        self.running_script.log += to_write

    def scroll_output_window_down(self):
        if self.output_window_visible:
            self.output_text_widget.see("end")

    def monitor_script_process(self):
        '''
        Whilst the script is running, copy what the
        `reader` function has put into the `self.line_buffer`
        and write it to the output and log files.

        This function will detect when the running script crashed
        or ended, append the output/log accordingly, and 
        run the next queued script.
        '''

        # write all contents of the `self.line_buffer` list
        # to the output/log
        while self.line_buffer:
            self.write_to_output(self.line_buffer.pop(0).decode("utf-8"))

        # if autoscroll is activated, scroll the output window
        # to the latest written 
        if self.output_window.follow:
            self.scroll_output_window_down()

        # poll checks on the status of the subprocess
        poll =self.script_process.poll()

        if poll is None:  
            # Hasnt crashed or ended 
            # monitor again in a time `self.t_output_monitoring`
            self.after(
                self.t_output_monitoring, 
                self.monitor_script_process)

        else:
            self.treat_end_of_script(poll)
            self.treat_next_queued_script(poll)


    def treat_end_of_script(self, poll):
        '''
        Called whenever a script crashes or ends.
        Appends the output/log to give maximum 
        information to the user about causes of crashes.
        '''


        if poll != 0:
            # Something went wrong

            while True:
                # Get Error Log and write to output/log
                line = self.script_process.stderr.readline()
                if not line:
                    break
                else:
                    self.write_to_output(line.decode("utf-8"))

            # Scroll the output window to the bottom
            self.scroll_output_window_down()

            # If `self.state` is stopped, then it's the user
            # who interrupted the script, write this into the output\log
            if self.state == 'stopped':
                self.write_to_output(self.interrupted_error_message)

                # Scroll the output window to the bottom
                self.scroll_output_window_down()

    def treat_next_queued_script(self, poll):
        '''
        Called when a script crashes or ends, 
        to carry out the actions which follow:
         - starting a new queued script if the 
            script ended/crashed on its own
         - stopping the run if the user forced a stop
         - notifying the user via email if enabled
        '''

        if poll!=0 and self.state == 'stopped':
            # User interrupted the script

            # The script is stopped and made ready to go again
            self.running_script.state = 'ready'

            # It is also duplicated and marked above as a 
            # stopped script, so that the user may also inspect the 
            # logging file
            stopped = self.running_script
            duplicate = ScriptWidget(self, 
                script_path = stopped.script_path, 
                state = 'ended')
            duplicate.success = 'stopped'
            duplicate.log = stopped.log
            self.scripts.insert(self.running_script_position, duplicate)

            # Update script states and graphical information
            self.update_script_widgets()

        else:
            if poll!=0:
                # Script stopped because of an error
                self.running_script.state = 'ended'
                self.running_script.success = 'failed'
            
            elif poll==0:
                # Script successfully ended
                self.running_script.state = 'ended'
                self.running_script.success = 'done'
            
            if settings.gmail_notifications['enable']:
                self.gmail_notify()
            

            if self.running_script_position+1<len(self.scripts):
                # more scripts are queued: run the next one
                self.run(position = self.running_script_position+1)

            else:
                # no more scripts to be run: just update visual information
                self.state = 'stopped'
                self.update_script_widgets()

    def gmail_notify(self):
        try:
            import smtplib 

            message = 'Subject: [scriptq] script %s\n\n'%self.running_script.success
            message += "Path -- %s\n"%self.running_script.script_path
            message += "Status -- %s\n"%self.running_script.success
            message += "Log -- \n%s"%self.running_script.log
            
            # creates SMTP session 
            s = smtplib.SMTP('smtp.gmail.com', 587) 
            
            # start TLS for security 
            s.starttls() 
            
            # Authentication 
            s.login(
                settings.gmail_notifications['sender_email'], 
                settings.gmail_notifications['sender_password']) 
            
            # sending the mail 
            s.sendmail(
                settings.gmail_notifications['sender_email'], 
                settings.gmail_notifications['receiver_emails'], 
                message) 
            
            # terminating the session 
            s.quit() 
        
        except Error as e:
            messagebox.showinfo(
                "Sending notification email failed with error:\n"+str(e)
            )




    def stop(self):
        '''
        Triggered by a user clicking the stop button
        all one needs to do is set the state to `stopped`
        and force the script to stop, the automatic
        monitoring of the running script in `monitor_script_process`
        will take care of the following actions
        '''
        self.state = 'stopped'

        # Interrupt process
        self.script_process.kill()

    def update_script_widgets(self):
        '''
        Updates the states of the ScriptWidget objects
        and updates the graphical information displayed.

        All is determined by the `self.states` list
        and the `self.state` variable.
        '''

        # The self.scripts list should never be empty
        # as a failsafe we always populate it in that case
        # with the insert widget
        if len(self.scripts) == 0:
            self.scripts = [InsertWidget(self)]
            return

        # The row is a property of the non-done scripts
        # it is displayed in the GUI starting from 1
        row = 1

        for i,s in enumerate(self.scripts):

            # All scripts are given a position, running from 0 upwards
            # this is not necessarily the same as the row and acts 
            # as a unique identifier of the script
            s.position = i

            # Scripts which are done are given no row information
            s.row = None

            if s.state in ['running', 'ready', 'queued'] or row>1:
                
                if row==1:
                    # First script running/to-run

                    # Helps in converting rows given by the user
                    # to the position identifier of a script
                    self.position_0 = i

                    # Since this is the first script which has not already been run
                    # it should be either running or stopped
                    if self.state == 'running':
                        s.state = 'running'
                    elif self.state == 'stopped':
                        s.state = 'ready'

                elif row>1:
                    # this script is lower down the queue:
                    # if they were just moved for example, we should
                    # adjust their state accordingly
                    s.state = 'queued'

                # These non-done scripts are given a row
                s.row = row
                row+=1


        for i,s in enumerate(self.scripts):
            # Place the script in the grid
            s.grid(row=i, column=0, sticky='news')
            # Populate it with buttons etc...
            s.add_widgets()

        # Adjust the scrollable region of the GUI
        self.update()
        self.config(scrollregion=self.bbox("all"))

    def build_gridframe(self):
        """
        This frame will be divided into a grid hosting the
        canvas, scrollbars, (and potentially a menubar in the future if needed)
        """

        self.frame = ttk.Frame()

        # Places the Frame widget self.frame in the parent
        # in a grid
        self.frame.grid()

        # Configure the frames grid
        self.frame.grid(sticky="nswe")  # make frame container sticky
        self.frame.rowconfigure(0, weight=1)  # make canvas expandable in x
        self.frame.columnconfigure(0, weight=1)  # make canvas expandable in y

    def build_menubar(self):
        """
        Builds the File, Edit, ... menu bar situated at the top of
        the window.

        Not used for the moment...
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
        Builds a vertical scrollbars and places
        it in the window
        """
        self.vbar = ttk.Scrollbar(
            self.frame, orient="vertical")

        self.vbar.grid(row=0, column=1, sticky="ns")

    def build_canvas(self):
        """
        Initializes the canvas from which this object inherits and
        places it in the grid of our frame
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
        when we interact with them, and make scrolling
        on the mouse do something similar
        """
        self.vbar.configure(command=self.scroll_y)
        self.bind("<MouseWheel>", self.scroll_y_wheel)

    def scroll_y(self, *args, **kwargs):
        """
        Is called when the user interacts with the vertical scroll bar
        """

        # stop from scolling up beyond a certain point
        if float(args[1])<0:
            args = (args[0], "0")

        # shift canvas vertically
        self.yview(*args)
        time.sleep(0.01)

        # Update scrollable area
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

        # Move the canvas appropriately, and stop 
        # the user from scrolling to far out
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

        # Update the scrollable region
        self.update()
        self.config(scrollregion=self.bbox("all"))

    def build_canvas_content(self):
        '''
        Build a window which will contain the widgets
        '''
        self.canvas_content = tk.Frame(self)
        self.create_window((0, 0), 
            window=self.canvas_content, 
            anchor='nw', 
            width = 1000)
        self.canvas_content.columnconfigure(0, weight=1)

class ScriptWidget(tk.Frame):
    '''
    Widget (tkinter frame) in which are stored all the graphical 
    elements and information about a script.
    '''

    def __init__(self, parent, 
            script_path = None, state = None, success = ''):

        super(ScriptWidget, self).__init__(parent.canvas_content)

        # A reference to the canvas in which 
        # the widget is placed
        self.parent = parent

        '''
        string representing the state
        of the script, can be one of:
         - ended
         - ready (waiting for user to click run)
         - running 
         - queued 
        '''
        self.state = state

        '''
        Is not None only if the script is ended.
        Can then be one of:
         - done (ran successfully)
         - failed (there was an error in the script)
         - stopped (the user interrupted the script)
        '''
        self.success = success

        # Full, absolute path to the script
        self.script_path = script_path

        # Row of the script displayed in the GUI
        # None if the script has ended, 
        # 1 and above if not
        self.row = None 

        # Position of the script regardless of the state
        # Goes from 0 up
        self.position = None

        # Vertical padding of the graphical elements
        self.pady = (1,1)

        # Stores all the widgets displayed
        self.all_widgets = []

    def next_script_state(self):
        '''
        Returns the state of the script below the current
        one. Returns None is this is the last script.
        '''
        try:
            return self.parent.scripts[self.position+1].state
        except IndexError:
            # This script is last in line
            return None

    def add_widgets(self):
        '''
        Builds all graphical elements
        depending on the state and information
        about the script.
        '''

        # remove all previously bult graphical elements
        for w in self.all_widgets:
            w.destroy()
        self.all_widgets = []


        ##################
        # INSERT BUTTON
        ##################
        if self.next_script_state() in ['ready', 'queued',None]:
            b = ImageButton(self,image = 'insert.gif', 
                command = (lambda: self.parent.insert(self.position)))
        else:
            b = ImageButton(self,image = 'half_blank.gif')
            b.config(state=tk.DISABLED)
        b.grid(row=0, column=0, sticky='swe', padx = (5,0))
        self.all_widgets.append(b)


        ##################
        # ROW LABEL
        ##################
        if self.state == 'ended':
            l = ImageLabel(self,image = 'blank.gif', compound = tk.CENTER)
        else:
            l = ImageLabel(self,image = 'blank.gif', compound = tk.CENTER, text = self.row)
        l.grid(row=0, column=1,sticky='new')
        self.all_widgets.append(l)


        ##################
        # STATE LABEL
        ##################
        if self.state == 'ended':
            text = self.success
        else:
            text = self.state
        b = ImageLabel(self,text = text, 
            image = 'label_'+self.state+self.success+".gif",
            compound = tk.CENTER)
        b.grid(row=0, column=2, sticky='new')
        self.all_widgets.append(b)


        ##################
        # REMOVE BUTTON
        ##################
        if self.state == 'running':
            b = ImageButton(self,image = 'blank.gif')
            b.config(state=tk.DISABLED)
        else:
            b = ImageButton(self,image = 'remove.gif', 
                command = (lambda: self.parent.remove(self.position)))
        b.grid(row=0, column=3, sticky='new', pady=self.pady)
        self.all_widgets.append(b)


        ##################
        # MOVE BUTTON
        ##################
        if self.state in ['queued','ready'] :
            b = ImageButton(self,image = 'move.gif', 
                command = (lambda: self.parent.move(self.position)))
        else:
            b = ImageButton(self,image = 'blank.gif')
            b.config(state=tk.DISABLED)
        b.grid(row=0, column=4, sticky='new', pady=self.pady)
        self.all_widgets.append(b)


        ##################
        # RUN/STOP BUTTON
        ##################
        if self.state == 'running':
            b = ImageButton(self,image = 'stop.gif', 
            command = self.parent.stop)
        elif self.state == 'ready':
            b = ImageButton(self,image = 'run.gif',
                command = (lambda: self.parent.run(self.position)))
        else:
            b = ImageButton(self,image = 'blank.gif')
            b.config(state=tk.DISABLED)
        b.grid(row=0, column=5, sticky='new', pady=self.pady)
        self.all_widgets.append(b)
        
        ##################
        # LOG/OUTPUT BUTTON
        ##################
        if self.state == 'ended':
            b = ImageButton(self,
                text = "view log", 
                command = self.view_log,
                image = 'blank.gif',
                compound = tk.CENTER)
        elif self.state in ['running','ready']:
            b = ImageButton(self,
                text = "view output", 
                command = self.parent.build_output_window,
                image = 'blank.gif',
                compound = tk.CENTER)
        else:
            b = ImageButton(self,
                text = "", 
                command = self.parent.build_output_window,
                image = 'blank.gif',
                compound = tk.CENTER)
            b.config(state=tk.DISABLED)
        self.all_widgets.append(b)
        b.grid(row=0, column=6, sticky='ne', pady=self.pady, padx=(2,10))
        
        ##################
        # SCRIPT PATH LABEL
        ##################
        b = tk.Label(self,text = self.script_path,
            anchor = tk.W,
            )
        b.grid(row=0, column=7,columnspan=1, sticky='new', pady=self.pady, padx = (0,40))
        self.columnconfigure(7, weight=1)
        self.all_widgets.append(b)
        self.update()
        # Wrap the path text
        b.config(wraplength = b.winfo_width()-50)

    def view_log(self):

        # Open up the output window
        self.log_window = tk.Toplevel(self.parent.master)
        self.log_window.title("Script queuer | Log | "+self.script_path) 

        # Opening size of the window  
        self.log_window.geometry("400x400")

        # Minimum size of the window
        self.log_window.minsize(200,150)

        # Put a scrollable text region in it
        self.log_text_widget = ScrolledLabel(self.log_window)
        self.log_text_widget.grid(column = 0, row=0, sticky = 'news')

        # Add the log text 
        self.log_text_widget.insert(self.log)

        # Scroll all the way down to the end
        self.log_text_widget.see("end")

        # Make the scrollable text stretch with the window
        self.log_window.rowconfigure(0, weight=1)
        self.log_window.columnconfigure(0, weight=1)


class InsertWidget(ScriptWidget):
    '''Like Script Widget, but with just an insert button.
    '''
    def __init__(self, parent):
        super(InsertWidget, self).__init__(parent, script_path = None, state = None, success = None)

    def add_widgets(self):
        '''
        Add the graphical elements of the widget
        '''
        if self.next_script_state() in ['ready','queued', None]:
            b = ImageButton(self,image = 'insert.gif', 
                command = (lambda: self.parent.insert(self.position)))
        else:
            b = ImageButton(self,image = 'half_blank.gif')
            b.config(state=tk.DISABLED)
        b.grid(row=0, column=0, sticky='swe', padx = (5,0))




class ImageButton(ttk.Button):
    '''Wrapper around the ttk.Button class
    which automizes the importation of the 
    buttons picture.
    '''
    def __init__(self, *args, image=None, **kwargs):

        # Import image
        image = PhotoImage(file=path.join(graphics_directory,image))

        # Make two times smaller
        image = image.subsample(2, 2)

        super(ImageButton, self).__init__(*args, image=image, **kwargs)

        # This is necessary otherwise the picture dosnt appear somehow
        self.image = image


class ImageLabel(ttk.Label):
    """docstring for ImageButton"""
    def __init__(self, *args, image=None, **kwargs):

        # Import image
        image = PhotoImage(file=path.join(graphics_directory,image))
        
        # Make two times smaller
        image = image.subsample(2, 2)
        
        super(ImageLabel, self).__init__(*args, image=image, **kwargs)
        
        # This is necessary otherwise the picture dosnt appear somehow
        self.image = image

class ToggleAutoscrollButton(tk.Radiobutton):
    """Button which turns auto scrolling on and off.
    """
    def __init__(self, parent, text):
        self.parent = parent

        # The button is checked when this variable is set to True
        self.state = tk.BooleanVar()
        self.state.set(True)

        # The auto-scrolling is activated in the parent widget
        # when this variable is set to True
        self.parent.follow = True

        super(ToggleAutoscrollButton, self).__init__(parent, 
            text = text, variable = self.state, value = True, command = self.click)

    def click(self):
        '''
        Called upon clicking the button
        '''

        if self.state.get():
            # If autoscrolling is on
            self.config(value = False)
            self.parent.follow = False

        else:
            # If autoscrolling is off
            self.config(value = True)   
            self.state.set(True)    
            self.parent.follow = True

class ScrolledLabel(scrolledtext.ScrolledText):
    """wrapper around scrolledtext, to make
    the text read-only
    """

    def __init__(self, *args, **kwargs):
        super(ScrolledLabel, self).__init__(*args, **kwargs)
        self.configure(state='disabled')

    def insert(self, text):
        self.configure(state='normal')
        super(ScrolledLabel, self).insert(tk.INSERT, text)
        self.configure(state='disabled')

    def clear(self):
        self.configure(state='normal')
        self.delete("1.0","end")
        self.configure(state='disabled')

def reader(f,buffer):
    '''Utility function runing in a thread
    which transfers any lines from the 
    pipe `f` into the list `buffer`
    '''
    while True:
        line=f.readline()
        if line:
            buffer.append(line)
        else:
            break

if __name__ == '__main__':
    GuiWindow()