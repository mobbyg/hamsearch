import requests
import ssl
import os.path
import calendar
from datetime import date
import zipfile

# Handles the SSL for websites
ssl._create_default_https_context = ssl._create_unverified_context

# URL to download data from the FCC
dbZip = 'https://data.fcc.gov/download/pub/uls/complete/l_amat.zip'

# Grab the file
theFile = requests.get(dbZip)

# Save the file after we get it
with open('l_amat.zip' , 'wb') as f:
	f.write(theFile.content)


# Extract the files we need. 
# The others are there for future updates.
with zipfile.ZipFile('l_amat.zip' , 'r') as my_zip:
	my_zip.extract('AM.dat' , 'data')
	my_zip.extract('EN.dat' , 'data')
	#my_zip.extract('CO.dat' , 'data')
	#my_zip.extract('HD.dat' , 'data')
	#my_zip.extract('HS.dat' , 'data')
	#my_zip.extract('LA.dat' , 'data')
	#my_zip.extract('SC.dat' , 'data')
	#my_zip.extract('SF.dat' , 'data')
	#my_zip.extract('counts' , 'data')



