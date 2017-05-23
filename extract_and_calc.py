#!/usr/bin/env python3
import paramiko
import logging
import socket
import time
import datetime
import sys
import csv
import datetime
import os
import percentile

perc = 95 #95th percentile to calculate for percentile.py input

# ================================================================
# class MySSH
# ================================================================
class MySSH:
	def __init__(self, compress=True, verbose=False):
		self.ssh = None
		self.transport = None
		self.compress = compress
		self.bufsize = 65536

		# Setup the logger
		self.logger = logging.getLogger('MySSH')
		fmt = '%(asctime)s MySSH:%(funcName)s:%(lineno)d %(message)s'
		format = logging.Formatter(fmt)
		handler = logging.StreamHandler()
		handler.setFormatter(format)
		self.logger.addHandler(handler)
		self.info = self.logger.info

	def __del__(self):
		if self.transport is not None:
			self.transport.close()
			self.transport = None

	def connect(self, hostname, username, port=22):
		self.info('connecting %s@%s:%d' % (username, hostname, port))
		self.hostname = hostname
		self.username = username
		self.port = port
		self.ssh = paramiko.SSHClient()
		self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		try:
			self.ssh.connect(hostname=hostname,port=port,username=username)
			self.transport = self.ssh.get_transport()
			self.transport.use_compression(self.compress)
			#print('succeeded: %s@%s:%d' % (username,hostname,port))
		except socket.error as e:
			self.transport = None
			print('failed: %s@%s:%d: %s' % (username,hostname,port,str(e)))
		except paramiko.BadAuthenticationType as e:
			self.transport = None
			print('failed: %s@%s:%d: %s' % (username,hostname,port,str(e)))
		except paramiko.AuthenticationException as e:
			self.transport = None
			print('failed: %s@%s:%d: %s' % (username,hostname,port,str(e)))

		return self.transport is not None

	def run(self, cmd, input_data=None, timeout=10):
		if self.transport is None:
			print('no connection to %s@%s:%s' % (str(self.username),str(self.hostname),str(self.port)))
			return -1, 'ERROR: connection not established\n'

		# Fix the input data.
		input_data = self._run_fix_input_data(input_data)

		# Initialize the session.
		session = self.transport.open_session()
		session.set_combine_stderr(True)
		session.get_pty()
		session.exec_command(cmd)
		output = self._run_poll(session, timeout, input_data)
		status = session.recv_exit_status()
		session.transport.close()
		return status, output

	def connected(self):
		return self.transport is not None

	def _run_fix_input_data(self, input_data):
		if input_data is not None:
			if len(input_data) > 0:
				if '\\n' in input_data:
					# Convert \n in the input into new lines.
					lines = input_data.split('\\n')
					input_data = '\n'.join(lines)
			return input_data.split('\n')
		return []

	def _run_send_input(self, session, stdin, input_data):
		if input_data is not None:
			self.info('session.exit_status_ready() %s' % str(session.exit_status_ready()))
			self.info('stdin.channel.closed %s' % str(stdin.channel.closed))
			if stdin.channel.closed is False:
				self.info('sending input data')
				stdin.write(input_data)

	def _run_poll(self, session, timeout, input_data):
		interval = 0.1
		maxseconds = timeout
		maxcount = maxseconds / interval
		input_idx = 0
		timeout_flag = False
		start = datetime.datetime.now()
		start_secs = time.mktime(start.timetuple())
		output = ""
		session.setblocking(0)
		while True:
			if session.recv_ready():
				data = str(session.recv(self.bufsize))
				output += data
				self.info('read %d bytes, total %d' % (len(data), len(output)))

				if session.send_ready():
					# We received a potential prompt.
					# In the future this could be made to work more like
					# pexpect with pattern matching.
					if input_idx < len(input_data):
						data = input_data[input_idx] + '\n'
						input_idx += 1
						session.send(data)

			if session.exit_status_ready():
				break

			# Timeout check
			now = datetime.datetime.now()
			now_secs = time.mktime(now.timetuple()) 
			et_secs = now_secs - start_secs
			if et_secs > maxseconds:
				timeout_flag = True
				break
			time.sleep(0.100)

		if session.recv_ready():
			data = session.recv(self.bufsize)
			output += data
		if timeout_flag:
			output += '\nERROR: timeout after %d seconds\n' % (timeout)
			session.close()
		return output

