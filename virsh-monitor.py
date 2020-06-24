#!/bin/python3


import subprocess
import re
import curses
import enum


class Colors(enum.IntFlag):
	DEFAULT = 0
	GRAY = 1
	SELECT = 2
	HEAD = 4

	@staticmethod
	def get_color(gray, gray_sel, sel_i, i, item):
		sel_color = Colors.SELECT if sel_i == (i - 1) else Colors.DEFAULT
		gray_color = Colors.GRAY if gray_sel(item) and gray else Colors.DEFAULT
		return curses.color_pair(sel_color | gray_color)


def print_table(std_scr, sel_i, x, y, cols, gray_sel, items):
	head_color = curses.color_pair(Colors.HEAD)
	sel_color = curses.color_pair(Colors.DEFAULT | Colors.SELECT)

	total_len = sum(col[1] + 1 for col in cols)
	std_scr.insstr(y, x, ' ' * total_len, head_color)
	col_offset = 0

	if sel_i > -1:
		std_scr.addstr(y + sel_i + 1, x, ' ' * total_len, sel_color)

	for c, (name, minsize, gray) in enumerate(cols, 0):
		std_scr.addstr(y, x + col_offset, name, head_color)
		for i, item in enumerate(items, 1):
			std_scr.addstr(y + i, x + col_offset, item[c], Colors.get_color(gray, gray_sel, sel_i, i, item))

		col_offset += minsize + 1


def print_help(std_scr, help_color, helps):
	height, width = std_scr.getmaxyx()
	std_scr.insstr(height - 1, 0, ' ' * width, help_color)
	max_len = max(len(x[1]) for x in helps) + 1
	offset = 0
	for key, name in helps:
		std_scr.insstr(height - 1, offset, key)
		std_scr.insstr(height - 1, offset + len(key), name, help_color)
		offset += len(key) + max_len


def set_x_for_yes(x):
	return 'X' if x == 'yes' else ' '


def render(std_scr, vms, nets, pools, sel, sel_i):
	pool_diff = 2
	longest_net = max(len(net[0]) for net in nets)
	longest_pool = max(len(pool[0]) for pool in pools)
	longest_net = max(longest_net, longest_pool - pool_diff)
	height, width = std_scr.getmaxyx()
	net_offset = width - longest_net - 9 - pool_diff - 3
	vm_width = net_offset - 3 - 9 - 1 - 2

	helps = [("TAB", "Next"), ("F1", "Start"), ("F2", "Stop"), ("F10", "Quit")]
	vm_table = [("ID", 3, False), ("VM", vm_width - 1, True), ("STATUS", 9, False)]
	net_table = [("NET", longest_net, True), ("STATUS", 8, False), ("A", 1, False), ("P", 1, False)]
	pool_table = [("POOL", longest_net + pool_diff, True), ("STATUS", 8, False), ("A", 1, False)]
	nets = [[net[0], net[1], set_x_for_yes(net[2]), set_x_for_yes(net[3])] for net in nets]
	pools = [[pool[0], pool[1], set_x_for_yes(pool[2])] for pool in pools]

	tables = [
		(0, 0, 0, vm_table, lambda vm: vm[2] != "running", vms),
		(1, net_offset, 0, net_table, lambda net: net[1] != "active", nets),
		(2, net_offset, len(nets) + 2, pool_table, lambda pool: pool[1] != "active", pools)
	]

	for sel_c, x, y, table, sel_test, items in tables:
		table_sel = sel_i if sel == sel_c else -1
		print_table(std_scr, table_sel, x, y, table, sel_test, items)

	print_help(std_scr, curses.color_pair(Colors.DEFAULT | Colors.SELECT), helps)


def virsh(*args):
	out = subprocess.check_output(('virsh', *args))
	out = re.split('[\r\n]+', out.decode("utf-8"))
	return [[x.strip() for x in re.split('\\s{2,}', line)] for line in out]


def main(std_scr):
	curses.curs_set(0)
	curses.halfdelay(20)
	curses.start_color()
	curses.use_default_colors()
	curses.init_pair(Colors.DEFAULT | Colors.SELECT, 0, 6)
	curses.init_pair(Colors.HEAD, 0, 2)
	curses.init_pair(Colors.GRAY, 8, -1)
	curses.init_pair(Colors.GRAY | Colors.SELECT, 8, 6)
	sel = 0
	sel_i = 0

	start_commands = ['start', 'net-start', 'pool-start']
	stop_commands = ['destroy', 'net-destroy', 'pool-destroy']

	while True:
		vms = virsh('list', '--all')[2:][:-1]
		nets = virsh('net-list', '--all')[2:][:-1]
		pools = virsh('pool-list', '--all')[2:][:-1]

		args = [vms, nets, pools]
		arg_indexes = [1, 0, 0]

		std_scr.clear()
		render(std_scr, vms, nets, pools, sel, sel_i)
		std_scr.refresh()
		c = std_scr.getch()

		if c == curses.KEY_F10:
			exit()
		elif c == ord('\t'):
			sel = 0 if sel == 2 else sel + 1
		elif c == curses.KEY_DOWN or c == curses.KEY_UP:
			sel_i += -1 if c == curses.KEY_UP else 1
		elif (c == curses.KEY_F1 or c == curses.KEY_F2) and sel_i < len(args[sel]):
			commands = stop_commands if c == curses.KEY_F2 else start_commands
			virsh(commands[sel], args[sel][sel_i][arg_indexes[sel]])

		if sel_i == -1:
			sel_i += 1
		if sel_i >= len(args[sel]):
			sel_i = len(args[sel]) - 1


if __name__ == '__main__':
	curses.wrapper(main)
