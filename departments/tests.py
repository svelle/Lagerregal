from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse

from devices.models import Manufacturer
from users.models import Lageruser

# class DepartmentsTests(TestCase):
#
#     def setUp(self):
#         '''method for setting up a testing environment'''
#         self.client = Client()
#         my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
#         self.client.login(username="test", password="test")
#
#     def test_departments_creation(self):
#         '''method for testing the functionality of creating a department'''
#         # creating an instance of Department and testing if this instance is instance of Department
#         manufacturer = mommy.make(Department)
#         self.assertTrue(isinstance(manufacturer, Manufacturer))
#         self.assertEqual(manufacturer.__unicode__(), manufacturer.name)
#
#         # testing the methods of creating absolute- and edit-url
#         self.assertEqual(manufacturer.get_absolute_url(),
#                          reverse('manufacturer-detail', kwargs={'pk': manufacturer.pk}))
#         self.assertEqual(manufacturer.get_edit_url(), reverse('manufacturer-edit', kwargs={'pk': manufacturer.pk}))