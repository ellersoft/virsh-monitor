#!/bin/python3


import curses
import enum
import libvirt
import getopt
import sys


class Colors(enum.IntFlag):
	DEFAULT = 0
	GRAY = 1
	SELECT = 2
	HEAD = 4

	@classmethod
	def get_color(cls, gray, gray_sel, sel_i, i, item):
		sel_color = cls.SELECT if sel_i == (i - 1) else cls.DEFAULT
		gray_color = cls.GRAY if gray_sel(item) and gray else cls.DEFAULT
		return curses.color_pair(sel_color | gray_color)

	@classmethod
	def init_curses(cls):
		gray_fg = 8
		select_bg = 6
		head_bg = 2
		sel_head_fg = 0

		curses.start_color()
		curses.use_default_colors()
		curses.init_pair(cls.DEFAULT | cls.SELECT, sel_head_fg, select_bg)
		curses.init_pair(cls.HEAD, sel_head_fg, head_bg)
		curses.init_pair(cls.GRAY, gray_fg, -1)
		curses.init_pair(cls.GRAY | cls.SELECT, gray_fg, select_bg)


class State:
	# noinspection SpellCheckingInspection
	state_dict = {
		libvirt.VIR_DOMAIN_NOSTATE: ('no state', 0),
		libvirt.VIR_DOMAIN_RUNNING: ('running', 1),
		libvirt.VIR_DOMAIN_BLOCKED: ('blocked', 3),
		libvirt.VIR_DOMAIN_PAUSED: ('paused', 4),
		libvirt.VIR_DOMAIN_SHUTDOWN: ('shut down', 6),
		libvirt.VIR_DOMAIN_SHUTOFF: ('shut off', 7),
		libvirt.VIR_DOMAIN_CRASHED: ('crashed', 2),
		libvirt.VIR_DOMAIN_PMSUSPENDED: ('suspended', 5),
	}
	active_dict = {
		0: ('inactive', 1),
		1: ('active', 0),
	}

	@classmethod
	def state_val(cls, item):
		return cls.state_dict[item][0]

	@classmethod
	def state(cls, item):
		return cls.state_val(item.state()[0])

	@classmethod
	def sort_vm(cls, vm):
		return cls.state_dict[vm.state()[0]][1], vm.ID()

	@classmethod
	def sort_net_pool(cls, item):
		return cls.active_dict[item.isActive()][1], item.name()

	@classmethod
	def active_val(cls, item):
		return cls.active_dict[item][0]

	@classmethod
	def active(cls, item):
		return cls.active_val(item.isActive())

	@staticmethod
	def set_x_for_true(x):
		return 'X' if x else ' '

	@classmethod
	def auto_start(cls, item):
		return cls.set_x_for_true(item.autostart())

	@classmethod
	def persistent(cls, item):
		return cls.set_x_for_true(item.isPersistent())


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


def render(std_scr, data, sel, sel_i):
	pool_diff = 2
	longest_net = max((len(net.name()) for net in data[1]), default=0)
	longest_pool = max((len(pool.name()) for pool in data[2]), default=0)
	longest_net = max(longest_net, longest_pool - pool_diff)
	height, width = std_scr.getmaxyx()
	net_offset = width - longest_net - 9 - pool_diff - 3
	vm_width = net_offset - 3 - 9 - 1 - 2

	helps = [("TAB", "Next"), ("F1", "Start"), ("F2", "Stop"), ("F10", "Quit")]
	vm_table = [("ID", 3, False), ("VM", vm_width - 1, True), ("STATUS", 9, False)]
	net_table = [("NET", longest_net, True), ("STATUS", 8, False), ("A", 1, False), ("P", 1, False)]
	pool_table = [("POOL", longest_net + pool_diff, True), ("STATUS", 8, False), ("A", 1, False)]

	vms = [['-' if vm.ID() == -1 else str(vm.ID()), vm.name(), State.state(vm)] for vm in data[0]]
	nets = [[net.name(), State.active(net), State.auto_start(net), State.persistent(net)] for net in data[1]]
	pools = [[pool.name(), State.active(pool), State.auto_start(pool)] for pool in data[2]]

	tables = [
		(0, 0, 0, vm_table, lambda vm: vm[2] != State.state_val(libvirt.VIR_DOMAIN_RUNNING), vms),
		(1, net_offset, 0, net_table, lambda net: net[1] != State.active_val(1), nets),
		(2, net_offset, len(nets) + 2, pool_table, lambda pool: pool[1] != State.active_val(1), pools)
	]

	for sel_c, x, y, table, sel_test, items in tables:
		table_sel = sel_i if sel == sel_c else -1
		print_table(std_scr, table_sel, x, y, table, sel_test, items)

	print_help(std_scr, curses.color_pair(Colors.DEFAULT | Colors.SELECT), helps)


def pump(std_scr, con, sel, sel_i):
	vms = sorted(con.listAllDomains(), key=State.sort_vm)
	nets = sorted(con.listAllNetworks(), key=State.sort_net_pool)
	pools = sorted(con.listAllStoragePools(), key=State.sort_net_pool)
	data = [vms, nets, pools]

	std_scr.clear()
	render(std_scr, data, sel, sel_i)
	std_scr.refresh()
	c = std_scr.getch()

	if c == curses.KEY_F10:
		return False, sel, sel_i
	elif c == ord('\t'):
		sel = 0 if sel == 2 else sel + 1
	elif c == curses.KEY_DOWN or c == curses.KEY_UP:
		sel_i += -1 if c == curses.KEY_UP else 1
	elif (c == curses.KEY_F1 or c == curses.KEY_F2) and sel_i < len(data[sel]):
		try:
			if c == curses.KEY_F1:
				# noinspection PyUnresolvedReferences
				data[sel][sel_i].create()
			else:
				# noinspection PyUnresolvedReferences
				data[sel][sel_i].destroy()
		except libvirt.libvirtError:
			pass

	if sel_i == -1:
		sel_i += 1
	if sel_i >= len(data[sel]):
		sel_i = len(data[sel]) - 1
	return True, sel, sel_i


def main(std_scr, con):
	curses.curs_set(0)
	curses.halfdelay(20)
	Colors.init_curses()
	cont, sel, sel_i = True, 0, 0

	while cont:
		cont, sel, sel_i = pump(std_scr, con, sel, sel_i)


if __name__ == '__main__':
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'c:')
	except getopt.GetoptError as err:
		print(err)
		sys.exit(1)

	uri = None
	for o, a in opts:
		if o == '-c':
			uri = a

	try:
		conn = libvirt.open(uri)
	except libvirt.libvirtError as err:
		print('Failed to open connection to the hypervisor')
		sys.exit(1)

	curses.wrapper(main, conn)
