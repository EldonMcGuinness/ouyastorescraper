# -*- coding: utf-8  -*-

## Requires: Py 2.7
## Site should be Mediawiki 1.24.4

# Standard includes
import time, sys, random, re, time, hashlib, json, os, itertools, hashlib, math

# 3rd party includes
import requests
from bs4 import BeautifulSoup

OUYA_API_URL = u'https://devs.ouya.tv/api/v1/apps/'
OUYA_WEB_URL = u'https://www.ouya.tv/game/'
WIKI_URL = u'http://ouyawiki.site/api.php'
WIKI_USERNAME = u'YOURUSERNAME'
WIKI_PASSWORD = u'YOURPASSWORD'
WIKI_COOKIE = u''
WIKI_TOKEN = u''
BOT_USER_AGENT = u'OUYAStoreScraper/1.0'
DEFAULT_OUYA_STORE_CATEGORY = [u'Discover Store Release']

def hashfile(apkName, hasher, blocksize=65536):
	print 'Checking apks/{0}.apk'.format(apkName)
	with open('apks/{0}.apk'.format(apkName), 'rb') as f:
		buf = f.read(blocksize)
		while len(buf) > 0:
			hasher.update(buf)
			buf = f.read(blocksize)
		return hasher.hexdigest()


class FileUploader(object):
	'''
	chunkSize is in bytes, default is 1MB
	'''
	wikiName = None # Name of the image on the wiki
	filename = None # Name of the app on the wiki uuid withoutdots
	extension  = None # Image type
	sourceUrl = None # URL to get the image from
	chunkSize = 1048576
	hash = None # Hash of the data, used in filename on wiki
	filesize = -1
	sourceFileData = None # Raw image data
	editToken = None
	
	def __init__(self, filename, url, token, chunkSize=None):
		self.sourceUrl = url
		self.editToken = token
		self.filename = filename.replace(u'.',u'')
		
		if chunkSize is not None:
			self.chunkSize = chunkSize
		
		self.extension = u'png'

		# Get the image data and create the hash
		self.__readSourceImage()
		
	def __exists(self):
		# Check to see if the image is online

		data = {u'action' : u'query',
				u'prop' : u'imageinfo', 
				u'bot':u'true',
				u'titles' : u'File:{0}'.format(self.wikiName),
				u'format' : u'json'}

		headers = {'User-Agent':BOT_USER_AGENT,
				   'Cookie':WIKI_COOKIE}

		for tries in range(3):
			try:
				response = requests.post(WIKI_URL, data=data, headers=headers)
				break
			except:
				response = None
				time.sleep(2)
				continue

		if response is None:
			return (-1, u'Unable to query the server')
			
		jsonData = response.json()

		# Get just the imageinfo line
		try:
			jsonData = jsonData[u'query'][u'pages'].itervalues().next()
			if u'imageinfo' in jsonData:
				logger(u'Image already exists')
				
				#Trim off the 'File:' prefix
				return (1, jsonData[u'title'][5:])
			else:
				logger(u'Image does not exist')
				return (0, None)
		except:
			logger(u'Unexpected Error: {0}'.format(sys.exc_info()[:2]))
			return (-1, None)

	def __readSourceImage(self):
		headers = {'User-Agent':BOT_USER_AGENT}

		for tries in range(3):
			try:
				response = requests.get(self.sourceUrl, headers=headers)
				break
			except:
				response = None
				time.sleep(2)
				continue

		if response is None:
			return (-1, u'Unable to query the server')

		self.sourceFileData = response.content

		f = open('testImage.png','wb')
		f.write(self.sourceFileData)
		f.close()
		
		self.filesize = len(self.sourceFileData)
		self.hash = hashlib.sha1(self.sourceFileData).hexdigest()
		self.wikiName = u'{0}{1}.{2}'.format(self.filename, self.hash, self.extension)
	
	def upload(self):
		exists = self.__exists()

		if exists[0] == 1:
			return (0,u'No Image Upload Needed',exists[1])
		else:
			logger(u'Uploading Image')

			# Do upload here
			fields = {u'action':u'upload',
					  u'format':u'json',
					  u'bot':u'true',
					  u'filename':self.wikiName,
					  u'filesize':str(self.filesize),
					  u'token':self.editToken}

			files = {u'file': self.sourceFileData}

			headers = {'User-Agent':BOT_USER_AGENT,
					   'Cookie':WIKI_COOKIE}


			for tries in range(3):
				try:
					response = requests.post(WIKI_URL, data=fields, headers=headers, files=files)
					break
				except:
					response = None
					time.sleep(2)
					continue

			if response is None:
				return (-1, u'Unable to query the server')

			jsonData = response.json()

			if u'error' in jsonData:
				return (-1,u'Image Upload [Failed]',None)
			else:
				return (1,u'Image Upload [OK]',self.wikiName)
			
