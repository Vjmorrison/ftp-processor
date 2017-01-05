
from google.appengine.api.taskqueue import taskqueue
import logging
import json

from coms.requests import BaseRequestObject
import coms.entitydefs as entitydefs


class _LogTask(BaseRequestObject):
	log_level = logging.INFO
	message = ""
	app_name = "DEFAULT"
	tags = []
	_target_url = "/task/write_log"

	def encode_params(self):
		return {
			"log_level": self.log_level,
			"message": self.message,
			"app_name": self.app_name,
			"tags": self.tags
		}

	def encode_payload(self):
		return json.dumps(self.encode_params(), sort_keys=True)


class _EmailTask(_LogTask):
	subject = ""
	body = ""
	to = ""
	_target_url = "/task/send_email"

	def encode_params(self):
		if self.message:
			if not self.subject:
				self.subject = self.message[:78]
			if not self.body:
				self.body = self.message
		return {
			"log_level": self.log_level,
			"to": self.to,
			"subject": self.subject,
			"body": self.body,
			"app_name": self.app_name,
			"tags": self.tags
		}


class _SlackTask(_LogTask):
	slackUser = "trending-notifier"
	slackIcon = ":chart_with_upwards_trend:"
	color = "good"
	room = ""
	title = ""
	title_link = ""
	text = ""
	fallback = ""
	_target_url = "/task/send_slack_message"

	def encode_params(self):
		raw_params = {
			"log_level": self.log_level,
			"app_name": self.app_name,
			"tags": self.tags,
			"slackUser": self.slackUser,
			'slackIcon': self.slackIcon,
			'color': self.color,
			'room': self.room,
			'title': self.title,
			'title_link': self.title_link,
			'fallback': self.fallback,
			'text': self.text
		}
		return raw_params

	def encode_payload(self):
		raw_data = {
			"channel": self.room,
			"username": self.slackUser,
			"icon_emoji": self.slackIcon,
			"attachments": [{
				"fallback": self.fallback,
				"color": self.color,
				"title": self.title,
				"title_link": self.title_link,
				"fields": []
			}]
		}
		raw_data['attachments'][0]['fields'].append({
			"value": self.text
		})

		payload = {
			'payload': json.dumps(raw_data).replace("\\r\\n", "\r\n")
		}
		return payload


class LogApiMixin(object):

	TASK_MODE, REQUEST_MODE = range(0, 2)

	_app_name = "DEFAULT"

	_mode = TASK_MODE
	_mode_map = []

	_taskqueue_name = ""

	enqueue_task_method = None

	def init(self):
		self._mode_map = {
			self.TASK_MODE: self._insert_task,
			self.REQUEST_MODE: self._make_request
		}

	def set_logger_info(self, mode=TASK_MODE, app_name="DEFAULT", taskqueue_name="logging-queue"):
		self.init()
		self._mode = mode
		self._app_name = app_name
		self._taskqueue_name = taskqueue_name
		pass

	def _insert_task(self, logtask):
		if callable(self.enqueue_task_method):
			self.enqueue_task_method(
				queue_name=self._taskqueue_name,
				params=logtask.encode_params(),
				url=logtask._target_url
			)
		else:
			taskqueue.add(url=logtask._target_url, target=self._taskqueue_name, params=logtask.encode_params())

	def _make_request(self, logtask):
		import urllib2
		request = urllib2.Request("{}?{}".format(logtask._target_url, logtask.encode_payload()))
		request.headers = self.request.headers
		urllib2.urlopen(request).read()
		pass

	def notify_subscription(self, subscription, alert):
		contact_data_list = subscription.contact_data
		for contact_key in contact_data_list:
			contact_data = contact_key.get()
			logging.info("alerting sub:{}".format(contact_data.name))
			self.format_and_notify_contact(contact_data, alert.to_format_dict())

	def format_and_notify_contact(self, contact, format_kwords):
		sub_type = contact.sub_type
		format_message = contact.message_format.format(**format_kwords)
		format_title = contact.title_format.format(**format_kwords)

		severity = entitydefs.status_to_log(format_kwords['status'])

		if sub_type == entitydefs.EMAIL:
			email_address = contact.email_address
			self.email(
				to=email_address,
				subject=format_title,
				body=format_message,
				metadata_tags=format_kwords['category'],
				severity=severity
			)
		else:
			raise ValueError("unknown sub type: {}".format(sub_type))

	def email(self, to, subject, body, metadata_tags=None, severity=logging.INFO):
		task = _EmailTask()
		task.to = to
		task.subject = subject
		task.body = body
		task.tags = metadata_tags
		task.log_level = severity
		self._mode_map[self._mode](task)

	def debug(self, message, *args, **kwargs):
		task = _LogTask()
		task.log_level = logging.DEBUG
		if len(kwargs) > 1:
			task.message = message.format(*args, **kwargs)
		else:
			task.message = message
		task.app_name = self._app_name
		print message
		self._mode_map[self._mode](task)

	def info(self, message, *args, **kwargs):
		task = _LogTask()
		task.log_level = logging.INFO
		if len(kwargs) > 1:
			task.message = message.format(*args, **kwargs)
		else:
			task.message = message
		print message
		task.app_name = self._app_name

		self._mode_map[self._mode](task)

	def warning(self, message, *args, **kwargs):
		task = _LogTask()
		task.log_level = logging.WARNING
		if len(kwargs) > 1:
			task.message = message.format(*args, **kwargs)
		else:
			task.message = message
		print message
		task.app_name = self._app_name

		self._mode_map[self._mode](task)

	def error(self, message, *args, **kwargs):
		task = _LogTask()
		task.log_level = logging.ERROR
		if len(kwargs) > 1:
			task.message = message.format(*args, **kwargs)
		else:
			task.message = message
		task.app_name = self._app_name
		print message
		self._mode_map[self._mode](task)

	def critical(self, message, *args, **kwargs):
		task = _LogTask()
		task.log_level = logging.CRITICAL
		if len(kwargs) > 1:
			task.message = message.format(*args, **kwargs)
		else:
			task.message = message
		task.app_name = self._app_name
		print message
		self._mode_map[self._mode](task)
