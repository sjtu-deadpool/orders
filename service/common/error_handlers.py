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
Module: error_handlers
"""
from flask import jsonify
from flask import current_app as app  # Import Flask application
from service.models import DataValidationError
from . import http_status


######################################################################
# Error Handlers
######################################################################
@app.errorhandler(DataValidationError)
def request_validation_error(error):
    """Handles Value Errors from bad data"""
    return bad_request(error)


@app.errorhandler(http_status.HTTP_400_BAD_REQUEST)
def bad_request(error):
    """Handles bad requests with 400_BAD_REQUEST"""
    message = str(error)
    app.logger.warning(message)
    return (
        jsonify(
            status=http_status.HTTP_400_BAD_REQUEST,
            error="Bad Request",
            message=message,
        ),
        http_status.HTTP_400_BAD_REQUEST,
    )