class RedirectPages(object):

	# List of redirect pages to make
	redirects = []
	title = None

	def get(self):
		return self.redirects
	
	def __init__(self,title):
		self.redirects = []
		self.redirects.append(title)
		self.title = title
		self.__generateProperCaseRedirect()
		self.__generateWordVariationRedirects()
		self.__generateCharacterVariationRedirects()
		self.__generateEndStrippedRedirects()
		self.__removeDuplicates()
		self.redirects.remove(title)

	def __removeDuplicates(self):
		cleanedRedirects = []

		# Check for duplicates
		for redirect in self.redirects:
			if redirect not in cleanedRedirects:
				cleanedRedirects.append(redirect)
				
		self.redirects = list(cleanedRedirects)

		
	def __generateProperCaseRedirect(self):
		invalidCapitalWords = (u'A', u'An', u'The', u'For', 
		u'And', u'Nor', u'But', u'Or',
		u'Yet', 'So', u'At', u'By', u'For',
		u'From', u'Of', u'On', u'To',
		u'With', u'Without' )

		titleWords = self.title.split(u' ')

		# Convert all but the first word to the proper case for the redirect page
		count = 0
		for index, titleWord in enumerate(titleWords):
			if count == 0:
				'''skip the first word'''
				count += 1
				continue
				
			for invalidCapitalWord in invalidCapitalWords:
				if titleWord == invalidCapitalWord:
					titleWords[index] = invalidCapitalWord.lower()
			
		# Put together the new title
		redirectFrom = u' '.join(titleWords)
		
		if redirectFrom != self.title:
			self.redirects.append(redirectFrom)
			
	def __generateEndStrippedRedirects(self):
		toStrip = (u'~',u'-',u'=',u'_',u'+')
		redirects = list(self.redirects)
		
		for redirect in redirects:
			stripped = redirect
		
			for char in toStrip:
				if char in redirect[0] or char in redirect[-1]:
					stripped = stripped.strip(char)
			self.redirects.append(stripped)

	def __generateWordVariationRedirects(self):
		wordVariations = ((u' and ', u' & '),
		(u' & ', u' and '),
		(u' vs. ', u' vs '),
		(u' vs ', u' vs. '))
		
		redirects = list(self.redirects)
		
		for redirect in redirects:
			for word in wordVariations:
				if word[0] in redirect:
					self.redirects.append(redirect.replace(word[0],word[1]))
	
	def __generateCharacterVariationRedirects(self):
		charactersVariations = ((u':',u''),
			(u'!', u''),
			(u'\'', u''),
			(u'™', u''),
			(u'®', u''),
			(u'?', u''))
		
		redirects = list(self.redirects)
		
		for redirect in redirects:
			for char in charactersVariations:
				if char[0] in redirect:
					self.redirects.append(redirect.replace(char[0],char[1]))
		
