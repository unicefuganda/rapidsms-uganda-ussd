from django.db import models

class USSDSession(models.Model):

	# MSISDN; telephone number on SIM card
	mssid = models.CharField(max_length=100):

	#TODO figure out how to map transaction_id to progess steps in script.
	transaction_id = models.CharField(max_length=100):

	