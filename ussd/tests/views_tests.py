from django.test import TestCase




        """
        self.ussd_session = USSDSession.objects.create(
           #probably setup by us or the USSD gateway
           transaction_id='1',

           #reusing existing connection
           connection="1234567",

           #user will probably make a choice between 1 or n
           ussd_request_string='1',

           current_menu_item=self.menu_item,
           #setting xform Node to None
           current_xform=None,
           submission = None,
           xform_step = 1
               )
        """
        """
        #self.ussd_session = USSDSession.objects.create(transaction_id='1', connection='1234567', \
        #                                              ussd_request_string='hello rapidsms', current)
        #self.client = Client()
        c = Client()
        #s = self.client.session
        response = c.post('ussd/')
        self.assertEqual(response.status_code, 302)
        """

"""

    def testNoExplosions(self):
        client = Client()
        # No menu in the DB, this should still return something
        url = reverse('ussd.views.ussd')
        print "url is %s" % url
        response = client.get(reverse('ussd.views.ussd'), {\
            'transactionId':'foo', \
            #'transactionTime':'20110101(T)01:01:01',
            'msisdn':Connection.objects.create(backend=self.backend,identity="1",contact=self.contact),
            'ussdServiceCode':'300',
            'ussdRequestString':'',
        })
        print "reponse is %s" % response.content
        self.assertEqual('responseString=%s&action=end' % urllib.quote('Your session has ended. Thank you.'), response.content)
"""