class SoftwareTitle(object):
	'''
	Object to hold title data
	'''
	
	properties = {}	

	def __init__(self,uuid,tags,image,md5sum,platforms):
		global DEFAULT_OUYA_STORE_CATEGORY
		apkName = uuid
		
		try:
			result = self.__getStoreData(uuid)
			if result[0] is not None:
				self.properties = result[0]
				self.properties = self.properties
				self.properties[u'uuidOriginal'] = apkName
				self.properties[u'gameImage'] = image
				self.properties[u'md5sum'] = md5sum
				self.properties[u'categories'] = DEFAULT_OUYA_STORE_CATEGORY + tags
				self.properties[u'platforms'] = platforms
				self.properties[u'downloadUrl'] = self.getDownloadURL()
				self.__fixProperties()
			else:
				raise TypeError(u'invalid data returned')
		
		except TypeError as e:
			logger(u'TypeError Error: {0}'.format(e))
		
		except UnicodeEncodeError as e:
			logger(u'UnicodeEncodeError Error: {0}'.format(e))
		
		except:
			logger(u'Unexpected Error: {0}'.format(sys.exc_info()[:2]))

			
	def setImage(self, imageName):
		self.properties['gameImage'] = imageName
	
	def __str__(self):
		return str(self.properties)
		
	def __repr__(self):
		return unicode(self.properties)
	
	def __getStoreData(self, uuid):
		'''
		Fetch the specific app info
		'''
		global OUYA_API_URL, OUYA_WEB_URL
		jsonData = None
		error = None
		
		try:
			headers = {'User-Agent':BOT_USER_AGENT}

			url = u'{0}{1}'.format(OUYA_API_URL, uuid)
			
			for tries in range(3):
				try:
					response = requests.get(url, headers=headers)
					break
				except:
					response = None
					time.sleep(2)
					continue

			if response is None:
				return (-1, u'Unable to query the server')
				
			jsonData = response.json()

			# Get only the app section
			jsonData = jsonData[u'app']
			
		except TypeError as e:
			jsonData = None
			error = e
			
		return (jsonData, error)
		
	def __fixProperties(self):
		global OUYA_WEB_URL
		
		# Fix the website link
		if self.getProperty(u'website') is not None:
			if u'http://' not in self.getProperty(u'website')[:7].lower() and self.getProperty(u'website') is not None:
				self.properties[u'website'] = u'http://{0}'.format(self.properties[u'website'])
		
		# Clean the ouyaWebsite link
		ouyaLinkSanitizer = (u'!', u'\'', u'"', u':', u';', u'.', u'?', u'(', u')', u'[', u']', u'{', u'}', u',', u'@', u'#', u'%', u'^', u'&', u'*', u'_', u'+', u'=',)
		
		self.properties[u'ouyaWebsite'] = self.getProperty(u'title').replace(u' ',u'-')
		for char in ouyaLinkSanitizer:
			self.properties[u'ouyaWebsite'] = self.getProperty(u'ouyaWebsite').replace(char,u'')
			
		self.properties[u'ouyaWebsite'] = u'{0}{1}'.format(OUYA_WEB_URL, self.properties[u'ouyaWebsite'])
		
		# Clean the description of newlines and '=='
		self.properties[u'description'] = self.properties[u'description'].replace(u'\r\n',u'<br/>')
		self.properties[u'description'] = self.properties[u'description'].replace(u'\n',u'<br/>')
		
		while u'==' in self.properties[u'description']:
			self.properties[u'description'] = self.properties[u'description'].replace(u'==',u'')
			
		# Clean up the titles and text that will be titles
		wikiTitleSanitizer = (u'[',u']',u'{',u'}',u'|',u'#',u'<',u'>',u'#')
		for item in [u'title',u'developer']:
			for char in wikiTitleSanitizer:
				self.properties[item] = self.properties[item].replace(char,u'')
				
		# Sort the categories in alpha order
		self.properties[u'categories'].sort()

		# Sort the platforms in alpha order
		self.properties[u'platforms'].sort()
		
		# Check if the developer is the same as the title, if so then we need to change the name and make an disambiguous page
		if self.properties[u'developer'] == self.properties[u'title']:
			self.properties[u'ambiguous'] = self.properties[u'developer']
			self.properties[u'developer'] = u'{0} (developer)'.format(self.properties[u'developer'])
			self.properties[u'title'] = u'{0} (game)'.format(self.properties[u'title'])
	
		
	def toWikitext(self):
		global OUYA_API_URL
	
		try:

			entry = u'<!-- OUYASTOREBOT TITLE INFORMATION START -->'
			entry += u'{{GameInfoBox\n'
			entry += u'|gameImage={}\n'.format(self.getProperty(u'gameImage'))
			
			if u' (developer)' in self.getProperty(u'developer'):
				entry += u'|developer={0}{1}{2}\n'.format(self.getProperty(u'developer'),u'{{!}}',self.getProperty(u'developer').replace(u' (developer)',u''))
			else:
				entry += u'|developer={0}\n'.format(self.getProperty(u'developer'))

			entry += u'|email={0}\n'.format(self.getProperty(u'supportEmailAddress'))
			entry += u'|website={0}\n'.format(self.getProperty(u'website'))
			entry += u'|ouyaWebsite={0}\n'.format(self.getProperty(u'ouyaWebsite'))
			entry += u'|version={0}\n'.format(self.getProperty(u'versionNumber'))
			entry += u'|platforms={0}\n'.format(', '.join(self.getProperty(u'platforms')))
			entry += u'|contentRating={0}\n'.format(self.getProperty(u'contentRating'))
			entry += u'|ratingAverage={0}\n'.format(self.getProperty(u'ratingAverage'))
			entry += u'|ratingCount={0}\n'.format(self.getProperty(u'ratingCount'))
			entry += u'|apkName={0}\n'.format(self.getProperty(u'uuidOriginal'))
			entry += u'|downloadUrl={0}\n'.format(self.getProperty('downloadUrl'))
			entry += u'|premium={0}\n'.format(self.getProperty(u'premium'))
			
			if self.getProperty(u'promotedProduct') is not None:
				entry += u'|price={:.2f}\n'.format(float(self.getProperty(u'promotedProduct')[u'originalPrice']))
				entry += u'|salePercent={0}\n'.format(self.getProperty(u'promotedProduct')[u'percentOff'])
				entry += u'|salePrice={:.2f}\n'.format(float(self.getProperty(u'promotedProduct')[u'localPrice']))
			else:
				entry += u'|price=\n'
				entry += u'|salePercent=0\n'
				entry += u'|salePrice=\n'
				
			entry += u'|description={0}\n'.format(self.getProperty(u'description'))
			entry += u'}}\n'

			#convert the categories into a string
			for category in self.getProperty(u'categories'):
				entry += u'[[Category:{0}]]'.format(category)

			if self.getProperty(u'promotedProduct') is not None:
				if int(self.getProperty(u'promotedProduct')[u'percentOff']) > 0:
					entry += u'[[Category:On Sale]]'
				
			entry += u'<!-- OUYASTOREBOT TITLE INFORMATION STOP -->'

		except:
			e = sys.exc_info()[:2]
			logger(u'Unxpected Error Creating wikiText: {0}'.format(e))
			entry = None
			

		return entry
	
	def getProperty(self, name):
		try:
			return self.properties[name]
		except KeyError:
			return None

	def generateDownloadBar(self, done, total, len):
		percentDone = float(done)/float(total)

		doneBarCount = int(math.floor(len*percentDone))
		leftBarCount = int(len-doneBarCount)

		return '{0}MB/{1}MB [{2}{3}]'.format(format(round(float(done)/(1024*1024*1.0),2),'.2f'), round(float(total)/(1024*1024*1.0),2), '#'*doneBarCount, ' '*leftBarCount)

	def downloadAPK(self, url, apkName):

		spinner = itertools.cycle(['|','/','-','\\'])
		print 'Downloading: {0}'.format(url)
		r = requests.get(url, stream=True)
		
		with open('apks/{0}.apk'.format(apkName), 'wb') as f:
			totalSize = r.headers['content-length']
			sizeDownloaded = 0
			chunkSize = 1024
			for chunk in r.iter_content(chunk_size=chunkSize): 
				sys.stdout.write('{0}\r'.format(self.generateDownloadBar(sizeDownloaded,totalSize,20)))
				sys.stdout.flush()
				if chunk: # filter out keep-alive new chunks
					f.write(chunk)
				sizeDownloaded += chunkSize


	def getDownloadURL(self):
		'''
		Gets the download URL 
		'''
		global OUYA_API_URL
		jsonData = None
		resonse = None
		
		headers = {'User-Agent':BOT_USER_AGENT}

		logger(u'Fetching {0}{1}/download\n'.format(OUYA_API_URL, self.getProperty(u'uuidOriginal')))

		for tries in range(3):
			try:
				response = requests.get(u'{0}{1}/download'.format(OUYA_API_URL, self.getProperty(u'uuidOriginal')), headers=headers)
				break
			except:
				response = None
				time.sleep(2)
				continue

		if response is None:
			return ''

		jsonData = response.json()

		try:
			return jsonData[u'app'][u'downloadLink']
		except:
			try:
				return ''
			except:
				return ''

