<snippet>
  <content><![CDATA[
${1:Project Name}

This script will run on a dictionary of servers that will extract perf data from HP Glance via extract command over ssh paramiko connection.

1. Files will be generated on the remote hosts
2. Fetched to the location from the cmd input
3. CPU and Memory percentile and average will be calculated per every csv file that was transferred.

extract_and_calc.py:

Running extract command on a remote server and copying back to the chosen directory.

percentile.py

Calculating  average and percentile for every csv file that was created previously 

USAGE:
```
./extract_and_calc.py 30 prod_servers.temp cpu_mem.reptall /tmp/extract_dir_prod_servers/
```

## Example

```
[alex@testserver cp_scripts]$ ./extract_csv_files.py 30 prod_servers.temp cpu_mem.reptall /tmp/vision23
appserv1
status: ok
appserv2
status: ok

Measurement,   Server,       CPU,    Memory,           Application
------------------------------------------------------------------
percentile , ehpap312,     10.30,     33.47,       Reporting Batch
average    , ehpap312,      4.55,     27.84,       Reporting Batch
percentile , ehpap311,      0.76,     22.01,       Reporting Batch
average    , ehpap311,      0.36,     21.43,       Reporting Batch
------------------------------------------------------------------

```
></content>
</snippet>
