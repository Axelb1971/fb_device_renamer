#!/usr/bin/python

from webdriver_manager.chrome import ChromeDriverManager # pip install webdriver-manager
from selenium import webdriver # pip install selenium
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import sys
import dns.resolver # pip install dnspython
import dns.reversename
from bs4 import BeautifulSoup # pip install beautifulsoup4  https://www.crummy.com/software/BeautifulSoup/bs4/doc/
import configparser

# exit codes:
# 0: no errors
# 1: FritzBox user mismatch available and config file
# 2: IP address not unique

# log function
def my_log(info, level):
    if (loglevel >= level):
        print(info)


# Initialize
config = configparser.ConfigParser()
config.read('fb_device_renamer.ini')

window_size_x = config.getint("general","window_size_x")
window_size_y = config.getint("general","window_size_y")
implicitlyWait = config.getint("general","implicitlyWait")
networktableWait = config.getint("general","networktableWait")
alertWait = config.getint("general","alertWait")

fbip = config.get("FritzBox","fbip")
fbuser = config.get("FritzBox","fbuser")
fbpasswd = config.get("FritzBox","fbpasswd")

dnsserver = config.get("Hostname_source","dnsserver")

exclude_hosts = config.get("Exclude_hosts","exclude_hosts")

loglevel = config.getint("Logging","loglevel")
my_log("loglevel: {}".format(loglevel),1)

# initialize DNS resolver
my_resolver = dns.resolver.Resolver()
my_resolver.nameservers = [dnsserver]

# initialize webdriver
driver = webdriver.Chrome(ChromeDriverManager().install())

# open FB Website
driver.get('http://'+fbip)
driver.set_window_size(window_size_x, window_size_y)
driver.implicitly_wait(implicitlyWait)

# Testseite aus File, um die Testgeschwindigkeit zu erhöhen
"""with open("page_source.html") as fp:
    soup = BeautifulSoup(fp, 'html.parser')"""

# Login Procedure
# choose user to login
driver.implicitly_wait(3)
dropdown = driver.find_element(By.ID, "uiViewUser")
try:
    dropdown.find_element(By.XPATH, "//option[. = '{}']".format(fbuser)).click()
except NoSuchElementException:
    my_log('fb user isn\'t available',0)
    driver.quit()
    sys.exit(1)

driver.implicitly_wait(implicitlyWait)

my_log('Enter Login',2)

# enter login password
driver.find_element(By.ID, "uiPass").click()
driver.find_element(By.ID, "uiPass").send_keys(fbpasswd)
my_log('Enter Password',1)
driver.find_element(By.ID, "submitLoginBtn").click()

# wait for availability of website navigation & choose lan and network
WebDriverWait(driver,networktableWait).until(EC.visibility_of_element_located((By.ID, "lan"))).click()
WebDriverWait(driver,networktableWait).until(EC.visibility_of_element_located((By.ID, "net"))).click()

# wait for appearence of network list / waiting for passive networklist, because it appears delayed after active network list
WebDriverWait(driver,networktableWait).until(EC.visibility_of_all_elements_located((By.XPATH,'//*[@id="PassiveNetwork"]/div/div[@id="Name"]')))
my_log('aktive / passive Verbindungen sind da',2)

# read complete contentbox to faster analyse content with BeautifulSoup
my_log('contentBox loaded',2)
pageSource = driver.find_element(By.ID, "contentBox").get_attribute("outerHTML")
soup = BeautifulSoup(pageSource, 'html.parser')

# find active and passive device lists
active = soup.find(id="ActiveNetwork")
passive = soup.find(id="PassiveNetwork")

my_log('IPs of active and passive connections stored',2)
act_pas_ips=active.find_all(prefid="ip") + passive.find_all(prefid="ip")

# Auskommentieren, um den gesamten HTML Code in ein File zu schreiben
if (loglevel>=3):
    fileToWrite = open("debug_page_source", "w")
    fileToWrite.write(pageSource)
    fileToWrite.close()

