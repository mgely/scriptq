import sys
import unittest
from os.path import join, dirname
from time import sleep

test_directory = dirname(__file__)
sys.path.append(join(join(dirname(test_directory), "src")))

from gui import GuiWindow

script_success = join(test_directory,'script_success.py')
script_open_success = join(test_directory,'script_open_success.py')
script_fail = join(test_directory,'script_fail.py')
script_nonexistent = join(test_directory,'nonexistent.py')
script_long = join(test_directory,'script_long.py')

def open_gui():
	return GuiWindow(unittesting = True).bf

def run(g,position, time_limit = 10):
	g.run(position)
	s = 0
	while g.state == 'running' and s<time_limit:
		g.update()
		s+=g.t_output_monitoring/1000
		sleep(g.t_output_monitoring/1000)

class TestAll(unittest.TestCase):

	def test_open_gui(self):
		g = open_gui()

	def test_insert_0(self):
		g = open_gui()
		g.insert(0,script_fail)
		g.insert(0,script_success)
		self.assertEqual(g.scripts[1].script_path,script_success)

	def test_insert_1(self):
		g = open_gui()
		g.insert(0,script_success)
		g.insert(1,script_fail)
		self.assertEqual(g.scripts[-1].script_path,script_fail)

	def test_move(self):
		g = open_gui()
		g.insert(0,script_success)
		g.insert(1,script_fail) # inserts after row 1 into 2
		g.move(position = 2, # current position
			new_position = 0 # move after this row
			)
		self.assertEqual(g.scripts[1].script_path,script_fail)


	def test_move_with_done(self):
		g = open_gui()

		# Run a script
		g.insert(0,script_success) 
		run(g,1)

		g.insert(1,script_fail) # inserts after row 1 into 2
		g.move(position = 1, # current position
			new_position = 0 # move after this row
			)
		self.assertEqual(g.scripts[2].script_path,script_fail)

	def test_remove(self):
		g = open_gui()
		g.insert(0,script_success) # inserts after row 0 into 1
		g.insert(1,script_fail) 
		g.remove(1)
		self.assertEqual(g.scripts[1].script_path,script_fail)

	def test_run(self):
		g = open_gui()
		g.insert(0,script_success) # inserts after row 0 into 1
		g.insert(1,script_fail) 
		run(g,1)

		self.assertEqual(g.scripts[1].script_path,script_success)
		self.assertEqual(g.scripts[1].state,'ended')
		self.assertEqual(g.scripts[1].success,'done')
		self.assertIn('1',g.scripts[1].log)

		self.assertEqual(g.scripts[2].script_path,script_fail)
		self.assertEqual(g.scripts[2].state,'ended')
		self.assertEqual(g.scripts[2].success,'failed')
		self.assertIn('NameError',g.scripts[2].log)


	def test_run_working_directory(self):
		g = open_gui()
		g.insert(0,script_open_success) 
		run(g,1)
		self.assertEqual(g.scripts[1].state,'ended')
		self.assertEqual(g.scripts[1].success,'done')


	def test_run_nonexistent(self):
		g = open_gui()
		g.insert(0,script_nonexistent) 
		run(g,1)
		self.assertEqual(g.scripts[1].state,'ended')
		self.assertEqual(g.scripts[1].success,'failed')
		self.assertIn("can't open file",g.scripts[1].log)


	def test_stop(self):
		g = open_gui()
		g.insert(0,script_long) 
		run(g,1, time_limit = 2*g.t_output_monitoring/1000)
		g.stop()
		sleep(2*g.t_output_monitoring/1000)
		g.update()
		self.assertEqual(g.scripts[1].state,'ended')
		self.assertEqual(g.scripts[1].success,'stopped')
		self.assertIn(g.interrupted_error_message,g.scripts[1].log)

		self.assertEqual(g.scripts[2].script_path,script_long)
		self.assertEqual(g.scripts[2].state,'ready')

	def test_close_open_output(self):
		g = open_gui()
		g.on_closing_output_window()
		g.update()
		g.build_output_window()
		g.update()

	def test_open_log(self):
		g = open_gui()
		g.insert(0,script_success)
		run(g,1)
		g.scripts[1].view_log()

if __name__ == "__main__":
    unittest.main()