def __getOUYAStoreCatalog():
	'''
	Catalog URL 
	'''
	global OUYA_API_URL
	jsonData = None
	error = None
	
	headers = {'User-Agent':BOT_USER_AGENT}
	
	for tries in range(3):
		try:
			response = requests.get(OUYA_API_URL, headers=headers)
			break
		except:
			response = None
			time.sleep(2)
			continue

	if response is None:
		return (-1, u'Unable to query the server')

	jsonData = response.json()
		
	return (jsonData, error)

def __getEditToken():
	#print u'Getting Edit Token'
	result = None

	data = {u'action' : u'query',
			u'prop' : u'info|revisions', 
			u'intoken' : u'edit',
			u'bot':u'true',
			u'rvprop' : u'timestamp',
			u'titles' : u'TEST_GAME',
			u'format' : u'json'}

	headers = {'User-Agent':BOT_USER_AGENT,
			   'Cookie':WIKI_COOKIE}

	for tries in range(3):
		try:
			response = requests.post(WIKI_URL, data=data, headers=headers)
			break
		except:
			response = None
			time.sleep(2)
			continue

	if response is None:
		return (-1, u'Unable to query the server')	

	jsonData = response.json()

	# Get only the edit token
	jsonData = jsonData[u'query'][u'pages'].itervalues().next()[u'edittoken']
	
	return jsonData

