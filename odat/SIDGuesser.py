#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .OracleDatabase import OracleDatabase
from time import sleep
from itertools import product
import logging, string
from .Tnscmd import Tnscmd
from .Constants import *
from .Utils import stringToLinePadded

class SIDGuesser (OracleDatabase):
	'''
	SID guesser
	'''
	def __init__(self, args, SIDFile, timeSleep=0):
		'''
		Constructor
		'''
		logging.debug("SIDGuesser object created")
		OracleDatabase.__init__(self,args)
		self.SIDFile = SIDFile
		self.sids = []
		self.valideSIDS = []
		self.baroff = args['baroff']
		self.args['SYSDBA'] = False
		self.args['SYSOPER'] = False
		self.timeSleep = timeSleep
		self.NO_GOOD_SID_STRING_LIST = [
				"listener does not currently know of service requested",
				"listener does not currently know of SID",
				"connection to server failed",
				"timeout occurred",
				"could not hand off client connection",
				"destination host unreachable"
		]

	def getValidSIDs(self):
		'''
		return a list containing valid sids found
		'''
		return self.valideSIDS

	def appendValideSID (self, sid):
		'''
		Append to self.valideSIDS a new DIS if no in the list
		'''
		if sid not in self.valideSIDS:
			self.valideSIDS.append(sid)

	def __loadSIDsFromFile__(self):
		'''
		return list containing SIDS
		'''
		sids = []
		logging.info('Load SIDS stored in the {0} file'.format(self.SIDFile))
		f = open(self.SIDFile)
		for l in f:
			sids.append(l.replace('\n','').replace('\t',''))
		f.close()
		return sorted(sids)

	def __testIfAGoodSID__(self):
		'''
		Test if it is a good SID
		Return status of the connection
		'''
		no_good_sid_found = False
		self.args['serviceName'] = None
		self.__generateConnectionString__(username=self.__generateRandomString__(nb=15), password=self.__generateRandomString__(nb=5))
		logging.debug("Try to connect with the {0} SID ({1})".format(self.args['sid'], self.args['connectionStr']))
		status = self.connection()
		if self.__needRetryConnection__(status) == True: 
			status = self.__retryConnect__(nbTry=4)
		if status != None :
			for aNoGoodString in self.NO_GOOD_SID_STRING_LIST:
				if aNoGoodString in str(status):
					no_good_sid_found = True
					break
			if no_good_sid_found == False:
				self.appendValideSID(self.args['sid'])
				logging.info("'{0}' is a valid SID (Server message: {1})".format(self.args['sid'],str(status)))
				self.args['print'].goodNews(stringToLinePadded("'{0}' is a valid SID. Continue... ".format(self.args['sid'])))
		self.close()
		return status

	def searchKnownSIDs(self):
		'''
		Search valid SIDs THANKS TO a well known sid list
		Return False if connection error.
		Return True if SIDs have been tested.
		'''
		self.args['print'].subtitle("Searching valid SIDs thanks to a well known SID list on the {0}:{1} server".format(self.args['server'], self.args['port']))
		self.sids += self.__loadSIDsFromFile__()
		nb=0
		barpips = len(self.sids)
		dotpips = int((barpips+80)/80)
		self.args['sid'] = None
		logging.info('Start the research')
		if self.baroff:
			print(str(barpips)+' to check.', str(dotpips)+' per dot.')
		else:
			pbar,nb = self.getStandardBarStarted(barpips), 0
		for aSID in self.sids :
			nb += 1
			if self.baroff:
				if 0 == (nb % dotpips):
					print('.', end='')
			else:
				pbar.update(nb)
			self.args['sid'] = aSID
			
			connectionStatus = self.__testIfAGoodSID__()

			sleep(self.timeSleep)
		if not self.baroff:
			pbar.finish()
		return True

	def bruteforceSIDs(self, size=4, charset=string.ascii_uppercase):
		'''
		Bruteforce SID
		'''
		self.args['print'].subtitle("Searching valid SIDs thanks to a brute-force attack on {2} chars now ({0}:{1})".format(self.args['server'], self.args['port'], size))
		nb=0
		barpips = (len(charset) ** size)
		dotpips = int((barpips+80)/80)
		logging.info('Start the research')
		if self.baroff:
			print(str(barpips)+' to check.', str(dotpips)+' per dot.')
		else:
			pbar,nb = self.getStandardBarStarted(barpips), 0
		for aSID in product(list(charset), repeat=size):
			nb +=1
			if self.baroff:
				if 0 == (nb % dotpips):
					print('.', end='')
			else:
				pbar.update(nb)
			self.args['sid'] = ''.join(aSID)

			self.__testIfAGoodSID__()

			sleep(self.timeSleep)
		if not self.baroff:
			pbar.finish()
		return True

	def loadSidsFromListenerAlias(self):
		'''
		Append ALIAS from listener into the SID list to try ALIAS like SID
		'''
		logging.info('Put listener ALIAS into the SID list to try ALIAS like SID')
		tnscmd = Tnscmd(self.args)
		tnscmd.getInformation()
		self.sids += tnscmd.getAlias()

def runSIDGuesserModule(args):
	'''
	Run the SIDGuesser module
	'''
	args['print'].title("Searching valid SIDs")
	sIDGuesser = SIDGuesser(args,args['sids-file'],timeSleep=args['timeSleep'])
	if args['no-alias-like-sid'] == False : sIDGuesser.loadSidsFromListenerAlias()
	sIDGuesser.searchKnownSIDs()
	for aSIDSize in range(args['sids-min-size'], args['sids-max-size']+1):
		sIDGuesser.bruteforceSIDs(size=aSIDSize, charset=args['sid-charset'])
	validSIDsList = sIDGuesser.getValidSIDs()
	if validSIDsList == []:
		args['print'].badNews("FAIL - Did not find a valid SID".format(args['server'], args['port']))
	else :
		args['print'].goodNews("SUCCESS - SID(s) found on the {0}:{1} server: {2}".format(args['server'], args['port'], ','.join(validSIDsList)))
	return validSIDsList


