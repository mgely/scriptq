import tkinter as tk
from tkinter import PhotoImage
from tkinter import ttk
import time


class GuiWindow(ttk.Frame):
    def __init__(self):
        # Initialize the frame, inside the root window (tk.Tk())
        ttk.Frame.__init__(self, master=tk.Tk())

        # Set the name to appear in the title bar
        self.master.title("Script queuer")

        # Set the initial size of the window in pixels
        self.master.geometry("800x600")

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

        self.build_gridframe()
        self.build_menubar()
        self.build_scrollbars()
        self.build_canvas()
        self.configure_scrollbars()

        self.bind("<MouseWheel>", self.scroll_y_wheel)

        canvas_content = tk.Frame(self, bg="blue")
        self.create_window((0, 0), 
            window=canvas_content, 
            anchor='nw', 
            width = 800)
        self.master.columnconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        canvas_content.columnconfigure(0, weight=1)

        for i in range(30):
            l = ScriptWidget(canvas_content)
            l.grid(row=i, column=0, sticky='news')

        self.update()
        self.config(scrollregion=self.bbox("all"))

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

        All these menu actions generate a keystroke which is bound to
        a function. In this way, when we are tracking the users actions,
        clicking a button can be easily stored as a keystroke.
        """

        # initialize the menubar object
        self.menubar = tk.Menu(self.frame)
        ####################################
        # Define the label formatting
        ####################################

        # File, Edit, ... are defined to have a width of 6 characters
        menu_label_template = "{:<6}"

        # The items appearing in the cascade menu that appears when
        # clicking on File for example will have 15 characters width on the
        # left where the name of the functionality is provided and
        # 15 characters on the right where the keyboard shortcut is provided
        label_template = "{:<15}{:>15}"

        ####################################
        # FILE cascade menu build
        ####################################

        # add new item to the menubar
        menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=menu_label_template.format("File"), menu=menu)

        # add cascade menu items
        menu.add_command(
            label=label_template.format("Exit", "Ctrl+Q"),
            command=(lambda: self.event_generate("<Control-q>"))
        )


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
    def __init__(self, parent):
        super(ScriptWidget, self).__init__(parent)

        self.state = "Q" 
        '''
        Options:
         - "Q" for queued script
         - "R" for running
         - "F" for finnished
        '''
        pady = (5,20)
        padx_text = 5

        l = ttk.Label(self,text = '11')
        l.grid(row=0, column=1,sticky='news', padx = padx_text)
        b = ttk.Label(self,text = 'queued')
        b.grid(row=0, column=4, sticky='news', padx = padx_text)

        ttk.Separator(self, orient=tk.VERTICAL).grid(column=1, row=0, rowspan=1, sticky='nse')
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(column=0, row=0, columnspan=6, sticky='swe', pady=10)


        b = ImageButton(self,image = 'insert.gif')
        b.grid(row=0, column=0, sticky='swe', padx = (5,0))


        b = ImageButton(self,image = 'remove.gif')
        b.grid(row=0, column=2, sticky='news', pady=pady)
        b = ImageButton(self,image = 'move.gif')
        b.grid(row=0, column=3, sticky='news', pady=pady)
        
        b = ttk.Button(self,text = r'D:\git_repos\script_queuer\src')
        b.grid(row=0, column=5, sticky='news', pady=pady, padx = (0,40))
        
        self.columnconfigure(5, weight=1)

class ImageButton(ttk.Button):
    """docstring for ImageButton"""
    def __init__(self, *args, image=None, **kwargs):
        image = PhotoImage(file=image)
        image = image.subsample(2, 2)
        super(ImageButton, self).__init__(*args, image=image, **kwargs)
        self.image = image
        

GuiWindow()