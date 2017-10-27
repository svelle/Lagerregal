from django.test.client import Client
from django.test import TestCase
from model_mommy import mommy
from django.core.urlresolvers import reverse
from devices.models import Building, Room

from locations.models import Section
from users.models import Lageruser


class BuildingTests(TestCase):
    def setUp(self):
        '''method for setting up a test environment'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_building_creation(self):
        '''method for testing functionality of creating a building'''
        # creating an instance of Building and testing if this instance is instance of Building
        building = mommy.make(Building)
        building.save()
        self.assertTrue(isinstance(building, Building))

        # testing building name
        self.assertEqual(building.__unicode__(), building.name)

        # testing the methods of creating absolute- and edit-url
        self.assertEqual(building.get_absolute_url(), reverse('building-detail', kwargs={'pk': building.pk}))
        self.assertEqual(building.get_edit_url(), reverse('building-edit', kwargs={'pk': building.pk}))

    def test_building_list(self):
        '''method for testinf presentation and reachability of building list-view on several pages'''
        buildings = mommy.make(Building, _quantity=40)
        url = reverse("building-list")

        # testing response of building-list
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # testing the display of only 30 elements of the response on one page and the distribution of the remaining
        # results on the second page
        self.assertEqual(len(resp.context["building_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        # testing if loading of second page of building-list was successful (statuscode 2xx)
        url = reverse("building-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_building_detail(self):
        '''method for testing reachability of detail-view of building'''
        building = mommy.make(Building)
        buildings = Building.objects.all()
        building = buildings[0]

        # testing response of detail-view of first building in list of all buildings
        url = reverse("building-detail", kwargs={"pk": building.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_building_add(self):
        '''method for testing functionality of adding a building'''
        building = mommy.make(Building)
        buildings = Building.objects.all()
        building = buildings[0]

        # testing if loading of of add-page was successful (statuscode 2xx)
        url = reverse("building-add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_building_edit(self):
        '''method for testing functionality of editing a building'''
        # fetching all buildings and use first one in list to test
        building = mommy.make(Building)
        buildings = Building.objects.all()
        building = buildings[0]

        # testing if loading of of edit-page was successful (statuscode 2xx)
        url = reverse("building-edit", kwargs={"pk": building.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_building_delete(self):
        '''method for testing functionality of deleting a building'''
        # fetching all buildings and uses first element in list for testing
        building = mommy.make(Building)
        buildings = Building.objects.all()
        building = buildings[0]

        # should test if loading of delete-page was successful (statuscode 2xx)
        url = reverse("building-edit", kwargs={"pk": building.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


class RoomTests(TestCase):
    def setUp(self):
        '''method for setting up a test-environment'''
        self.client = Client()
        my_admin = Lageruser.objects.create_superuser('test', 'test@test.com', "test")
        self.client.login(username="test", password="test")

    def test_room_creation(self):
        '''method for testing the creation of a room'''
        # creating an instance of Room and testing if this instance is instance of Room
        room = mommy.make(Room)
        self.assertTrue(isinstance(room, Room))

        # testing room-naming
        self.assertEqual(room.__unicode__(), room.name)

        # testing the methods of creating absolute- and edit-url
        self.assertEqual(room.get_absolute_url(), reverse('room-detail', kwargs={'pk': room.pk}))
        self.assertEqual(room.get_edit_url(), reverse('room-edit', kwargs={'pk': room.pk}))

    def test_room_list(self):
        '''method for testing the presentation and reachability of the room list'''
        rooms = mommy.make(Room, _quantity=40)
        url = reverse("room-list")

        # testing response of room-list-page
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # testing the display of only 30 elements of the response on one page and the distribution of the remaining
        # results on the second page
        self.assertEqual(len(resp.context["room_list"]), 30)
        self.assertEqual(resp.context["paginator"].num_pages, 2)

        # testing if loading of second page of room-list was successful (statuscode 2xx)
        url = reverse("room-list", kwargs={"page": 2})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_room_detail(self):
        '''method for testing the reachability of the romm detail-view'''
        room = mommy.make(Room)
        rooms = Room.objects.all()
        room = rooms[0]

        # testing response of detail-view of first room in list of all rooms
        url = reverse("room-detail", kwargs={"pk": room.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_room_add(self):
        '''method for testing the functionality of adding a room'''
        room = mommy.make(Room)

        # testing if loading of of add-page was successful (statuscode 2xx)
        url = reverse("room-add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_room_edit(self):
        '''method for testing the functionality of editing a room'''
        # fetching all rooms and use first one in list to test
        room = mommy.make(Room)
        rooms = Room.objects.all()
        room = rooms[0]

        # testing if loading of of edit-page was successful (statuscode 2xx)
        url = reverse("room-edit", kwargs={"pk": room.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_room_delete(self):
        '''method for testing functionality of deleting a room'''
        # fetching all rooms and uses first element in list for testing
        room = mommy.make(Room)
        rooms = Room.objects.all()
        room = rooms[0]

        # should test if loading of delete-page was successful (statuscode 2xx)
        url = reverse("room-edit", kwargs={"pk": room.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)


class SectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        myadmin = Lageruser.objects.create_superuser("test", "test@test.com", "test")
        self.client.login(username = "test", password = "test")

    def test_section_creation(self):
        section = mommy.make(Section)
        self.assertEqual(section.__unicode__(), section.name)
        self.assertEqual(section.get_absolute_url(), reverse('section-detail', kwargs={'pk': section.pk}) )
        self.assertEqual(section.get_edit_url(), reverse('section-edit', kwargs={'pk': section.pk}))
