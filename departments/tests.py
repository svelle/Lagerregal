from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse

from users.models import Department
from users.models import Lageruser

class DepartmentTests(TestCase):

    def setUp(self):
        '''method for setting up a testing environment'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_department_list(self):
        '''method for testing the presentation and reachability of the list of departemnts over several pages'''
        department = mommy.make(Department, _quantity=40)

        # testing if loading of department-list-page was successful (statuscode 2xx)
        url = reverse("department-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # testing the presentation of only 30 results of query on one page
        self.assertEqual(len(resp.context["department_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        # testing the successful loading of second page of department-list (statuscode 2xx)
        url = reverse("department-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_department_add(self):
        '''method for testing adding a department'''
        department = mommy.make(Department)

        # testing successful loading of device-page of added device (statuscode 2xx)
        url = reverse("department-add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    # def test_department_edit(self):
    #     '''method for testing the functionality of editing a department'''
    #     department = mommy.make(Department)
    #
    #     # querying all devices and choose first one
    #     departments = Department.objects.all()
    #     department = departments[0]
    #
    #     # testing successful loading of edited department-detail-page (statuscode 2xx)
    #     url = reverse("department-edit", kwargs={"pk": department.pk})
    #     resp = self.client.get(url)
    #     self.assertEqual(resp.status_code, 200)