# Auslesen aller aktiven Verbindungen und schreiben in eine Datei für Debugzwecke über selenium und nicht pagesource
if (loglevel>=3):
    active = driver.find_element(By.XPATH,'//*[@id="ActiveNetwork"]')
    fileToWrite = open("debug_active", "w")
    fileToWrite.write(active.get_attribute('outerHTML'))
    fileToWrite.close()

# Auslesen aller passiven Verbindungen und schreiben in eine Datei für Debugzwecke über selenium und nicht pagesource
if (loglevel>=3):
    passive = driver.find_element(By.XPATH,'//*[@id="PassiveNetwork"]')
    fileToWrite = open("debug_passive", "w")
    fileToWrite.write(passive.get_attribute('outerHTML'))
    fileToWrite.close()

my_log('check IPs',2)
# Finden aller IP Adressen in der Geräteliste
hosts_edit_ip = []
hosts_edit_dns = []
for act_pas in act_pas_ips:
    try: 
        ip = act_pas.div.string

        if (len(ip) == 0):
            continue
        
        # IP addresses must be unique, because they are the identifier for devices. Doubled entrys must be corrected before running the script
        for nip in exclude_hosts:
            if (ip == nip):
                break

        if (ip == nip):
            continue

        vpn = act_pas.parent.find(class_="portitem vpn")
        if vpn is not None:
            # no edit button, so nothing to change, skip this IP
            my_log("Skip VPN {}".format(ip),2)
            continue

        for ip_stored in hosts_edit_ip:
            if (ip == ip_stored):
                my_log('IP address is doubled: {}'.format(ip),0)
                driver.quit()
                sys.exit(2)

        # Device name within FritzBox
        name = act_pas.parent.find(prefid="name")['title']

        # DNS resolve IP address
        if (len(ip)>0):
            query_results = my_resolver.resolve(dns.reversename.from_address(ip),'PTR')
            dnsname = query_results[0].to_text().split('.')[0]
            if (dnsname != name and len(dnsname)>0):
                # IP address has a different name in the Fritzbox than in DNS - so change it later
                hosts_edit_ip.append(ip)
                hosts_edit_dns.append(dnsname)
                my_log('edit: IP: {} FB-Name: {} DNS: {}'.format(ip,name,dnsname),2)
            else:
                my_log('no change: IP: {} FB-Name: {} DNS: {}'.format(ip,name,dnsname),2)

    except NoSuchElementException:
        break

# some statistics
my_log('len of Array hosts_edit_ip {}'.format(len(hosts_edit_ip)),2)
my_log('len of Array hosts_edit_dns {}'.format(len(hosts_edit_dns)),2)

# change FritzBox device names to DNS names
for i in range(0,len(hosts_edit_ip),1):
        my_log('rename {} to {}'.format(hosts_edit_ip[i],hosts_edit_dns[i]),1)

        # rename it
        button = driver.find_element(By.XPATH,'//div[@title="{}"]/../../../div/button[@class="icon edit"]'.format(hosts_edit_ip[i]))
        button.click()
        driver.find_element(By.ID, "uiViewDeviceName-input").click()

        # delete device name
        driver.find_element(By.ID, "uiViewDeviceName-input").send_keys(Keys.CONTROL + "a")
        driver.find_element(By.ID, "uiViewDeviceName-input").send_keys(Keys.DELETE)

        # enter DNS name
        driver.find_element(By.ID, "uiViewDeviceName-input").send_keys("{}".format(hosts_edit_dns[i]))
        driver.find_element(By.NAME, "apply").click()

        # after button press it takes a long time to receive an alert that the host is reached via its new name
        WebDriverWait(driver,alertWait).until(EC.alert_is_present())
        driver.switch_to.alert.accept()

        # wait until device table is renewed and available
        if (i < len(hosts_edit_ip)-1):
            WebDriverWait(driver,networktableWait).until(EC.visibility_of_all_elements_located((By.XPATH,'//*[@id="PassiveNetwork"]/div/div[@id="Name"]')))
    

if (len(hosts_edit_ip) == 0):
    my_log('all hosts are already renamed - no change needed',1)

# successful finished
my_log('Finish',1)
driver.quit()
sys.exit(0)