def __putDisambiguationPage(softwareTitle, tries=0):

	if tries > 3:
		return (-1,u'Too Many Retries')
		
	originalPageData = __getSoftwareTitlePage(softwareTitle.getProperty(u'ambiguous'), softwareTitle.getProperty(u'uuidOriginal'))
	
	originalMatch = re.search(r'<!-- OUYASTOREBOT DISAMBIGUATION INFORMATION START -->\s*(?P<data>.+)\s*<!-- OUYASTOREBOT DISAMBIGUATION INFORMATION STOP -->', originalPageData, re.MULTILINE|re.DOTALL)

	# Create the new list of disambiguous pages
	newPageData =  u'<!-- OUYASTOREBOT DISAMBIGUATION INFORMATION START -->'
	newPageData += u'\'\'\'{{ARTICLEPAGENAME}}\'\'\' may refer to:\n'
	newPageData += u'* [[{0}]]\n'.format(softwareTitle.getProperty(u'title'))
	newPageData += u'* [[{0}]]\n'.format(softwareTitle.getProperty(u'developer'))
	newPageData += u'[[Category:Disambiguation Page]]<!-- OUYASTOREBOT DISAMBIGUATION INFORMATION STOP -->'
	
	if originalMatch is not None:
		newPageData = u'{0}{1}{2}'.format(originalPageData[:originalMatch.start()],newPageData,originalPageData[originalMatch.end():])
	
	if originalPageData == newPageData:
		return (0, u'No Update Needed')

	logger(u'Putting Disambiguation Page {0}'.format(__encode_obj(softwareTitle.getProperty(u'ambiguous'))))
	
	data = {u'format':u'json',
			u'action':u'edit',
			u'title':__encode_obj(softwareTitle.getProperty(u'ambiguous')),
			u'summary':u'Autoupdated',
			u'bot':u'true',
			u'text':__encode_obj(newPageData),
			u'token':__getEditToken()}
		
	headers = {'User-Agent':BOT_USER_AGENT,
			   'Cookie':WIKI_COOKIE}

	for tries in range(3):
		try:
			response = requests.post(WIKI_URL, data=data, headers=headers)
			break
		except:
			response = None
			time.sleep(2)
			continue

	if response is None:
		return (-1, u'Unable to query the server')
				
	jsonData = response.json()

	# Get the result
	jsonData = jsonData[u'edit'][u'result']

	if jsonData == u'Success':
		return (1, u'Success')
	else:
		return (-1, u'Error')
		
def __putDeveloperPage(softwareTitle):
	originalPageData = __getSoftwareTitlePage(softwareTitle.getProperty(u'developer'), softwareTitle.getProperty(u'uuidOriginal'))
	
	originalMatch = re.search(r'<!-- OUYASTOREBOT DEVELOPER INFORMATION START -->\s*(?P<data>.+)\s*<!-- OUYASTOREBOT DEVELOPER INFORMATION STOP -->', originalPageData, re.MULTILINE|re.DOTALL)
	
	if originalMatch is not None:
		titles = originalMatch.group(u'data').split('\n')
	else:
		titles = []

	try:
		# Remove the title
		titles.remove(u'== Titles ==')
		titles.remove(u'[[Category:Developers]]')
	except:
		# Title did not exist
		#print u'Title missing'
		pass

	# Strip away the '* ' wiki prefix
	for index, title in enumerate(titles):
		
		title = title.lstrip(u'* ')
		title = title.rstrip(u'\n')
		titles[index] = title.strip(u'[]')
		
	# See if the link already is in the page, if not then append it
	if u' (game)' in softwareTitle.getProperty(u'title'):
		disambiguousTitle = u'{0}|{1}'.format(softwareTitle.getProperty(u'title'),softwareTitle.getProperty(u'title').replace(u' (game)',u''))
		
		'''
		Try to remove the actual app name from the list if it already exists.
		This will only be needed if an app and developer have the same name and
		had an entry prior to disambiguation.
		'''
		try:
			titles.remove(softwareTitle.getProperty(u'title'))
		except ValueError as e:
			pass
		
		if disambiguousTitle not in titles:
			titles.append(disambiguousTitle)
	else:
		if softwareTitle.getProperty(u'title') not in titles:
			titles.append(softwareTitle.getProperty(u'title'))

	tempTitles = []

	# Check for duplicates
	for title in titles:
		if title not in tempTitles:
			tempTitles.append(title)
		
	titles = list(tempTitles)
	tempTitles = None
	
	# Sort the titles by name
	titles.sort()
	
	# Create the new list of apps/games
	newPageData =  u'<!-- OUYASTOREBOT DEVELOPER INFORMATION START -->'
	newPageData += u'== Titles ==\n'
	for title in titles:
		newPageData += u'* [[{0}]]\n'.format(title)
	newPageData +=  u'[[Category:Developers]]<!-- OUYASTOREBOT DEVELOPER INFORMATION STOP -->'
	
	if originalMatch is not None:
		newPageData = u'{0}{1}{2}'.format(originalPageData[:originalMatch.start()],newPageData,originalPageData[originalMatch.end():])
	
	#print u'Developer Page Data {0}\n'.format(newPageData)
	if originalPageData == newPageData:
		return (0, u'No Update Needed')

	logger(u'Putting Developer Page {0}'.format(__encode_obj(softwareTitle.getProperty(u'uuidOriginal'))))
	
	data = {u'format':u'json',
			u'action':u'edit',
			u'title':__encode_obj(softwareTitle.getProperty(u'developer')),
			u'summary':u'Autoupdated',
			u'bot':u'true',
			u'text':__encode_obj(newPageData),
			u'token':__getEditToken()}
		
	headers = {'User-Agent':BOT_USER_AGENT,
			   'Cookie':WIKI_COOKIE}

	for tries in range(3):
		try:
			response = requests.post(WIKI_URL, data=data, headers=headers)
			break
		except:
			response = None
			time.sleep(2)
			continue

	if response is None:
		return (-1, u'Unable to query the server')

	jsonData = response.json()

	# Get the result
	jsonData = jsonData[u'edit'][u'result']

	if jsonData == u'Success':
		return (1, u'Success')
	else:
		return (-1, u'Error')

