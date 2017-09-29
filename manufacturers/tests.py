
from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse

from devices.models import Manufacturer
from users.models import Lageruser


class ManufacturerTests(TestCase):
    def setUp(self):
        '''method for setting up a testing environment'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_manufacturer_creation(self):
        '''method for testing the functionality of creating a manufacturer'''
        manufacturer = mommy.make(Manufacturer) # creating an instance of Manufacturer
        self.assertTrue(isinstance(manufacturer, Manufacturer))
        self.assertEqual(manufacturer.__unicode__(), manufacturer.name)

        # testing the methods of creating absolute- and edit-url
        self.assertEqual(manufacturer.get_absolute_url(),
                         reverse('manufacturer-detail', kwargs={'pk': manufacturer.pk}))
        self.assertEqual(manufacturer.get_edit_url(), reverse('manufacturer-edit', kwargs={'pk': manufacturer.pk}))

    def test_manufacturer_list(self):
        '''method for testing the presentation and reachability of the manufacturer-list-view for several pages'''
        manufacturers = mommy.make(Manufacturer, _quantity=40) # creating 40 instances of Manufacturer
        url = reverse("manufacturer-list")

        # testing response of manufacturer-list-page
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # testing the display of only 30 elements of the response on one page and the distribution of the remaining
        # results on the second page
        self.assertEqual(len(resp.context["manufacturer_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        # testing response of second page of manufacturer-list
        url = reverse("manufacturer-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_manufacturer_detail(self):
        '''method for testing the reachability of the detail-view of the chosen manufacturer'''
        manufacturer = mommy.make(Manufacturer)
        manufacturers = Manufacturer.objects.all()
        manufacturer = manufacturers[0]

        # testing response of detail-view of first manufacturer in list of all manufacturers
        url = reverse("manufacturer-detail", kwargs={"pk": manufacturer.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_manufacturer_add(self):
        '''method for testing the functionality of adding a manufacturer'''
        manufacturer = mommy.make(Manufacturer)
        url = reverse("manufacturer-add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_manufacturer_edit(self):
        '''method for testing the functionality of editing a manufacturer'''
        manufacturer = mommy.make(Manufacturer)
        manufacturers = Manufacturer.objects.all()
        manufacturer = manufacturers[0]
        url = reverse("manufacturer-edit", kwargs={"pk": manufacturer.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_manufacturer_delete(self):
        '''method for testing the functionality of deleting a manufacturer'''
        manufacturer = mommy.make(Manufacturer)
        manufacturers = Manufacturer.objects.all()
        manufacturer = manufacturers[0]
        url = reverse("manufacturer-edit", kwargs={"pk": manufacturer.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)