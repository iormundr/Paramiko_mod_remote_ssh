#!/usr/local/python-3.6.0/bin/python3
import paramiko
import logging
import socket
import time
import datetime
import sys
import csv
import datetime


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
		print("Unable to copy to",server_name)
		print("Error:",e)
		return -1
	sftp.put(file_name,destination_path + file_name)
	sftp.close()
	print("copied successfully!")
	

def remote_extract_command(server_name,user_name,days_back):
	date = datetime.datetime.now().strftime("%Y%m%d")
	build_command = '/opt/perf/bin/extract -xp -r /home/aaizenbe/reptall.new -f /home/aaizenbe/Extract_120517_"$1"_glb_30days.csv -G -b 04/08/17 00:00 -e 05/07/17 23:59'

	

if __name__ == '__main__':


	#connect_wrapper_no_add_output('vmbdcl007','aaizenbe','uptime')
	#for server_name in prod_servers_list:
	#   status,output = connect_wrapper(server_name['name'],server_name['username'],'uptime',output='do-not-display-display')
	#   if status == 0:
	#	   print("server {} is ok".format(server_name['name']))
	prod_list = read_csv_file('prod_servers.csv')	
	#for i in prod_list:
	#	print(i['server_name'])
	

'''
cat servers_list  | awk '{print "ssh -q aaizenbe@"$1" -n \" /opt/perf/bin/extract -xp -r /home/aaizenbe/reptall.new -f /home/aaizenbe/Extract_120517_"$1"_glb_30days.csv -G -b 04/08/17 00:00 -e 05/07/17 23:59 \""}'
cat servers_list  | awk '{print "scp aaizenbe@"$1":/home/aaizenbe/Extract_120517_"$1"_glb_30days.csv ."}'
'''
