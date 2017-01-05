# Copyright 2016 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Sample backend module deployed by backend.yaml and accessed in main.py
"""

import webapp2
import healthcheck
import basemodule

import logging

from google.appengine.api.mail_errors import InvalidSenderError

from google.appengine.api import mail
from google.appengine.runtime.apiproxy_errors import OverQuotaError
from google.appengine.api import app_identity

from webloggingapi import _LogTask, _EmailTask


class LoggingHandler(basemodule.BaseApiHandler):
	test_method = healthcheck.test_registry()
	api_method = basemodule.api_registry()

	LOG_FORMAT = 'AppName="{app_name}" | message="{message}" | Tags="{tags}"'

	_log_map = {
		logging.CRITICAL: logging.critical,
		logging.ERROR: logging.error,
		logging.WARNING: logging.warning,
		logging.INFO: logging.info,
		logging.DEBUG: logging.debug,
		logging.NOTSET: logging.debug,
		'CRITICAL': logging.critical,
		'ERROR': logging.error,
		'WARN': logging.warning,
		'WARNING': logging.warning,
		'INFO': logging.info,
		'DEBUG': logging.debug,
		'NOTSET': logging.debug,
	}

	@test_method(expected_value=True)
	def test_email(self):
		email_task = _EmailTask()
		email_task.to = "test@emailme.pw"
		email_task.subject = "This is a test Email from the logging server"
		email_task.body = "This is a test Email from the logging server"
		email_task.app_name = "LoggingHandler"
		email_task.log_level = logging.DEBUG
		self._send_email(email_task)
		return True

	@test_method(expected_value=True)
	def test_log(self):
		log_task = _LogTask()
		log_task.log_level = logging.DEBUG
		log_task.app_name = "TEST"
		log_task.message = "This is a test message"
		log_task.tags = ["test", "log"]
		self._write_log(log_task)
		return True

	@api_method(req_type=basemodule.GET_METHOD, base_request=_LogTask(required_args=["name", "message"]))
	def write_log(self):
		"""Writes a log message of the specified level to the named logger.
		Required Query Arguments:
		level - The log level to be used, must be a set value from the logging package, eg. logging.DEBUG or logging.ERROR
		message - The actual pre-formatted log message
		name - The name of the logger to use for the message. Normally the name of the module or application sending the message

		Optional Arguments:
		tags - [] 1 or more string tags to include in the log message
		"""

		self._write_log(self.parsed_arguments)

		return

	def _write_log(self, log_task):
		formattedMessage = self.LOG_FORMAT.format(
			app_name=log_task.app_name,
			message=log_task.message,
			tags=", ".join(log_task.tags)
		)
		logging.debug("{}: {}".format(log_task.log_level, formattedMessage))
		self._log_map[log_task.log_level](formattedMessage)

	@api_method(req_type=basemodule.POST_METHOD, base_request=_EmailTask(required_args=["subject", "body", "to"]))
	def send_email(self):
		self._send_email(self.parsed_arguments)

	@classmethod
	def _send_email(cls, email_task):
		app_ID = app_identity.get_application_id()
		sender_email = "noreply@{app_ID}.appspotmail.com".format(app_ID=app_ID)

		try:
			mail.send_mail(
				sender=sender_email,
				to=email_task.to,
				subject=email_task.subject,
				body=email_task.body
			)
		except InvalidSenderError:
			logging.critical("sender email: {}  is INVALID".format(sender_email))
		except OverQuotaError:
			logging.critical("Over Quota for sending Emails!")
		logging.debug("Sent an email with the following payload: {}".format(email_task.encode_payload()))


class LoggingHeathCheckHandler(healthcheck.HeathCheckMixIn, LoggingHandler):
	pass


app = webapp2.WSGIApplication([
	('/api/.*', LoggingHandler),
	('/task/.*', LoggingHandler),
	('/healthcheck', LoggingHeathCheckHandler),
], debug=True)



