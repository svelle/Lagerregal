import os.path

from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse

from devices.models import Device, Template, Note
from users.models import Lageruser
from network.models import IpAddress


class DeviceTests(TestCase):

    def setUp(self):
        '''method for setting up a client for testing'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_device_creation(self):
        '''method for testing the functionality of creating a new device'''
        # creating an instance of Device and testing if created instance is instance of Device
        device = mommy.make(Device)
        self.assertTrue(isinstance(device, Device))

        # testing naming
        self.assertEqual(device.__unicode__(), device.name)

        # testing creation of absolute and relative url
        self.assertEqual(device.get_absolute_url(), reverse('device-detail', kwargs={'pk': device.pk}))
        self.assertEqual(device.get_edit_url(), reverse('device-edit', kwargs={'pk': device.pk}))

    def test_device_list(self):
        '''method for testing the presentation and reachability of the list of devices over several pages'''
        devices = mommy.make(Device, _quantity=40)

        # testing if loading of device-list-page was successful (statuscode 2xx)
        url = reverse("device-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # testing the presentation of only 30 results of query on one page
        self.assertEqual(len(resp.context["device_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        # testing the successful loading of second page of device-list (statuscode 2xx)
        url = reverse("device-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_device_detail(self):
        '''method for testing the reachability of existing devices'''
        # querying all devices and choose first one to test
        device = mommy.make(Device)
        devices = Device.objects.all()
        device = devices[0]

        # test successful loading of detail-view of chossen device (first one, statuscode 2xx)
        url = reverse("device-detail", kwargs={"pk": device.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_device_add(self):
        '''method for testing adding a device'''
        device = mommy.make(Device)

        # testing successful loading of device-page of added device (statuscode 2xx)
        url = reverse("device-add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_device_edit(self):
        '''method for testing the functionality of editing a device'''
        device = mommy.make(Device)

        # querying all devices and choose first one
        devices = Device.objects.all()
        device = devices[0]

        # testing successful loading of edited device-detail-page (statuscode 2xx)
        url = reverse("device-edit", kwargs={"pk": device.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_device_delete(self):
        '''method for testing the functionality of deleting a device'''
        device = mommy.make(Device)

        # querying all devices and choose first one
        devices = Device.objects.all()
        device = devices[0]

        # !!!! there should be no device-detail-view -> have to test the loading ao device-list!!!!
        # testing successful loading of device-page after deletion (statuscode 2xx)
        url = reverse("device-edit", kwargs={"pk": device.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_device_archive(self):
        '''testing movement of device to archive'''
        device = mommy.make(Device)

        # querying all devices and choose first one
        devices = Device.objects.all()
        device = devices[0]

        # testing successful loading of device-archive-page (statuscode 3xx)
        archiveurl = reverse("device-archive", kwargs={"pk": device.pk})
        resp = self.client.post(archiveurl)
        self.assertEqual(resp.status_code, 302)

        url = reverse("device-detail", kwargs={"pk": device.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["device"].archived)

        resp = self.client.post(archiveurl)
        self.assertEqual(resp.status_code, 302)

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["device"].archived)

    def test_device_trash(self):
        '''????'''
        device = mommy.make(Device)
        devices = Device.objects.all()
        device = devices[0]
        trashurl = reverse("device-trash", kwargs={"pk": device.pk})
        resp = self.client.post(trashurl)
        self.assertEqual(resp.status_code, 302)

        url = reverse("device-detail", kwargs={"pk": device.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["device"].trashed)

        resp = self.client.post(trashurl)
        self.assertEqual(resp.status_code, 302)

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["device"].trashed)

    def test_device_inventoried(self):
        '''???'''
        device = mommy.make(Device)
        devices = Device.objects.all()
        device = devices[0]
        url = reverse("device-inventoried", kwargs={"pk": device.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

        url = reverse("device-detail", kwargs={"pk": device.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["device"].inventoried)

    def test_device_bookmark(self):
        '''???'''
        device = mommy.make(Device)
        devices = Device.objects.all()
        device = devices[0]
        bookmarkurl = reverse("device-trash", kwargs={"pk": device.pk})
        url = reverse("device-detail", kwargs={"pk": device.pk})
        resp = self.client.post(bookmarkurl)
        self.assertEqual(resp.status_code, 302)

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.context["device"].trashed)

        resp = self.client.post(bookmarkurl)
        self.assertEqual(resp.status_code, 302)

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["device"].trashed)

    def test_device_ipaddress(self):
        '''???'''
        device = mommy.make(Device)
        ip = IpAddress(address="127.0.0.1")
        ip.save()
        devices = Device.objects.all()
        device = devices[0]
        url = reverse("device-ipaddress", kwargs={"pk": device.pk})
        resp = self.client.post(url, {"ipaddresses": [ip.pk], "device": device.pk})
        self.assertEqual(resp.status_code, 302)

        deviceurl = reverse("device-detail", kwargs={"pk": device.pk})
        resp = self.client.get(deviceurl)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["device"].ipaddress_set.all()), 1)

        url = reverse("device-ipaddress-remove", kwargs={"pk": device.pk, "ipaddress": ip.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

        resp = self.client.get(deviceurl)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["device"].ipaddress_set.all()), 0)


class TemplateTests(TestCase):
    def setUp(self):
        '''method for setting up a test environment'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_template_creation(self):
        '''method for testing functionality of creatinga template'''
        template = mommy.make(Template)
        self.assertTrue(isinstance(template, Template))
        self.assertEqual(template.__unicode__(), template.templatename)
        self.assertEqual(template.get_absolute_url(), reverse('device-list'))

    def test_template_list(self):
        '''method for testing presentation and reachability of list-view of templates'''
        templates = mommy.make(Template, _quantity=40)
        url = reverse("template-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["template_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        url = reverse("template-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_template_add(self):
        '''method for testing functionality of adding a template'''
        template = mommy.make(Template)
        url = reverse("template-add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_template_edit(self):
        '''methof for testing functionality of editing templates'''
        template = mommy.make(Template)
        templates = Template.objects.all()
        template = templates[0]
        url = reverse("template-edit", kwargs={"pk": template.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_template_delete(self):
        '''method for testing functionality of deleting templates'''
        template = mommy.make(Template)
        templates = Template.objects.all()
        template = templates[0]
        url = reverse("template-edit", kwargs={"pk": template.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


class NoteTests(TestCase):
    def setUp(self):
        '''method for setting up a test environment'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_note_creation(self):
        '''method for testing functionality of creating a note'''
        note = mommy.make(Note)
        self.assertTrue(isinstance(note, Note))
        self.assertEqual(note.get_absolute_url(), reverse('device-detail', kwargs={'pk': note.device.pk}))