def __putRedirectPages(title):
	redirects = RedirectPages(title).get()
	
	if len(redirects) == 0:
		logger(u'No redirects needed')
	else:
		for redirect in redirects:
			data = {u'format':u'json',
					u'action':u'edit',
					u'title':__encode_obj(redirect),
					u'summary':u'Autoupdated',
					u'bot':u'true',
					u'text':__encode_obj(u'#REDIRECT [[{0}]]'.format(title)),
					u'token':__getEditToken()}

			headers = {'User-Agent':BOT_USER_AGENT,
					   'Cookie':WIKI_COOKIE}

			for tries in range(3):
				try:
					response = requests.post(WIKI_URL, data=data, headers=headers)
					break
				except:
					response = None
					time.sleep(2)
					continue

			if response is None:
				return (-1, u'Unable to query the server')

			jsonData = response.json()

			# Get the result
			jsonData = jsonData[u'edit'][u'result']

def __encode_obj(in_obj):

	def encode_list(in_list):
		out_list = []
		for el in in_list:
			out_list.append(__encode_obj(el))
		return out_list

	def encode_dict(in_dict):
		out_dict = {}
		for k, v in in_dict.iteritems():
			out_dict[k] = __encode_obj(v)
		return out_dict

	if isinstance(in_obj, unicode):
		return in_obj.encode('utf-8')
	elif isinstance(in_obj, list):
		return encode_list(in_obj)
	elif isinstance(in_obj, tuple):
		return tuple(encode_list(in_obj))
	elif isinstance(in_obj, dict):
		return encode_dict(in_obj)

	return in_obj	
	
def __getSoftwareTitlePage(title, uuidOriginal):
	logger(u'Getting Page: {0}'.format(__encode_obj(uuidOriginal)))

	data = {u'action':u'query', 
			u'prop':u'revisions',
			u'rvprop':u'content',
			u'bot':u'true',
			u'format':u'json',
			u'titles':__encode_obj(title)}

	headers = {'User-Agent':BOT_USER_AGENT,
			   'Cookie':WIKI_COOKIE}

	for tries in range(3):
		try:
			response = requests.post(WIKI_URL, data=data, headers=headers)
			break
		except:
			response = None
			time.sleep(2)
			continue

	if response is None:
		return (-1, u'Unable to query the server')
	
	jsonData = response.json()

	if u'revisions' in jsonData[u'query'][u'pages'].itervalues().next().keys():
		jsonData = jsonData[u'query'][u'pages'].itervalues().next()[u'revisions'][0][u'*']
	else:
		jsonData = u''
		
	logger(u'Getting Page [OK]')
	
	return jsonData
	

