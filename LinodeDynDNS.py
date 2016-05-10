#!/usr/bin/python3.1
#
# Easy Python3 Dynamic DNS
# By Jed Smith <jed@jedsmith.org> 4/29/2009
# This code and associated documentation is released into the public domain.
#
# This script **REQUIRES** Python 3.0 or above.  Python 2.6 may work.
# To see what version you are using, run this:
#
#   python --version
#
# To use:
#
#   0. You'll probably have to edit the shebang above.
#
#   1. In the Linode DNS manager, edit your zone (must be master) and create
#      an A record for your home computer.  You can name it whatever you like;
#      I call mine 'home'.  Fill in 0.0.0.0 for the IP.
#
#   2. Save it.
#
#   3. Go back and edit the A record you just created. Make a note of the
#      ResourceID in the URI of the page while editing the record.
#
#   4. Edit the four configuration options below, following the directions for
#      each.  As this is a quick hack, it assumes everything goes right.
#
# First, the resource ID that contains the 'home' record you created above. If
# the URI while editing that A record looks like this:
#
#  linode.com/members/dns/resource_aud.cfm?DomainID=98765&ResourceID=123456
#  You want 123456. The API key MUST have write access to this resource ID.
#
# As of lately ( 5/2016 ) the DOMAINID is not in the URI
# https://manager.linode.com/dns/resource/domain.com?id=000000
#                                          Resource ID  ^   
#
RESOURCE = "000000"
#
#
# Find this domain by going to the DNS Manager in Linode and then clicking
# check next to the domain associates with the above resource ID. 
# Number should be sitting in parentheses next to domain name.
#
#
DOMAIN = "000000"
#
# Your Linode API key.  You can generate this by going to your profile in the
# Linode manager.  It should be fairly long.
#
KEY = "abcdefghijklmnopqrstuvwxyz"
#
# The URI of a Web service that returns your IP address as plaintext.  You are
# welcome to leave this at the default value and use mine.  If you want to run
# your own, the source code of that script is:
#
#     <?php
#     header("Content-type: text/plain");
#     printf("%s", $_SERVER["REMOTE_ADDR"]);
#
GETIP = "http://icanhazip.com/"
#
# If for some reason the API URI changes, or you wish to send requests to a
# different URI for debugging reasons, edit this.  {0} will be replaced with the
# API key set above, and & will be added automatically for parameters.
#
API = "https://api.linode.com/api/?api_key={0}&resultFormat=JSON"
#
# Comment or remove this line to indicate that you edited the options above.
#
exit("Did you edit the options?  vi this file open.")
#
# That's it!
#
# Now run dyndns.py manually, or add it to cron, or whatever.  You can even have
# multiple copies of the script doing different zones.
#
# For automated processing, this script will always print EXACTLY one line, and
# will also communicate via a return code.  The return codes are:
#
#    0 - No need to update, A record matches my public IP
#    1 - Updated record
#    2 - Some kind of error or exception occurred
#
# The script will also output one line that starts with either OK or FAIL.  If
# an update was necessary, OK will have extra information after it.
#
# If you want to see responses for troubleshooting, set this:
#
DEBUG = False


#####################
# STOP EDITING HERE #

try:
	from json import load
	from urllib.parse import urlencode
	from urllib.request import urlretrieve
except Exception as excp:
	exit("Couldn't import the standard library. Are you running Python 3?")

def execute(action, parameters):
	# Execute a query and return a Python dictionary.
	uri = "{0}&action={1}".format(API.format(KEY), action)
	if parameters and len(parameters) > 0:
		uri = "{0}&{1}".format(uri, urlencode(parameters))
	if DEBUG:
		print("-->", uri)
	file, headers = urlretrieve(uri)
	if DEBUG:
		print("<--", file)
		print(headers, end="")
		print(open(file).read())
		print()
	json = load(open(file), encoding="utf-8")
	if len(json["ERRORARRAY"]) > 0:
		err = json["ERRORARRAY"][0]
		raise Exception("Error {0}: {1}".format(int(err["ERRORCODE"]),
			err["ERRORMESSAGE"]))
	return load(open(file), encoding="utf-8")

def ip():
	if DEBUG:
		print("-->", GETIP)
	file, headers = urlretrieve(GETIP)
	if DEBUG:
		print("<--", file)
		print(headers, end="")
		print(open(file).read())
		print()
	return open(file).read().strip()

def main():
	try:
		res = execute("domainResourceGet", {"DomainID": DOMAIN, "ResourceID": RESOURCE})["DATA"]
		res = res[0] # Turn res from a list to a dict
		if(len(res)) == 0:
			raise Exception("No such resource?".format(RESOURCE))
		public = ip()
		if res["TARGET"] != public:
			old = res["TARGET"]
			request = {
				"ResourceID": res["RESOURCEID"],
				"DomainID": res["DOMAINID"],
				"Name": res["NAME"],
				"Type": res["TYPE"],
				"Target": public,
				"TTL_Sec": res["TTL_SEC"]
			}
			execute("domainResourceSave", request)
			print("OK {0} -> {1}".format(old, public))
			return 1
		else:
			print("OK")
			return 0
	except Exception as excp:
		import traceback; traceback.print_exc()
		print("FAIL {0}: {1}".format(type(excp).__name__, excp))
		return 2

if __name__ == "__main__":
	exit(main())
