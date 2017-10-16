from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse

from devicegroups.models import Devicegroup
from users.models import Lageruser

class DevicegroupTests(TestCase):

    def setUp(self):
        '''method for setting up a client for testing'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_devicegroup_creation(self):
        '''method for testing the functionality of creating a new devicegroup'''
        # creating an instance of Devicegroup and testing if created instance is instance of Devicegroup
        devicegroup = mommy.make(Devicegroup)
        self.assertTrue(isinstance(devicegroup, Devicegroup))

        # testing naming
        self.assertEqual(devicegroup.__unicode__(), devicegroup.name)

        # testing creation of absolute and relative url
        self.assertEqual(devicegroup.get_absolute_url(), reverse('devicegroup-detail', kwargs={'pk': devicegroup.pk}))
        self.assertEqual(devicegroup.get_edit_url(), reverse('devicegroup-edit', kwargs={'pk': devicegroup.pk}))

    def test_device_list(self):
        '''method for testing the presentation and reachability of the list of devicegroups over several pages'''
        devicegroups = mommy.make(Devicegroup, _quantity=40)

        # testing if loading of devicegroup-list-page was successful (statuscode 2xx)
        url = reverse("devicegroup-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # testing the presentation of only 30 results of query on one page
        self.assertEqual(len(resp.context["devicegroup_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        # testing the successful loading of second page of devicegroup-list (statuscode 2xx)
        url = reverse("devicegroup-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_devicegroup_detail(self):
        '''method for testing the reachability of existing devices'''
        # querying all devicegroups and choose first one to test
        devicegroup = mommy.make(Devicegroup)
        devicegroups = Devicegroup.objects.all()
        devicegroup = devicegroups[0]

        # test successful loading of detail-view of chossen device (first one, statuscode 2xx)
        url = reverse("devicegroup-detail", kwargs={"pk": devicegroup.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_devicegroup_add(self):
        '''method for testing adding a devicegroup'''
        devicegroup = mommy.make(Devicegroup)

        # testing successful loading of devicegroup-page of added device (statuscode 2xx)
        url = reverse("devicegroup-add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_devicegroup_edit(self):
        '''method for testing the functionality of editing a devicegroup'''
        devicegroup = mommy.make(Devicegroup)

        # querying all devices and choose first one
        devicegroups = Devicegroup.objects.all()
        devicegroup = devicegroups[0]

        # testing successful loading of edited devicegroup-detail-page (statuscode 2xx)
        url = reverse("devicegroup-edit", kwargs={"pk": devicegroup.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_devicegroup_delete(self):
        '''method for testing the functionality of deleting a devicegroup'''
        devicegroup = mommy.make(Devicegroup)

        # querying all devicegroups and choose first one
        devicegroups = Devicegroup.objects.all()
        devicegroup = devicegroups[0]

        # testing successful loading of devicegroup-page after deletion (statuscode 2xx)
        url = reverse("devicegroup-edit", kwargs={"pk": devicegroup.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)