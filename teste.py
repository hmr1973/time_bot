import os
os.system("netsh interface ip set address "Local Area Connection" static 192.168.0.10 255.255.255.0 192.168.0.1 1")
print "IP ADRESS CHANGED!"