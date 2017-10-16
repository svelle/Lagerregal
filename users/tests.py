import os.path

from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse

from users.models import Lageruser


class UserTests(TestCase):

    def setUp(self):
        '''method for setting up a client for testing'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_User_list(self):
        '''method for testing the presentation and reachability of the list of users over several pages'''
        user = mommy.make(Lageruser, _quantity=40)

        # testing if loading of device-list-page was successful (statuscode 2xx)
        url = reverse("user-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # testing the presentation of only 30 results of query on one page
        self.assertEqual(len(resp.context["user_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        # doesn't work
        # # testing the successful loading of second page of device-list (statuscode 2xx)
        # url = reverse("user-list", kwargs={"page": 2, "department":"my"})
        # resp = self.client.get(url)
        # self.assertEqual(resp.status_code, 200)