def __login(tries=0):
	global WIKI_COOKIE, WIKI_TOKEN, BOT_USER_AGENT, WIKI_USERNAME, WIKI_PASSWORD

	if tries > 3:
		return (-1, u'Could not login')

	result = None
	response = None

	for tries in range(3):
		try:

			data = {u'action' : u'login',
                                        u'lgname' : WIKI_USERNAME,
                                        u'lgpassword' : WIKI_PASSWORD,
					u'bot':u'true',
					u'lgtoken' : WIKI_TOKEN,
					u'format' : u'json'}

			headers = {'User-Agent':BOT_USER_AGENT,
					   'Cookie':WIKI_COOKIE}

			response = requests.post(WIKI_URL, data=data, headers=headers)

			jsonData = response.json()

			# Get the login section and results
			jsonData = jsonData[u'login']
			result = jsonData[u'result']

			#If something does not match then try again
			if 	result != u'Success' and (WIKI_COOKIE != response.headers[u'set-cookie'] or \
				WIKI_TOKEN != jsonData[u'token']):

				WIKI_COOKIE = response.headers[u'set-cookie']
				WIKI_TOKEN = jsonData[u'token']
				continue
			else:
				break
		except:
			response = None
			time.sleep(2)
			continue

	if response is None:
		return (-1, u'Unable to query the server')

	if result == u'Success':
		return (1, u'Success')
	else:
		return (-1, u'Unknown Error')

def logger(text, truncate=False):
	text += u'\n'
	print(text)
	
	if truncate:
		f = open('errors.log', 'wb')
	else:
		f = open('errors.log', 'ab')
	f.write(text)
	f.close()

def die():
	logger(u'Finished Time: {0}'.format(time.strftime(u'%c')))
	exit()

def __putNewSoftwareTitlePage(softwareTitle):
	
	originalPageData = __getSoftwareTitlePage(softwareTitle.getProperty(u'title'), softwareTitle.getProperty(u'uuidOriginal'))
	
	originalMatch = re.search(r'<!-- OUYASTOREBOT TITLE INFORMATION START -->\s*(?P<data>.+)\s*<!-- OUYASTOREBOT TITLE INFORMATION STOP -->', originalPageData, re.MULTILINE|re.DOTALL)

	if originalMatch is not None:
		# If the page exists on the wiki
		originalMatchData = u'{0}'.format(originalMatch.group(u'data'))
	else:
		# If the page does not exist on the wiki
		originalMatchData = u''

	# Create the new page data
	newPageData = softwareTitle.toWikitext()
	newMatch = re.search(r'<!-- OUYASTOREBOT TITLE INFORMATION START -->\s*(?P<data>.+)\s*<!-- OUYASTOREBOT TITLE INFORMATION STOP -->', newPageData, re.MULTILINE|re.DOTALL)

	newMatchData =  u'{0}'.format(newMatch.group(u'data'))
	
	# Compare the originalPageData section to the newpage section
	if newMatchData == originalMatchData:
		return (0, u'No Update Needed')
	
	#print u'Original Len: {0}'.format(len(originalPageData))
	#print u'New Len: {0}'.format(len(newPageData))
	
	if originalMatch is not None:
		#print u'Boundaries [{0}|{1}]'.format(originalMatch.start(),originalMatch.end())
		#print u'Boundaries2 [{0}|{1}]'.format(originalPageData[:originalMatch.start()],originalPageData[originalMatch.end():])
		newPageData = u'{0}{1}{2}'.format(originalPageData[:originalMatch.start()],newPageData,originalPageData[originalMatch.end():])

	#print u'Original Len: {0}'.format(len(originalPageData))
	#print u'New Len: {0}'.format(len(newPageData))
		
	data = {u'format':u'json',
			u'action':u'edit',
			u'title':__encode_obj(softwareTitle.getProperty(u'title')),
			u'summary':u'Autoupdated',
			u'bot':u'true',
			u'text':__encode_obj(newPageData),
			u'token':__getEditToken()}

	headers = {'User-Agent':BOT_USER_AGENT,
			   'Cookie':WIKI_COOKIE}

	for tries in range(3):
		try:
			response = requests.post(WIKI_URL, data=data, headers=headers)
			break
		except:
			response = None
			time.sleep(2)
			continue

	if response is None:
		return (-1, u'Unable to query the server')

	jsonData = response.json()

	# Get the result
	jsonData = jsonData[u'edit'][u'result']

	if jsonData == u'Success':
		return (1, u'Success')
	else:
		return (-1, u'Error')
	
