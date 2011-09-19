from django.db import models
from rapidsms.models import Contact, Connection



class USSDSession(models.Model):

	# MSISDN; telephone number on SIM card
	mssid = models.ForeignKey(Connection,related_name="messages")

	#TODO figure out how to map transaction_id to progess steps in script.
	transaction_id = models.CharField(max_length=100):
	
	def __unicode__(self):
		return self.mssid
	