def connect_wrapper(hostname, username, cmd, indata=None, output='display'):
	ssh = MySSH()
	ssh.connect(hostname=hostname,username=username,port=22)
	if output == 'display':
		print()
		print('=' * 64)
		print('command: %s' % (cmd))
		status, output = ssh.run(cmd, indata)
		print('status : %d' % (status))
		print('output : %d bytes' % (len(output)))
		print('=' * 64)
		print('%s' % (output))
	else:
		status, output = ssh.run(cmd, indata)
		return status, output

def read_csv_file(filename):
	'''
	Reading a csv file into a list. file consists of 'server name','Application name','Login name (username)'
	server01,web_server,root
	server02,app_server,guest2
	server03,app2_server,adams
	'''
	result_list = []
	with open(filename, 'r') as f:
		rows = csv.reader(f)
		for row in rows:
			info = {
				'server_name': row[0],
				'app_name': row[1],
				'user_name': row[2]	
				}
			result_list.append(info)
	return result_list

def remote_copy_to_server(server_name,user_name,file_name,destination_path):
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	try:
		ssh.connect(hostname=server_name, username=user_name,allow_agent=True)
		sftp = ssh.open_sftp()
	except paramiko.AuthenticationException as e:
		print("Unable to establish connection to",server_name)
		print("Error:",e)
		return -1
	except socket.error as e:
		print("Wrong server name")
		print("Eror:",e)
		return -1
	sftp.put(file_name,destination_path + file_name)
	sftp.close()
	return 0
	

def remote_copy_from_server(server_name,user_name,file_name,destination_path):
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	try:
		ssh.connect(hostname=server_name, username=user_name,allow_agent=True)
		sftp = ssh.open_sftp()
	except paramiko.AuthenticationException as e:
		print("Unable to establish connection to",server_name)
		print("Error:",e)
		return -1
	sftp.get(file_name,destination_path + file_name)
	sftp.close()
	return 0
	
def remote_extract_command(server_name,user_name,days_back):
	end_date = (datetime.datetime.now() + datetime.timedelta(-1)).strftime("%Y%m%d")
	end_date_slash_format = (datetime.datetime.now() + datetime.timedelta(-1)).strftime("%m/%d/%d")
	start_date_slash_format = (datetime.datetime.now() + datetime.timedelta(-int(days_back))).strftime("%m/%d/%y")
	extract_command = '/opt/perf/bin/extract -xp -r /home/' + user_name + '/reptall.new -f /home/' + user_name + '/Extract_' + end_date + '_' + server_name + '_glb_' + days_back + 'days.csv -G -b ' + start_date_slash_format + ' 00:00 -e ' + end_date_slash_format + ' 23:59'
	file_name_to_return = '/home/' + user_name + '/Extract_' + end_date + '_' + server_name + '_glb_' + days_back + 'days.csv'
	connect_wrapper(server_name,user_name,'rm -f /home/' + user_name + '/Extract_*' + server_name + '*.csv',output='noDisplay')
	connect_wrapper(server_name,user_name,extract_command,output='noDisplay')
	file_name_to_return = file_name_to_return.split("/")
	return file_name_to_return

def make_sure_path_exists(path):
	try:
		os.mkdir(path)
	except FileExistsError:
		print("Path alraedy exists",path)
	except PermissionError:
		raise SystemExit("Warning: Cannot create directory.\nCheck permission to the path",path)
	if path[-1] != '/':
		path = path + '/'
		return path
	return path

	
if __name__ == '__main__':
	if len(sys.argv) == 5:
		days_to_extract = sys.argv[1]
		input_list = read_csv_file(sys.argv[2])	
		metric_file = sys.argv[3]
		path_to_copy_back = make_sure_path_exists(sys.argv[4])
		for info in input_list:
			print(info['server_name'])
			status = remote_copy_to_server(info['server_name'],info['user_name'],metric_file,'/home/' + info['user_name'] + '/')
			if status != 0:
				print("Server {} was skipped due to a problem".format(info['server_name']))
			else:
				print("status: ok")
				file_name_to_copy_back = remote_extract_command(info['server_name'],info['user_name'],days_to_extract)
				remote_copy_from_server(info['server_name'],info['user_name'],file_name_to_copy_back[-1],path_to_copy_back)
		#server_list = percentile.read_csv_file(sys.argv[2])
		path_to_copy_back += 'Extract_*.csv'
		percentile.main(perc,path_to_copy_back,sys.argv[2])
		
	else:
		print("Missing input parameters")
		print("Example: ./extract_and_calc.py 30 prod_servers.temp cpu_mem.reptall /tmp/")
