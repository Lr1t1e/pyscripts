"""
this is a python script that can be used to trace log and save wav file.

Requirement:

    + pyserial
    + colorama
    + click

    pip install pyserial colorama click


Usage:
    python log_trace_and_dump.py -p COM3 -b 1152000 
	python log_trace_and_dump.py -p COM5 -b 3000000 -wr 32000 -wn 2

	Press Esc to exit.
"""

import os 
if os.name == "nt": 
	os.system("title Terminal S")

from collections import deque
from datetime import datetime 
import sys
import threading
import wave

import colorama
import click
import serial
from serial.tools import list_ports

############################添加日志文件路径###########################
current_time = datetime.now().strftime("%Y%m%d-%H%M%S")
LOG_FILE_PATH = os.path.join(os.path.expanduser("~"), "Desktop","logfile",f"{current_time}.txt")

def default_output(msg):
	decoded_msg = msg.decode(errors = 'replace')
	print(decoded_msg,end="",flush=True)
	with open(LOG_FILE_PATH,"a",encoding='UTF-8') as f:
		f.write(decoded_msg)

def mac_output(msg):
	msg.replace(b'\n',b'\r\n')
	decoded_msg = msg.decode(errors = 'replace')
	print(decoded_msg,end='',flush=True)
	with open(LOG_FILE_PATH,"a",encoding='UTF-8')as f:
		f.write(decoded_msg)

def linux_output(msg):
	decoded_msg = msg.decode(errors ='replace')
	print(decoded_msg,end='',flush=True)
	with open(LOG_FILE_PATH,'a',encoding='UTF-8') as f:
		f.write(decoded_msg)

if sys.platform == "win32":
	output = default_output
elif sys.platform == "darwin":
	output = mac_output
else:
	output = linux_output

def wav_setup(wavnum, wavrate):
	wav_name = os.path.join(os.path.expanduser("~"),"Desktop","logfile","dump_out",f"dump_{current_time}.wav")
	wav = wave.open(wav_name,'wb')
	wav.setnchannels(wavnum)
	wav.setsampwidth(2)
	wav.setframerate(wavrate)
	return wav

def run(port, baudrate, wavnum, wavrate):
	try:
		device = serial.Serial(port=port,
								baudrate=baudrate,
								bytesize=8,
								parity='N',
								stopbits=1,
								timeout=0.1,
		)
	except:
		output(f'---------failed to open {port}---------'.encode())
		return 0

	output(f'---------connected to {port}---------'.encode())
	queue = deque()

	def read_input():
		if os.name == "nt":
			from msvcrt import getch
		else:
			import tty
			import termios
			stdin_fd = sys.stdin.fileno()
			tty_attr = termios.tcgetattr(stdin_fd)
			tty.setraw(stdin_fd)
			getch = lambda: sys.stdin.read(1).encode()

		while device.is_open:
			ch = getch()
			if ch == b'\x1b':  # Esc key exit
				break
			else:
				queue.append(ch)
		
		if os.name != 'nt':
			termios.tcsetattr(stdin_fd,termios.TCSADRAIN,tty_attr)

	colorama.init()

	thread = threading.Thread(target=read_input)
	thread.start()
	header = b'[trace][audio dump]'
	cache = deque(maxlen=16)
	wav = wav_setup(wavnum,wavrate)
	wav_len = 0

	while thread.is_alive():
		try:
			length = len(queue)
			if length > 0:
				device.write(b''.join(queue.popleft() for _ in range(length)))

			c = device.read(512)
			if len(cache) > 2:
				x = cache.popleft()
				output(x)
			cache.append(c)

			while True:
				date = b''.join(cache)
				position = date.find(header)
				if position < 0:
					break
				if position > 0:
					output(date[:position])
				position += len(header)
				date = date[position:]
				if len(date) < 4:
					date += device.read(4)
				size = int.from_bytes(date[:4],byteorder='little')
				date = date[4:]
				remain = size - len(date)

				cache.clear()
				if remain > 0:
					date += device.read(remain)
				elif len(date) > size:
					cache.append(date[size:])
				wav.writeframes(date[:size])
				wav_len += size

				if wav_len >= (16000 * 2 * wavnum * 60 * 30):
					wav.close()
					wav = wav_setup(wavnum,wavrate)
					wav_len = 0
			
		except IOError:
			output(f'\n---{port} is disconnected---\n'.encode())
			break

	wav.close()
	device.close()
	if thread.is_alive():
		output(f'\n---Press R to reconnect the device,or press Enter to exit---\n'.encode())
		thread.join()
		if queue and queue[0] in (b'r',b'R'):
			return 1
	return 0



@click.command()
@click.option('--port','-p',default=None,help='serial port name')
@click.option('--baudrate','-b',default=115200,help='serial port baudrate')
@click.option('--parity', default='N', type=click.Choice(['N', 'E', 'O', 'S', 'M']), help='set parity')
@click.option('-s', '--stopbits', default=1, help='set stop bits')
@click.option('-l', is_flag=True, help='list serial ports')
@click.option('--wavnum','-wn', default=3, help='wav set channels')
@click.option('--wavrate','-wr', default=16000, help='wav set framerate')

def main(port, baudrate, parity, stopbits, l, wavnum, wavrate):
	if l:
		ports = list_ports.comports()
		for p in ports:
			print(p.device)
		return 0
	if port is None:
		ports = list_ports.comports()
		if len(ports) == 0:
			print('no serial port found')
			return 0
		elif len(ports) == 1:
			port = ports[0].device
		else:
			print('multiple serial ports found, please specify one with -p')
			for com in ports:
				print(com.device)
			return 0
	
	while run(port, baudrate,wavnum,wavrate):
		pass

if __name__ == '__main__':
	main()

