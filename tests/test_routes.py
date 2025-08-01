######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
TestOrder API Service Test Suite
"""

import os
import logging
from unittest import TestCase
from flask.testing import FlaskClient
from wsgi import app
from service.common import http_status
from service.models import db, Order, OrderItem
from service.routes import generate_apikey
from .factories import OrderFactory, OrderItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)

BASE_URL = "/api/orders"


class CustomClient(FlaskClient):
    """FlaskClient subclass to inject X-Api-Key header for authorization"""

    def __init__(self, *args, **kwargs):
        self._authentication = kwargs.pop("authentication")
        super().__init__(*args, **kwargs)

    def open(self, *args, **kwargs):
        headers = kwargs.pop("headers", {})
        no_auth = kwargs.pop("no_auth", False)
        # Automatically inject the X-Api-Key header if authentication is set
        if self._authentication and not no_auth:
            headers["X-Api-Key"] = self._authentication
        kwargs["headers"] = headers
        return super().open(*args, **kwargs)


app.test_client_class = CustomClient


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestOrder(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.config["API_KEY"] = generate_apikey()
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client(authentication=app.config["API_KEY"])
        # Clean up OrderItems first due to foreign key constraint
        db.session.query(OrderItem).delete()
        db.session.query(Order).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ############################################################
    # Utility function to bulk create orders
    ############################################################
    def _create_orders(self, count: int = 1) -> list[Order]:
        """Factory method to create orders in bulk"""
        orders = []
        for _ in range(count):
            test_order = OrderFactory()
            response = self.client.post(BASE_URL, json=test_order.serialize())
            self.assertEqual(
                response.status_code,
                http_status.HTTP_201_CREATED,
                "Could not create test order",
            )
            new_order = response.get_json()
            test_order.id = new_order["id"]
            orders.append(test_order)
        return orders

    ############################################################
    # Utility function to bulk create order items for an order
    ############################################################
    def _create_order_items(self, order_id: int, count: int = 1) -> list[OrderItem]:
        """Factory method to create order items in bulk"""
        items = []
        for _ in range(count):
            item = OrderItemFactory()
            response = self.client.post(
                f"{BASE_URL}/{order_id}/items", json=item.serialize()
            )
            self.assertEqual(
                response.status_code,
                http_status.HTTP_201_CREATED,
                "Could not create test order item",
            )
            item.id = response.json["id"]
            items.append(item)
        return items

    ######################################################################
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        self.assertIn(b"Order Demo REST API Service", resp.data)

    # for the last if-check of routes._check_content_type()
    def test_invalid_content_type(self):
        """It should return 415 for a non-json content type"""
        resp = self.client.post(
            BASE_URL, data="data", headers={"Content-Type": "text/html"}
        )
        self.assertEqual(resp.status_code, http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_unauthenticated(self):
        """It should return 401 for calling an authenticated endpoint without a token"""
        resp = self.client.post(BASE_URL, no_auth=True)
        self.assertEqual(resp.status_code, http_status.HTTP_401_UNAUTHORIZED)

    # ----------------------------------------------------------
    # TEST CREATE ORDER
    # ----------------------------------------------------------
    def test_create_order(self):
        """It should Create a new Order"""
        test_order = OrderFactory()
        logging.debug("Test Order: %s", test_order.serialize())
        response = self.client.post(BASE_URL, json=test_order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_order = response.get_json()
        self.assertEqual(new_order["customer_id"], test_order.customer_id)

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        new_order = response.get_json()
        self.assertEqual(new_order["customer_id"], test_order.customer_id)

    # ----------------------------------------------------------
    # TEST GET
    # ----------------------------------------------------------
    def test_get_order(self):
        """It should Get an existing Order by ID"""
        # First create and save an order
        test_order = OrderFactory()
        test_order.create()

        # Send GET request to /orders/<id>
        response = self.client.get(f"{BASE_URL}/{test_order.id}")
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

        # Check returned data
        data = response.get_json()
        self.assertEqual(data["id"], test_order.id)
        self.assertEqual(data["customer_id"], test_order.customer_id)

    def test_get_order_only_order(self):
        """It should Get an Order without OrderItems"""
        order = OrderFactory()
        order.create()
        resp = self.client.get(f"{BASE_URL}/{order.id}?o=true")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        data = resp.get_json()
        self.assertNotIn("order_items", data)

    # ----------------------------------------------------------
    # TEST DELETE
    # ----------------------------------------------------------
    def test_delete_order(self):
        """It should Delete an order"""
        test_order = self._create_orders(1)[0]
        response = self.client.delete(f"{BASE_URL}/{test_order.id}")
        self.assertEqual(response.status_code, http_status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)
        # make sure they are deleted
        response = self.client.get(f"{BASE_URL}/{test_order.id}")
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_delete_non_existing_order(self):
        """It should Delete an order even if it doesn't exist"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, http_status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)

    def test_delete_all_orders(self):
        """It should Delete all Orders"""
        # create orders
        self._create_orders(5)

        # verify they exist
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)

        # delete them all
        resp = self.client.delete(BASE_URL)
        self.assertEqual(resp.status_code, http_status.HTTP_204_NO_CONTENT)

        # verify they are gone
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 0)

    # ----------------------------------------------------------
    # TEST UPDATE
    # ----------------------------------------------------------
    def test_update_order(self):
        """It should Update an existing Order"""
        # create a order to update
        test_order = OrderFactory()
        response = self.client.post(BASE_URL, json=test_order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)

        # update the order
        new_order = response.get_json()
        logging.debug(new_order)
        # Only send the fields we want to update, avoiding order_items
        update_data = {
            "id": new_order["id"],
            "customer_id": -1,
            "status": new_order["status"],
        }
        response = self.client.put(f"{BASE_URL}/{new_order['id']}", json=update_data)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        updated_order = response.get_json()
        self.assertEqual(updated_order["customer_id"], -1)

    def test_create_order_missing_keys(self):
        """It should return 400 when creating an Order without customer_id"""
        resp = self.client.post(BASE_URL, json={})
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn("missing customer_id", resp.json["message"])

    def test_update_order_not_found_with_correct_content_type(self):
        """It should return 404 when updating an Order that does not exist"""
        payload = {"customer_id": 1}
        resp = self.client.put(f"{BASE_URL}/9999", json=payload)
        self.assertEqual(resp.status_code, http_status.HTTP_404_NOT_FOUND)
        data = resp.get_json()
        self.assertIn("was not found", data["message"])

    def test_update_order_unsupported_media_type(self):
        """It should return 415 when updating an Order without Content-Type"""
        order = OrderFactory()
        response = self.client.post(BASE_URL, json=order.serialize())
        order_id = response.get_json()["id"]
        resp = self.client.put(f"{BASE_URL}/{order_id}", data="something")
        self.assertEqual(resp.status_code, http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ----------------------------------------------------------
    # TEST LIST ORDERS
    # ----------------------------------------------------------
    def test_list_orders(self):
        """It should Get a list of Orders"""
        # list the order
        self._create_orders(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_list_orders_filter_by_id_and_customer(self):
        """It should filter Orders by id and by customer_id"""
        # create three orders: A, B, C
        created = self._create_orders(3)
        # pick the 2nd one
        order2 = created[1]

        # 2) filter by customer_id
        # reuse order2.customer_id
        resp2 = self.client.get(f"{BASE_URL}?customer_id={order2.customer_id}")
        self.assertEqual(resp2.status_code, http_status.HTTP_200_OK)
        data2 = resp2.get_json()
        # all orders with that same customer_id
        expected = [o for o in created if o.customer_id == order2.customer_id]
        self.assertEqual(len(data2), len(expected))
        for item in data2:
            self.assertEqual(item["customer_id"], order2.customer_id)

    def test_list_orders_filter_by_status(self):
        """It should filter Orders by status"""
        # Create orders with different statuses
        order1 = OrderFactory(status="placed")
        self.client.post(BASE_URL, json=order1.serialize())
        order2 = OrderFactory(status="shipped")
        self.client.post(BASE_URL, json=order2.serialize())
        order3 = OrderFactory(status="canceled")
        self.client.post(BASE_URL, json=order3.serialize())

        # Filter by status=shipped
        resp = self.client.get(f"{BASE_URL}?status=shipped")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(order["status"] == "shipped" for order in data))
        self.assertTrue(any(order["status"] == "shipped" for order in data))
        self.assertFalse(any(order["status"] == "placed" for order in data))
        self.assertFalse(any(order["status"] == "canceled" for order in data))

    def test_list_orders_filter_by_customer_and_status(self):
        """It should filter Orders by customer_id and status"""
        # Create orders with different customer_id and status combinations
        order1 = OrderFactory(customer_id=101, status="placed")
        self.client.post(BASE_URL, json=order1.serialize())
        order2 = OrderFactory(customer_id=101, status="shipped")
        self.client.post(BASE_URL, json=order2.serialize())
        order3 = OrderFactory(customer_id=102, status="placed")
        self.client.post(BASE_URL, json=order3.serialize())

        # Filter by customer_id=101 and status=placed
        resp = self.client.get(f"{BASE_URL}?customer_id=101&status=placed")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["customer_id"], 101)
        self.assertEqual(data[0]["status"], "placed")

        # Filter by customer_id=101 and status=shipped
        resp = self.client.get(f"{BASE_URL}?customer_id=101&status=shipped")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["customer_id"], 101)
        self.assertEqual(data[0]["status"], "shipped")

        # Filter by customer_id=102 and status=placed
        resp = self.client.get(f"{BASE_URL}?customer_id=102&status=placed")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["customer_id"], 102)
        self.assertEqual(data[0]["status"], "placed")

        # Filter by non-existent combination
        resp = self.client.get(f"{BASE_URL}?customer_id=999&status=placed")
        self.assertEqual(resp.status_code, http_status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 0)

    def test_list_orders_only_order(self):
        """It should Get a list of Orders without order_items"""
        # list the order
        self._create_orders(5)
        response = self.client.get(f"{BASE_URL}?o=true")
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)
        for order_data in data:
            self.assertNotIn("order_items", order_data)

    # ----------------------------------------------------------
    # TEST CREATE ORDER ITEM
    # ----------------------------------------------------------
    def test_create_order_item(self):
        """It should create a new OrderItem inside an existing Order"""

        order = OrderFactory()
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        order_item = OrderItemFactory()

        url = f"{BASE_URL}/{order_id}/items"
        response = self.client.post(url, json=order_item.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)

        created = response.get_json()
        self.assertEqual(created["order_id"], order_id)
        self.assertEqual(created["product_id"], order_item.product_id)
        self.assertEqual(created["quantity"], order_item.quantity)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["order_id"], order_id)
        self.assertEqual(data["product_id"], order_item.product_id)
        self.assertEqual(data["quantity"], order_item.quantity)

    def test_create_order_item_order_not_found(self):
        """It should return 404 when creating an OrderItem in a non-existing Order"""
        payload = {"product_id": 1, "quantity": 1}
        resp = self.client.post(f"{BASE_URL}/0/items", json=payload)
        self.assertEqual(resp.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_create_order_item_missing_keys(self):
        """It should return 400 when creating an OrderItem without required keys"""
        order = OrderFactory()
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        resp = self.client.post(f"{BASE_URL}/{order_id}/items", json={"quantity": 1})
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn("missing product_id", resp.json["message"])

        resp = self.client.post(f"{BASE_URL}/{order_id}/items", json={"product_id": 1})
        self.assertEqual(resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn("missing quantity", resp.json["message"])

    # ----------------------------------------------------------
    # TEST GET ORDER ITEM
    # ----------------------------------------------------------
    def test_get_order_item(self):
        """It should Get an existing OrderItem"""
        # Create an order
        order = OrderFactory()
        resp = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(resp.status_code, http_status.HTTP_201_CREATED)
        order_id = resp.get_json()["id"]

        # Create an order item
        order_item = OrderItemFactory(order_id=order_id)
        response = self.client.post(
            f"{BASE_URL}/{order_id}/items", json=order_item.serialize()
        )
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        created_item = response.get_json()
        order_item_id = created_item["id"]

        # Retrieve the item and check it
        get_url = f"{BASE_URL}/{order_id}/items/{order_item_id}"
        get_resp = self.client.get(get_url)
        self.assertEqual(get_resp.status_code, http_status.HTTP_200_OK)
        data = get_resp.get_json()
        self.assertEqual(data["id"], order_item_id)
        self.assertEqual(data["order_id"], order_id)
        self.assertEqual(data["quantity"], order_item.quantity)
        self.assertEqual(data["product_id"], order_item.product_id)

    def test_get_order_item_order_not_found(self):
        """It should return 404 when getting an OrderItem in a non-existing Order"""
        resp = self.client.get(f"{BASE_URL}/0/items/1")
        self.assertEqual(resp.status_code, http_status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST UPDATE ORDER ITEM
    # ----------------------------------------------------------
    def test_update_order_item(self):
        """It should Update an existing OrderItem"""
        # Create an order
        order = OrderFactory()
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.json["id"]

        # Create an order item
        response = self.client.post(
            f"{BASE_URL}/{order_id}/items",
            json=OrderItemFactory(order_id=order_id).serialize(),
        )
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        resp_data = response.get_json()

        # Verify that the item is attached to the order
        self.assertEqual(resp_data["order_id"], order_id)

        # Update the OrderItem object received with new values
        item_data = response.get_json()
        original_order_id = item_data["order_id"]
        item_data["order_id"] = -1  # This should be ignored by the API
        item_data["quantity"] = 99
        item_data["product_id"] = 123

        # Call the Update Order Item API endpoint
        item_id = item_data["id"]
        response = self.client.put(
            f"{BASE_URL}/{order_id}/items/{item_id}", json=item_data
        )
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

        # Verify that the OrderItem was updated
        updated_item = response.get_json()
        # order_id should remain unchanged (not be updated to -1)
        self.assertEqual(updated_item["order_id"], original_order_id)
        # Other fields should be updated
        self.assertEqual(updated_item["quantity"], 99)
        self.assertEqual(updated_item["product_id"], 123)

    def test_update_order_item_order_not_found(self):
        """It should return 404 when updating an OrderItem in a non-existing Order"""
        resp = self.client.put(
            f"{BASE_URL}/0/items/1", json={"quantity": 1, "product_id": 1}
        )
        self.assertEqual(resp.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_update_order_item_not_found(self):
        """PUT existing order but missing item -> 404"""
        order = OrderFactory()
        response = self.client.post(BASE_URL, json=order.serialize())
        order_id = response.get_json()["id"]
        resp = self.client.put(
            f"{BASE_URL}/{order_id}/items/9999", json={"quantity": 3}
        )
        self.assertEqual(resp.status_code, http_status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST LIST ORDER ITEMS
    # ----------------------------------------------------------
    def test_list_order_items(self):
        """It should Get a list of OrderItems for an Order"""
        # Create an order
        order = OrderFactory()
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.json["id"]

        # list the order
        self._create_order_items(order_id, 5)
        response = self.client.get(f"{BASE_URL}/{order_id}/items")
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    # ----------------------------------------------------------
    # TEST LIST ORDER ITEMS
    # ----------------------------------------------------------
    def test_list_order_items_order_doesnt_exist(self):
        """It should Get a list of OrderItems for an Order"""
        response = self.client.get(f"{BASE_URL}/99999/items")
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST DELETE ORDER ITEM
    # ----------------------------------------------------------
    def test_delete_order_item(self):
        """It should Delete an existing OrderItem from an Order"""
        # Create an order
        order = OrderFactory()
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Create an order item
        order_item = OrderItemFactory(order_id=order_id)
        item_resp = self.client.post(
            f"{BASE_URL}/{order_id}/items", json=order_item.serialize()
        )
        self.assertEqual(item_resp.status_code, http_status.HTTP_201_CREATED)
        item_id = item_resp.get_json()["id"]

        # Delete the item
        delete_resp = self.client.delete(f"{BASE_URL}/{order_id}/items/{item_id}")
        self.assertEqual(delete_resp.status_code, http_status.HTTP_204_NO_CONTENT)

        # Confirm it's gone
        get_resp = self.client.get(f"{BASE_URL}/{order_id}/items/{item_id}")
        self.assertEqual(get_resp.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_order_item(self):
        """It should return 204 when deleting a non-existing OrderItem in an existing Order"""
        # Create an order
        order = OrderFactory()
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Attempt to delete non-existing item
        item_id = 99999
        delete_resp = self.client.delete(f"{BASE_URL}/{order_id}/items/{item_id}")
        self.assertEqual(delete_resp.status_code, http_status.HTTP_204_NO_CONTENT)

    def test_delete_order_item_wrong_order(self):
        """It should return 404 when deleting an OrderItem from the wrong Order"""
        # Create order A
        order_a = OrderFactory()
        resp_a = self.client.post(BASE_URL, json=order_a.serialize())
        self.assertEqual(resp_a.status_code, http_status.HTTP_201_CREATED)
        order_a_id = resp_a.get_json()["id"]

        # Create order B
        order_b = OrderFactory()
        resp_b = self.client.post(BASE_URL, json=order_b.serialize())
        self.assertEqual(resp_b.status_code, http_status.HTTP_201_CREATED)
        order_b_id = resp_b.get_json()["id"]

        # Create item in order B
        item = OrderItemFactory(order_id=order_b_id)
        resp_item = self.client.post(
            f"{BASE_URL}/{order_b_id}/items", json=item.serialize()
        )
        self.assertEqual(resp_item.status_code, http_status.HTTP_201_CREATED)
        item_id = resp_item.get_json()["id"]

        # Try to delete that item using order A's path
        delete_resp = self.client.delete(f"{BASE_URL}/{order_a_id}/items/{item_id}")
        self.assertEqual(delete_resp.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_delete_order_item_order_not_found(self):
        """It should return 404 when deleting an OrderItem in a non-existing Order"""
        resp = self.client.delete(f"{BASE_URL}/0/items/1")
        self.assertEqual(resp.status_code, http_status.HTTP_404_NOT_FOUND)

    # ----------------------------------------------------------
    # TEST RETURN ORDER
    # ----------------------------------------------------------
    def test_return_order_placed_status(self):
        """It should return 400 when trying to return an order with 'placed' status"""
        # Create an order with 'placed' status
        order = OrderFactory(status="placed")
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Try to return the placed order
        return_resp = self.client.put(f"{BASE_URL}/{order_id}/return")
        self.assertEqual(return_resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot return order with status 'placed'",
            return_resp.get_json()["message"],
        )

        # Verify order status was not changed
        get_resp = self.client.get(f"{BASE_URL}/{order_id}")
        order_data = get_resp.get_json()
        self.assertEqual(order_data["status"], "placed")

    def test_return_order_shipped_status(self):
        """It should return an order with 'shipped' status"""
        # Create an order with 'shipped' status
        order = OrderFactory(status="shipped")
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Return the order
        return_resp = self.client.put(f"{BASE_URL}/{order_id}/return")
        self.assertEqual(return_resp.status_code, http_status.HTTP_202_ACCEPTED)

        # Check response data
        data = return_resp.get_json()
        self.assertEqual(data["order_id"], order_id)
        self.assertEqual(data["status"], "returned")

    def test_return_order_already_returned(self):
        """It should return 400 when trying to return an already returned order"""
        # Create an order with 'returned' status
        order = OrderFactory(status="returned")
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Try to return the already returned order
        return_resp = self.client.put(f"{BASE_URL}/{order_id}/return")
        self.assertEqual(return_resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot return order with status 'returned'",
            return_resp.get_json()["message"],
        )

    def test_return_order_canceled_status(self):
        """It should return 400 when trying to return a canceled order"""
        # Create an order with 'canceled' status
        order = OrderFactory(status="canceled")
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Try to return the canceled order
        return_resp = self.client.put(f"{BASE_URL}/{order_id}/return")
        self.assertEqual(return_resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot return order with status 'canceled'",
            return_resp.get_json()["message"],
        )

    def test_return_order_not_found(self):
        """It should return 404 when trying to return a non-existing order"""
        # Try to return a non-existing order
        return_resp = self.client.put(f"{BASE_URL}/99999/return")
        self.assertEqual(return_resp.status_code, http_status.HTTP_404_NOT_FOUND)
        self.assertIn(
            "Order with id '99999' was not found", return_resp.get_json()["message"]
        )

    # ----------------------------------------------------------
    # TEST CANCEL ORDER
    # ----------------------------------------------------------
    def test_cancel_order_placed_status(self):
        """It should cancel an order with 'placed' status"""
        # Create an order with 'placed' status
        order = OrderFactory(status="placed")
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Cancel the order
        cancel_resp = self.client.put(f"{BASE_URL}/{order_id}/cancel")
        self.assertEqual(cancel_resp.status_code, http_status.HTTP_200_OK)

        # Check response data
        data = cancel_resp.get_json()
        self.assertEqual(data["id"], order_id)
        self.assertEqual(data["status"], "canceled")

        # Verify order status was updated in database
        get_resp = self.client.get(f"{BASE_URL}/{order_id}")
        order_data = get_resp.get_json()
        self.assertEqual(order_data["status"], "canceled")

    def test_cancel_order_shipped_status(self):
        """It should return 400 when trying to cancel an order with 'shipped' status"""
        # Create an order with 'shipped' status
        order = OrderFactory(status="shipped")
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Try to cancel the shipped order
        cancel_resp = self.client.put(f"{BASE_URL}/{order_id}/cancel")
        self.assertEqual(cancel_resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot cancel order with status 'shipped'",
            cancel_resp.get_json()["message"],
        )

        # Verify order status was not changed
        get_resp = self.client.get(f"{BASE_URL}/{order_id}")
        order_data = get_resp.get_json()
        self.assertEqual(order_data["status"], "shipped")

    def test_cancel_order_already_canceled(self):
        """It should return 400 when trying to cancel an already canceled order"""
        # Create an order with 'canceled' status
        order = OrderFactory(status="canceled")
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Try to cancel the already canceled order
        cancel_resp = self.client.put(f"{BASE_URL}/{order_id}/cancel")
        self.assertEqual(cancel_resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot cancel order with status 'canceled'",
            cancel_resp.get_json()["message"],
        )

    def test_cancel_order_returned_status(self):
        """It should return 400 when trying to cancel a returned order"""
        # Create an order with 'returned' status
        order = OrderFactory(status="returned")
        response = self.client.post(BASE_URL, json=order.serialize())
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        order_id = response.get_json()["id"]

        # Try to cancel the returned order
        cancel_resp = self.client.put(f"{BASE_URL}/{order_id}/cancel")
        self.assertEqual(cancel_resp.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot cancel order with status 'returned'",
            cancel_resp.get_json()["message"],
        )

    def test_cancel_order_not_found(self):
        """It should return 404 when trying to cancel a non-existing order"""
        # Try to cancel a non-existing order
        cancel_resp = self.client.put(f"{BASE_URL}/99999/cancel")
        self.assertEqual(cancel_resp.status_code, http_status.HTTP_404_NOT_FOUND)
        self.assertIn(
            "Order with id '99999' was not found", cancel_resp.get_json()["message"]
        )

    # ----------------------------------------------------------
    # TEST Health
    # ----------------------------------------------------------

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["status"], 200)
        self.assertEqual(data["message"], "Healthy")
