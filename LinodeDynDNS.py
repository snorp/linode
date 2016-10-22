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
#   3. If you did not already create an API key, please generate it
# 
#	4. Copy LinodeDynDNS.conf.template into LinodeDynDNS.conf
#
#	5. Edit LinodeDynDNS.conf
#
#	6. Configure your Linode API key
#
#	7. Configure your domain
#
# 	8. Configure your resource (server)
#
#	9. Configure the GETIP
#
# The URI of a Web service that returns your IP address as plaintext.  You are
# welcome to leave this at the default value and use mine.  If you want to run
# your own, the source code of that script is:
#
#     <?php
#     header("Content-type: text/plain");
#     printf("%s", $_SERVER["REMOTE_ADDR"]);
#
#
# If for some reason the API URI changes, or you wish to send requests to a
# different URI for debugging reasons, edit this.  {0} will be replaced with the
# API key set above, and & will be added automatically for parameters.
#
API = "https://api.linode.com/api/?api_key={0}&resultFormat=JSON"
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
CONFIG_SECTION = 'LINODE'
CONFIG_OPTIONS = ['KEY', 'GETIP', 'RESOURCE', 'DOMAIN']

#####################
# STOP EDITING HERE #

try:
	import os
	from json import load
	from urllib.parse import urlencode
	from urllib.request import urlretrieve
	from configparser import SafeConfigParser
except Exception as excp:
	exit("Couldn't import the standard library. Are you running Python 3?")

def execute(action, key, parameters):
	# Execute a query and return a Python dictionary.
	uri = "{0}&api_action={1}".format(API.format(key), action)
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

def ip(GETIP):
	if DEBUG:
		print("-->", GETIP)
	file, headers = urlretrieve(GETIP)
	if DEBUG:
		print("<--", file)
		print(headers, end="")
		print(open(file).read())
		print()
	return open(file).read().strip()

def load_config():
	# determine the conf file based on path and filename
	filename = os.path.join(os.path.dirname(__file__), os.path.basename(__file__)[0:-3] + '.conf' )
	config = SafeConfigParser()
	
	# exit of config file is not created
	if not os.path.exists(filename):
		print('Config file {0} was not found.\nExiting...\n'.format(filename))

		exit(-1)

	config.read(filename)
	
	# validate the file
	if not(CONFIG_SECTION == config.default_section or CONFIG_SECTION in config.sections()):
		print('[{0}] section is not defined'.format(CONFIG_SECTION))
		exit(-1)
	
	# validate config options
	for option in CONFIG_OPTIONS:
		if not config.has_option(CONFIG_SECTION, option):
			print("Option '{0}' is not defined in section [{1}]".format(option, CONFIG_SECTION))
			exit(-1)
	
	if DEBUG:
		print("Configuration is loaded")
	return config 

def main():
	try:
		# load configuration file
		config = load_config()
		key = config.get(CONFIG_SECTION, 'KEY')
		# obtain list of all domains
		res = execute("domain.list", key, None)

		# determine the DOMAINID of our domain
		DOMAINID = None
		cfg_domain = config.get(CONFIG_SECTION, 'DOMAIN')
		for domain in res['DATA']:
			if domain['DOMAIN'] == cfg_domain:
				DOMAINID = domain['DOMAINID']
				break
		
		if not DOMAINID:
			raise Exception(("Could not determine the DOMAINID for domain '{0}'".format(cfg_domain)))
		
		# determine the RESOURCEID of configured RESOURCE
		cfg_resource = config.get(CONFIG_SECTION, 'RESOURCE')
		RESOURCEID = None
		# obtain list of resources within domain
		res = execute("domain.resource.list", key, {'DOMAINID': DOMAINID})
		# determine the RESOUCEID of resource
		for resource in res['DATA']:
			if resource['NAME'] == cfg_resource:
				RESOURCEID=resource['RESOURCEID']
				break

		if not RESOURCEID:
			raise Exception("Could not determine the RESOURCEID for resource '{0}'".format(cfg_resource))		

		res = execute("domain.resource.list", key, {"DomainID": DOMAINID, "ResourceID": RESOURCEID})["DATA"]
		res = res[0] # Turn res from a list to a dict
		if(len(res)) == 0:
			raise Exception("No such resource?".format(RESOURCEID))
		public = ip(config.get(CONFIG_SECTION, 'GETIP'))
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
			execute("domain.resource.update", key, request)
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
