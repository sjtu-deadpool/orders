"""
Models for Order

All of the models are stored in this module
"""

import logging
from typing import Any
from datetime import datetime, UTC
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger("flask.app")

# Create the SQLAlchemy object to be initialized later in init_db()
db = SQLAlchemy()

ALLOWED_STATUS = {"placed", "shipped", "returned", "canceled"}
DEFAULT_STATUS = "placed"


class DataValidationError(Exception):
    """Used for an data validation errors when deserializing"""


class Order(db.Model):
    """
    Class that represents an order
    """

    __tablename__ = "Order"
    ##################################################
    # Table Schema
    ##################################################
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer)
    status = db.Column(db.String(16), nullable=False, default="placed")
    shipped_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # maybe store any promotions used on this order?

    # Relationship to OrderItem with cascade delete
    order_items = db.relationship(
        "OrderItem", backref="order", cascade="all, delete-orphan", passive_deletes=True
    )

    def create(self):
        """
        Creates an order in the database
        """
        logger.info("Creating %s", self)
        self.id = None
        try:
            if self.status == "shipped" and self.shipped_at is None:
                self.shipped_at = datetime.now(UTC)
            db.session.add(self)
            # The order_items will be automatically saved due to the relationship
            # with cascade="all, delete-orphan" option
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DataValidationError(e) from e

    def update(self):
        """
        Updates an order in the database
        """
        logger.info("Saving %s", self)
        try:
            if self.status == "shipped" and self.shipped_at is None:
                self.shipped_at = datetime.now(UTC)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DataValidationError(e) from e

    def delete(self):
        """Removes an order from the data store"""
        logger.info("Deleting %s", self)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DataValidationError(e) from e

    def serialize(self, with_items=False) -> dict[str, Any]:
        """Serializes an order into a dictionary"""
        data = {
            "id": self.id,
            "customer_id": self.customer_id,
            "status": self.status,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
        }
        if with_items:
            data["order_items"] = [item.serialize() for item in self.order_items]
        return data

    # Add new require_fields parameter, because we require customer_id
    # **when creating** an order, but if we want to **update** a field other
    # than customer_id, then we cannot have this code always require it.
    def deserialize(self, data: dict[str, Any], *, require_fields=False):
        """
        Deserializes an order from a dictionary
        """
        try:
            if "customer_id" in data or require_fields:
                self.customer_id = data["customer_id"]

            status = str(data.get("status", self.status or DEFAULT_STATUS)).lower()
            if status not in ALLOWED_STATUS:
                raise DataValidationError(f"Invalid status '{status}'")
            self.status = status

            if "created_at" in data:
                self.created_at = data["created_at"]

            if "shipped_at" in data:
                self.shipped_at = data["shipped_at"]

            # Handle order_items if present in the data
            if "order_items" in data:
                # Clear existing order_items first
                self.order_items.clear()

                # Add new order_items
                for item_data in data["order_items"]:
                    order_item = OrderItem()
                    order_item.deserialize(item_data)
                    # The order_id will be set automatically due to the relationship
                    self.order_items.append(order_item)

        except KeyError as error:
            raise DataValidationError(
                "Invalid Order: missing " + error.args[0]
            ) from error

        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def remove_all(cls):
        """Removes all documents from the database (use for testing)"""
        for document in cls.all():  # pylint: disable=(not-an-iterable
            document.delete()

    @classmethod
    def all(cls) -> list["Order"]:
        """Returns all of the Orders in the database"""
        logger.info("Processing all Orders")
        return cls.query.all()  # type: ignore

    @classmethod
    def find(cls, by_id: Any):
        """Finds a Order by its ID"""
        logger.info("Processing lookup for id %s ...", by_id)
        return cls.query.session.get(cls, by_id)

    @classmethod
    def find_by_customer(cls, customer_id: Any):
        """Returns all orders with the given customer ID"""
        logger.info("Processing Order query with customer_id=%s", customer_id)
        return cls.query.filter(cls.customer_id == customer_id)

    @classmethod
    def find_by_status(cls, status: str):
        """Returns all orders with the given status"""
        logger.info("Processing Order query with status=%s", status)
        return cls.query.filter(cls.status == status)

    @classmethod
    def find_by_customer_and_status(cls, customer_id: Any, status: str):
        """Returns all orders with the given customer ID and status"""
        logger.info("Processing Order query with customer_id=%s and status=%s", customer_id, status)
        return cls.query.filter(cls.customer_id == customer_id, cls.status == status)


class OrderItem(db.Model):
    """
    Class that represents an order item
    """

    __tablename__ = "OrderItem"
    ##################################################
    # Table Schema
    ##################################################
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer)
    order_id = db.Column(
        db.Integer, db.ForeignKey("Order.id", ondelete="CASCADE"), nullable=False
    )
    product_id = db.Column(db.Integer)

    def create(self):
        """
        Creates an order item in the database
        """
        logger.info("Creating %s", self)
        self.id = None
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DataValidationError(e) from e

    def update(self):
        """
        Updates an order item in the database
        """
        logger.info("Saving %s", self)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DataValidationError(e) from e

    def delete(self):
        """Removes an order item from the data store"""
        logger.info("Deleting %s", self)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DataValidationError(e) from e

    def serialize(self) -> dict[str, Any]:
        """Serializes an order item into a dictionary"""
        return {
            "id": self.id,
            "quantity": self.quantity,
            "order_id": self.order_id,
            "product_id": self.product_id,
        }

    def deserialize(self, data: dict[str, Any]):
        """
        Deserializes an order item from a dictionary

        Args:
            data (dict): A dictionary containing the order data
        """
        try:
            # order_id is optional - can be set through relationship
            if "order_id" in data:
                self.order_id = data["order_id"]
            self.quantity = data["quantity"]
            self.product_id = data["product_id"]
        except KeyError as error:
            raise DataValidationError(
                "Invalid OrderItem: missing " + error.args[0]
            ) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid OrderItem: body of request contained bad or no data "
                + str(error)
            ) from error
        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def all(cls) -> list["OrderItem"]:
        """Returns all of the order items in the database"""
        logger.info("Processing all order items")
        return cls.query.all()  # type: ignore

    @classmethod
    def find(cls, by_id: Any):
        """Finds an order item by it's ID"""
        logger.info("Processing lookup for id %s ...", by_id)
        return cls.query.session.get(cls, by_id)

    @classmethod
    def find_by_order_id(cls, order_id: Any):
        """Returns all order items with the given order ID"""
        logger.info("Processing OrderItem lookup by order_id=%s", order_id)
        return cls.query.filter(cls.order_id == order_id)

    @classmethod
    def find_by_product(cls, product_id: Any):
        """Returns all order items with the given product ID"""
        logger.info("Processing OrderItem lookup by product_id=%s", product_id)
        return cls.query.filter(cls.product_id == product_id)
