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
#   3. Edit the three configuration options below, following the directions for
#      each.  As this is a quick hack, it assumes everything goes right.
#
# Set the domain name below.  The API key MUST have write access to this 
# resource ID.
#
DOMAIN = "home.yourdomain.com"
#
# Your Linode API key.  You can generate this by going to your profile in the
# Linode manager.  It should be fairly long.
#
KEY = "yourapikey"
#
# The URI of a Web service that returns your IP address as plaintext.  You are
# welcome to leave this at the default value and use mine.  If you want to run
# your own, the source code of that script is:
#
#     <?php
#     header("Content-type: text/plain");
#     printf("%s", $_SERVER["REMOTE_ADDR"]);
#
GETIP = "http://hosted.jedsmith.org/ip.php"
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
	return json["DATA"]

def ip():
	if DEBUG:
		print("-->", GETIP)
	file, headers = urlretrieve(GETIP)
	result = open(file).read().strip()
	if DEBUG:
		print("<--", file)
		print(headers, end="")
		print(result)
		print()
	return result

def main():
	try:
		# Determine DomainId
		domains = execute("domain.list", {})
		for domain in domains:
			if DOMAIN.endswith(domain["DOMAIN"]):
				matchedDomain = domain
				break
		if matchedDomain is None:
			raise Exception("Domain not found")
		domainId = matchedDomain["DOMAINID"]
		domainName = matchedDomain["DOMAIN"]
		if DEBUG:
			print("Found matching domain:")
			print("  DomainId = {0}".format(domainId))
			print("  Name = {0}".format(domainName))
		
		# Determine resource id (subdomain)
		resources = execute("domain.resource.list",
			{"DomainId": domainId})
		for resource in resources:
			if resource["NAME"] + "." + domainName == DOMAIN:
				matchedResource = resource
				break
		if resource is None:
			raise Exception("Resource not found")
		resourceId = matchedResource["RESOURCEID"]
		oldIp = matchedResource["TARGET"]
		if DEBUG:
			print("Found matching resource:")
			print("  ResourceId = {0}".format(resourceId))
			print("  Target = {0}".format(oldIp))

		# Determine public ip
		newIp = ip()
		if oldIp == newIp:
			print("OK")
			return 0
		
		# Update public ip
		execute("domain.resource.update", {
			"ResourceID": resourceId,
			"DomainID": domainId,
			"Target": newIp})
		print("OK {0} -> {1}".format(oldIp, newIp))
		return 1
	except Exception as excp:
		print("FAIL {0}: {1}".format(type(excp).__name__, excp))
		return 2

if __name__ == "__main__":
	exit(main())
