import os.path

from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse

from devices.models import Device, Manufacturer, Template, Note
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
        device = mommy.make(Device)

        self.assertTrue(isinstance(device, Device))
        self.assertEqual(device.__unicode__(), device.name)
        self.assertEqual(device.get_absolute_url(), reverse('device-detail', kwargs={'pk': device.pk}))
        self.assertEqual(device.get_edit_url(), reverse('device-edit', kwargs={'pk': device.pk}))

    def test_device_list(self):
        '''method for testing the presentation and reachability of the list of devices over several pages'''
        devices = mommy.make(Device, _quantity=40)
        url = reverse("device-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["device_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        url = reverse("device-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_device_detail(self):
        '''method for testing the reachability of existing devices'''
        device = mommy.make(Device)
        devices = Device.objects.all()
        device = devices[0]
        ip = IpAddress(address="127.0.0.1")
        ip.save()
        url = reverse("device-detail", kwargs={"pk": device.pk})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)

    def test_device_add(self):
        '''method for testing adding a device'''
        device = mommy.make(Device)
        url = reverse("device-add")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)

    def test_device_edit(self):
        '''method for testing the functionality of editing a device'''
        device = mommy.make(Device)
        devices = Device.objects.all()
        device = devices[0]
        url = reverse("device-edit", kwargs={"pk": device.pk})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)

    def test_device_delete(self):
        '''method for testing the functionality of deleting a device'''
        device = mommy.make(Device)
        devices = Device.objects.all()
        device = devices[0]
        url = reverse("device-edit", kwargs={"pk": device.pk})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)

    def test_device_archive(self):
        '''????'''
        device = mommy.make(Device)
        devices = Device.objects.all()
        device = devices[0]
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

class ManufacturerTests(TestCase):
    def setUp(self):
        '''method for setting up a testing environment'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_manufacturer_creation(self):
        '''method for testing the functionality of creating a manufacturer'''
        manufacturer = mommy.make(Manufacturer)
        self.assertTrue(isinstance(manufacturer, Manufacturer))
        self.assertEqual(manufacturer.__unicode__(), manufacturer.name)
        self.assertEqual(manufacturer.get_absolute_url(),
                         reverse('manufacturer-detail', kwargs={'pk': manufacturer.pk}))
        self.assertEqual(manufacturer.get_edit_url(), reverse('manufacturer-edit', kwargs={'pk': manufacturer.pk}))

    def test_manufacturer_list(self):
        '''method for testing the presentation and reachability of the manufacturer-list-view for several pages'''
        manufacturers = mommy.make(Manufacturer, _quantity=40)
        url = reverse("manufacturer-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["manufacturer_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        url = reverse("manufacturer-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_manufacturer_detail(self):
        '''method for testing the reachability of the detail-view of the choosen manufacturer'''
        manufacturer = mommy.make(Manufacturer)
        manufacturers = Manufacturer.objects.all()
        manufacturer = manufacturers[0]
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
