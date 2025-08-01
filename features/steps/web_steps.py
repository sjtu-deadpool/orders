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

# pylint: disable=function-redefined, missing-function-docstring
# flake8: noqa
"""
Web Steps

Steps file for web interactions with Selenium

For information on Waiting until elements are present in the HTML see:
    https://selenium-python.readthedocs.io/waits.html
"""
import re
import logging
from typing import Any
from behave import when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions

ID_PREFIX = "order_"


def save_screenshot(context: Any, filename: str) -> None:
    """Takes a snapshot of the web page for debugging and validation

    Args:
        context (Any): The session context
        filename (str): The message that you are looking for
    """
    # Remove all non-word characters (everything except numbers and letters)
    filename = re.sub(r"[^\w\s]", "", filename)
    # Replace all runs of whitespace with a single dash
    filename = re.sub(r"\s+", "-", filename)
    context.driver.save_screenshot(f"./captures/{filename}.png")


@when('I visit the "Home Page"')
def step_impl(context: Any) -> None:
    """Make a call to the base URL"""
    context.driver.get(context.base_url)
    # Uncomment next line to take a screenshot of the web page
    # save_screenshot(context, 'Home Page')


@then('I should see "{message}" in the title')
def step_impl(context: Any, message: str) -> None:
    """Check the document title for a message"""
    assert message in context.driver.title


@then('I should not see "{text_string}"')
def step_impl(context: Any, text_string: str) -> None:
    element = context.driver.find_element(By.TAG_NAME, "body")
    assert text_string not in element.text


@when("I get the first order id from the results")
def step_impl(context):
    table = context.driver.find_element(By.ID, "search_results")
    first_row = table.find_element(By.TAG_NAME, "tbody").find_element(By.TAG_NAME, "tr")
    order_id = first_row.find_elements(By.TAG_NAME, "td")[0].text
    context.first_order_id = order_id


@when('I set the "{element_name}" to "{text_string}"')
def step_impl(context, element_name, text_string):
    # Support dynamic variable substitution
    if text_string.startswith("{") and text_string.endswith("}"):
        var_name = text_string[1:-1]
        text_string = getattr(context, var_name)
    element_id = element_name.replace(" ", "_")
    element = WebDriverWait(context.driver, context.wait_seconds).until(
        expected_conditions.element_to_be_clickable((By.ID, element_id))
    )
    element.clear()
    element.send_keys(text_string)


@when('I select "{text}" in the "{element_name}" dropdown')
def step_impl(context, text, element_name):
    element_id = element_name.replace(" ", "_")
    element = Select(context.driver.find_element(By.ID, element_id))
    element.select_by_visible_text(text)


@then('I should see "{text}" in the "{element_name}" dropdown')
def step_impl(context, text, element_name):
    element_id = element_name.replace(" ", "_")
    element = Select(context.driver.find_element(By.ID, element_id))
    assert element.first_selected_option.text == text


@then('I should see "{text}" in the "{element_name}" field')
def step_impl(context, text, element_name):
    element_id = element_name.replace(" ", "_")
    element = context.driver.find_element(By.ID, element_id)
    assert element.get_attribute("value") == text


@then('the "{element_name}" field should be empty')
def step_impl(context, element_name):
    element_id = element_name.replace(" ", "_")
    element = context.driver.find_element(By.ID, element_id)
    assert element.get_attribute("value") == ""


##################################################################
# These two function simulate copy and paste
##################################################################
@when('I copy the "{element_name}" field')
def step_impl(context, element_name):
    element_id = element_name.replace(" ", "_")
    element = WebDriverWait(context.driver, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, element_id))
    )
    context.clipboard = element.get_attribute("value")
    logging.info("Clipboard contains: %s", context.clipboard)


@when('I paste the "{element_name}" field')
def step_impl(context, element_name):
    element_id = element_name.replace(" ", "_")
    element = WebDriverWait(context.driver, context.wait_seconds).until(
        expected_conditions.presence_of_element_located((By.ID, element_id))
    )
    element.clear()
    element.send_keys(context.clipboard)


##################################################################
# This code works because of the following naming convention:
# The buttons have an id in the html hat is the button text
# in lowercase followed by '-btn' so the Clear button has an id of
# id='clear-btn'. That allows us to lowercase the name and add '-btn'
# to get the element id of any button
##################################################################


