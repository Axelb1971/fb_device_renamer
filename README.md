# fb_device_renamer
Rename devices of a FritzBox to local DNS or host names.

This python script uses Selenium Webdriver to interact with the FritzBox. As browser google chrome is added.

To use the script please add the following modules to your local installed python packages and do a minimal configuration:
1. pip install webdriver-manager selenium dnspython beautifulsoup4
2. rename "fb_device_renamer.ini.template" to "fb_device_renamer.ini"
3. edit "fb_device_renamer.ini" to your needs, e.g. IP FritzBox (FB), FB User, FB password, IP local DNS Server)

After configuration run the script fb_device_renamer.py. This compares and edits the hostnames within the FritzBox to defined names by a local DNS or hosts file.