def main():
	
	# Holds the Catelog results
	catalog = None
	successfulProcesses = 0
	failedProcesses = 0
	
	logger(u'Start Time: %s'  %  time.strftime(u'%c'), truncate=True)
	
	#login to the wiki
	try:
		logger(u'Logging In...')
		result = __login()
		
		if result[0] != 1:
			logger(u'Logging In [Failed]')
			die()
		
		logger(u'Logging In [{0}]'.format(result[1]))
	except:
		logger(u'Logging In [Failed]')
		logger(u'Unexpected Error: {0}'.format(sys.exc_info()[:2]))
		die()
	
	# Get the current OUYA Discover Store Catalog
	try:
		logger(u'Getting Catalog...')
		catalog = __getOUYAStoreCatalog()
		catalog = catalog[0][u'apps']
		logger(u'Catalog Fetch [OK]')
	except:
		logger(u'Catalog Fetch [Failed]')
		logger(u'Unexpected Error: {0}'.format(sys.exc_info()[:2]))
	
	'''
	tempjson = u'[{"uuid":"com.StrangeGamesStudios.TinasToyFactory","title":"Tina\'s Toy Factory","version":"c49a941b-9af3-4ecd-a5f3-4cb7111c6b96","tags":["Multiplayer","Puzzle/Trivia","Sim/Strategy","Kids List"],"mainImageFullUrl":"https://www.filepicker.io/api/file/8C3IpuNIRPCVAMm4UURj","mainImageFullUrl":"https://www.filepicker.io/api/file/8C3IpuNIRPCVAMm4UURj","md5sum":"58c2df7b80558efafe4f3c29689d9b3e","premium":false,"released":"2015-03-12T00:16:16Z","updated":"2015-03-20T16:02:23Z","rating":{"count":13,"average":3.54}}]'
	catalog = json.loads(tempjson)
	'''
	
	for item in catalog:
		logger(u'==========================================================')

		# Convert the catalog item to a software titles
		softwareTitle = SoftwareTitle(item[u'uuid'],item[u'tags'],item[u'mainImageFullUrl'],item[u'md5sum'], item[u'availableDevices'])

		try:
			# See if the file we have now is the same md5sum
			currentHash = None

			try:
				currentHash = hashfile(softwareTitle.getProperty(u'uuidOriginal'), hashlib.md5())
			except Exception as e:
				print 'Could not check hash of file'
				pass

			if currentHash != softwareTitle.properties['md5sum'] and softwareTitle.properties['md5sum'] != None :
				print 'Compare Hash: \n{0}\n{1}'.format(currentHash,softwareTitle.properties['md5sum'])

				# Download the apk
				softwareTitle.downloadAPK(url=str(softwareTitle.getProperty(u'downloadUrl')), apkName=softwareTitle.getProperty(u'uuidOriginal'))

		except Exception as e:
			print 'Download Failed'
			print e
			pass

		# Create DisambiguationPage & Redirects
		if softwareTitle.getProperty(u'ambiguous') is not None:
			try:
				logger(u'Creating Disambiguation Pages...')
				result = __putDisambiguationPage(softwareTitle)

				# If we made a page then create redirects
				if result[0] == 1:
					__putRedirectPages(softwareTitle.getProperty(u'ambiguous'))
					
				logger(u'Creating Disambiguation Pages [OK]')
			except:
				logger(u'Creating Disambiguation Pages [Failed]')
				logger(u'Unexpected Error: {0}'.format(sys.exc_info()[:2]))
			
		# Create title link on Developer page and redirects
		try:
			logger(u'Creating Developer Page...')
			result = __putDeveloperPage(softwareTitle)

			# If we made a page then create redirects
			if result[0] == 1:			
				__putRedirectPages(softwareTitle.getProperty(u'developer'))
			
			logger(u'Creating Developer Page [{0}]'.format(result[1]))
		except:
			logger(u'Creating Developer Page [Failed]')
			logger(u'Unexpected Error: {0}'.format(sys.exc_info()[:2]))

		# Get ready to upload the image
		try:
			logger(u'Getting Title Image...')
			uploader = FileUploader(softwareTitle.getProperty(u'uuidOriginal'),softwareTitle.getProperty(u'gameImage'), __getEditToken())
			result = uploader.upload()

			if result[0] != -1:
				softwareTitle.setImage(result[2])
			
			logger(u'Getting Title Image [{0}]'.format(result[1]))
		except:
			logger(u'Getting Title Image [Failed]')
			logger(u'Unexpected Error: {0}'.format(sys.exc_info()[:2]))

		# Try to create the application page
		try:
			logger(u'Creating Software Page [{0}]'.format(softwareTitle.getProperty(u'uuidOriginal')))
			result = __putNewSoftwareTitlePage(softwareTitle)
			
			if result[0] == -1:
				__putRedirectPages(softwareTitle.getProperty(u'title'))
			
			logger(u'Creating Software Page [{0}]'.format(result[1]))			
		except:
			logger(u'Creating Software Page [Failed]')
			logger(u'Unexpected Error: {0}'.format(sys.exc_info()[:2]))
			
		logger(u'==========================================================\n\n')
		
		#Wait a minute before we repeat the loop
		time.sleep(random.randint(1,4))

	logger(u'Total Passed Processed Items: {0}'.format(successfulProcesses))
	logger(u'Total Failed Processed Items: {0}'.format(failedProcesses))
		
if __name__ == '__main__':
	main()
	