# Optionally, you can keep the generic button step for other buttons, but 'Apply' is now handled in orders_steps.py


@then('I should see "{name}" in the results')
def step_impl(context: Any, name: str) -> None:
    found = WebDriverWait(context.driver, context.wait_seconds).until(
        expected_conditions.text_to_be_present_in_element(
            (By.ID, "search_results"), name
        )
    )
    assert found


@then('I should not see "{name}" in the results')
def step_impl(context: Any, name: str) -> None:
    element = context.driver.find_element(By.ID, "search_results")
    assert name not in element.text


@then('I should see the message "{message}"')
def step_impl(context: Any, message: str) -> None:
    # Uncomment next line to take a screenshot of the web page for debugging
    # save_screenshot(context, message)
    found = WebDriverWait(context.driver, context.wait_seconds).until(
        expected_conditions.text_to_be_present_in_element(
            (By.ID, "flash_message"), message
        )
    )
    assert found


@then('I should see "{text}" in the message')
def step_impl(context, text):
    # Wait until the flash_message contains the expected text
    WebDriverWait(context.driver, context.wait_seconds).until(
        expected_conditions.text_to_be_present_in_element(
            (By.ID, "flash_message"), text
        )
    )
    element = context.driver.find_element(By.ID, "flash_message")
    print("DEBUG: flash_message =", element.text)
    assert text in element.text

@then('I should see {count} orders in the results table')
def step_impl(context, count):
    """Check the number of orders in the results table"""
    if int(count) == 0:
        # For 0 orders, just wait for flash message to appear
        # This is faster than waiting for table updates
        WebDriverWait(context.driver, 10).until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "flash_message"), "Found 0 order(s)"
            )
        )
    else:
        # Wait for the table to be updated with a shorter timeout
        WebDriverWait(context.driver, 5).until(
            expected_conditions.presence_of_element_located((By.ID, "search_results"))
        )
        
        # Wait for flash message to appear (indicates AJAX request completed)
        WebDriverWait(context.driver, 10).until(
            expected_conditions.text_to_be_present_in_element(
                (By.ID, "flash_message"), "Found"
            )
        )
        
        # Now check the table rows
        table = context.driver.find_element(By.ID, "search_results")
        rows = table.find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")
        assert len(rows) == int(count)

@then('I should see an order with id "{order_id}"')
def step_impl(context, order_id):
    """Check if an order with specific ID exists in the results"""
    table = context.driver.find_element(By.ID, "search_results")
    rows = table.find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")
    found = False
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if cells and cells[0].text == order_id:
            found = True
            break
    assert found, f"Order with id {order_id} not found in results"

@then('every order in the results should have status "{status}"')
def step_impl(context, status):
    """Check if all orders in results have the specified status"""
    table = context.driver.find_element(By.ID, "search_results")
    rows = table.find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if cells and len(cells) >= 3:
            order_status = cells[2].text
            assert order_status.lower() == status.lower(), f"Expected status {status}, got {order_status}"

@then('every order in the results should belong to customer "{customer_id}"')
def step_impl(context, customer_id):
    """Check if all orders in results belong to the specified customer"""
    table = context.driver.find_element(By.ID, "search_results")
    rows = table.find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if cells and len(cells) >= 2:
            order_customer_id = cells[1].text
            assert order_customer_id == customer_id, f"Expected customer_id {customer_id}, got {order_customer_id}"

@then('I should see "{text}" in the page')
def step_impl(context, text):
    """Check if text appears anywhere on the page"""
    element = context.driver.find_element(By.TAG_NAME, "body")
    assert text in element.text

@when('I should see "{text}" in the page')
def step_impl(context, text):
    """Check if text appears anywhere on the page (when step)"""
    element = context.driver.find_element(By.TAG_NAME, "body")
    assert text in element.text

@when('I press the "Retrieve" button')
def step_impl(context):
    button = context.driver.find_element(By.ID, "retrieve-btn")
    button.click()

@when('I press the "Delete" button')
def step_impl(context):
    button = context.driver.find_element(By.ID, "delete-btn")
    button.click()

@then('the "{element_name}" field should not be empty')
def step_impl(context, element_name):
    element_id = element_name.replace(" ", "_")
    element = context.driver.find_element(By.ID, element_id)
    assert element.get_attribute("value") != ""
