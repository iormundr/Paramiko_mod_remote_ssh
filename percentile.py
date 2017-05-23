#!/usr/bin/env python3

import csv
import os
import sys
import glob
import numpy as np


def file_line_count(fname):
	fname.seek(0)
	for counter, l in enumerate(fname, start=1):
		pass
	fname.seek(3)
	return counter

def percentile_average_calculation_from_csv_files(files,perc,servers_list,errors='display'):
	for s_file in files:
		cpu = []
		mem = []
		with open(s_file, 'r') as f:
			rows = csv.reader(f)
			next(rows) * 3
			count = file_line_count(f)	
			file_name = s_file.split('_')
			server_name = file_name[2]
#			file_name = str(file_name[2])
			if count > 6:
				for row in rows:
					if len(row) == 4:
						try:
							cpu.append(float(row[1].strip()))
							mem.append(float(row[2].strip()))
						except ValueError as e:
							if errors == 'display':
								print('Bad row: ',row)
								print('Reason : ',e)
							continue
					elif len(row) == 5:
						try:
							cpu.append(float(row[2].strip()))
							mem.append(float(row[3].strip()))
						except ValueError as e:
							if errors == 'display':
								print('Bad row: ',row)
								print('Reason : ',e)
							continue
	
				c = np.percentile(cpu,perc)
				m = np.percentile(mem,perc)
				ac = np.average(cpu)
				am = np.average(mem)
				print("percentile , {:>5s},{:>10.2f},{:>10.2f},    {:>18s}".format(file_name[2],c,m,servers_list[server_name]))
				print("average    , {:>5s},{:>10.2f},{:>10.2f},    {:>18s}".format(file_name[2],ac,am,servers_list[server_name]))
			else:
				print("Stats for",file_name[2], servers_list[server_name],"are not avaliable. Files are empty.")




def read_csv_file(filename):
	'''
	Reading a csv file into a list. file consists of 'server name','Application name','Login name (username)'
	server01,web_server,root
	server02,app_server,guest2
	server03,app2_server,adams
	'''
	result_list = {}
	with open(filename, 'r') as f:
		rows = csv.reader(f)
		result_list = {row[0]:row[1] for row in rows}
		#print(result_list)
		#for row in rows:
			#print(row)
			#row[0]:row[1] for row in rows
			#print(dict(info))
	return result_list
	

def main(perc,file_path,servers_list):
	servers_list = read_csv_file(servers_list)
	files = glob.glob(file_path)
	if files == []:
		raise SystemExit("No such file/s was found...")
	os.system('clear')
	print("")
	print("Measurement,   Server,       CPU,    Memory,           Application")
	print("------------------------------------------------------------------")
	percentile_average_calculation_from_csv_files(files,perc,servers_list,errors='silent')
	print("------------------------------------------------------------------")

if __name__ == "__main__":
	if len(sys.argv) == 4:
		main(sys.argv[1],sys.argv[2] + "*.csv",sys.argv[3])
	else:
		print("Usage: ./percentile.py percentile_number path+beginnig_of_the_name csv_file_list")
		print("Example: ./percentile.py 95 /home/aaizenbe/maestro/Extract_ prod_csv_file")
		print("Please do not use special characters as *?. in the path to the file")

