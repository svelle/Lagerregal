import os.path

from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse

from devices.models import Device
from users.models import Lageruser
#from public import views


class PublicDeviceTests(TestCase):

    def setUp(self):
        '''method for setting up a client for testing'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")
        print self.client

    # def test_PublicDevice_list(self):
    #     '''method for testing the presentation and reachability of the list of public devices over several pages'''
    #     devices = mommy.make(Device, _quantity=40)
    #
    #     # testing if loading of public-device-list-page was successful (statuscode 2xx)
    #     url = reverse("public-device-list")
    #     print url
    #     resp = self.client.get(url)
        #print resp
        # self.assertEqual(resp.status_code, 200)
        #
        # # testing the presentation of only 30 results of query on one page
        # self.assertEqual(len(resp.context["public-device-list"]), 30)
        # self.assertEqual(resp.context["paginator"].num_pages, 2)
#
#         # testing the successful loading of second page of public-device-list (statuscode 2xx)
#         url = reverse("public-device-list", kwargs={"page": 2})
#         resp = self.client.get(url)
#         self.assertEqual(resp.status_code, 200)
#
    # def test_PublicDevice_detail(self):
    #     '''method for testing the reachability of existing public devices'''
    #     # querying all devices and choose first one to test
    #     device = mommy.make(Device)
    #     devices = Device.objects.all()
    #     device = devices[0]
    #
    #     # test successful loading of detail-view of choosen device (first one, statuscode 2xx)
    #     url = reverse("public-device-detail", kwargs={"pk": device.pk})
    #     resp = self.client.get(url)
    #     self.assertEqual(resp.status_code, 200)

