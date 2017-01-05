import webapp2
import json
from coms.response import json_encode, ApiReference, ApiResponse
from google.appengine.api import app_identity
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.api import modules
from google.appengine.api import taskqueue
import logging

import urllib

import sys
import traceback

import webloggingapi

POST_METHOD = urlfetch.POST
GET_METHOD = urlfetch.GET

JSON_RESPONSE = "JSON"
METHOD_OVERRIDE_RESPONSE = "METHOD_OVERRIDE"


class BaseApiHandler(webapp2.RequestHandler, webloggingapi.LogApiMixin):
	api_method = None
	request_type = None
	parsed_arguments = None
	is_prod = "-prod-" in app_identity.get_application_id().lower()
	valid_users = []

	def _do_request(self):
		if not self._validate_request():
			self.response.set_status(401, "unauthorized")
			self.render_json({
				'error': 'Unauthorized',

			}, True)
			return
		splitPath = [value for value in self.request.path.split('/') if not value == ""]
		if "cron" in splitPath:
			splitPath.pop(splitPath.index("cron"))
		try:
			validAPIMethodNames = [apiMethod_name for apiMethod_name in self.api_method.all if self.api_method.all[apiMethod_name].request_type == self.request_type]
			validAPIMethodNames.append("get_api_methods")
		except AttributeError:
			validAPIMethodNames = []

		if len(splitPath) > 1:
			requestedAPI = splitPath[-1]
		else:
			requestedAPI = "_index"

		if requestedAPI == "get_api_methods":
			self.render_json(self.get_api_methods(), True)
			return

		foundAPI = [self.api_method.all[api_name] for api_name in validAPIMethodNames if api_name.lower() == requestedAPI.lower()]
		if len(foundAPI) > 0:
			result, api_response = foundAPI[0](self)
			if foundAPI[0].response_type == JSON_RESPONSE:
				self.render_json(api_response, self.request.get('debug'))
			elif foundAPI[0].response_type == METHOD_OVERRIDE_RESPONSE:
				'''Method handled the response directly (typically for Jinja Template rendering)'''
				return
			return

		self.render_json(
			{
				'error': 'No Such API Found',
				'validAPIs': [api for api in validAPIMethodNames],
				'sentAPI': requestedAPI
			},
			True
		)

	def get_api_methods(self):
		api_methods = []
		method_names = [apiMethod_name for apiMethod_name in self.api_method.all]
		for name in method_names:
			if self.api_method.all[name].request_type == GET_METHOD:
				req_type_string = "GET"
			else:
				req_type_string = "POST"

			data = {
				'name': name,
				'description': self.api_method.all[name].description,
				'parameters': "",
				'request_method': req_type_string,
				'url': urllib.basejoin(
					"http://{}/".format(modules.get_hostname(module=modules.get_current_module_name())),
					"/api/{}".format(name)
				)
			}
			if self.api_method.all[name].base_request:
				data['parameters'] = self.get_arg_properties(self.api_method.all[name].base_request)
			api_methods.append(data)
		api_methods = sorted(api_methods, key=lambda api: api['name'])
		result = {
			"name": modules.get_current_module_name(),
			"api_methods": api_methods
		}
		return result

	def startup(self):
		self.set_logger_info(mode=self.TASK_MODE, app_name=self.__class__.__name__)
		self.enqueue_task_method = self.enqueue_task
		with open('valid_users.json') as data_file:
			data = json.load(data_file)
			self.valid_users.extend(data)

	def post(self):
		self.startup()
		self.request_type = POST_METHOD
		self._do_request()

	def get(self):
		self.startup()
		self.request_type = GET_METHOD
		self._do_request()

	def render_json(self, obj, debug):
		convertedObject = json_encode(obj)
		if debug:
			returnJson = json.dumps(convertedObject, sort_keys=True, indent=4, separators=(',', ': '))
		else:
			try:
				returnJson = json.dumps(convertedObject)
			except TypeError:
				returnJson = "{}".format(convertedObject)
		self.response.headers.add_header("Content-Type", "application/json")
		self.response.write(returnJson)

	@classmethod
	def log_info(cls, message, *format_args):
		pass

	@classmethod
	def get_arg_properties(cls, base_request_obj):
		arg_names = base_request_obj.get_arg_names()
		arg_names.remove('required_args')
		arg_properties = []
		for name in arg_names:
			prop = getattr(base_request_obj, name)
			if hasattr(prop, "strip"):
				readable_prop = '"{}"'.format(prop)
			else:
				readable_prop = prop
			arg_properties.append({
				'name': name,
				'default_value': prop,
				'default_value_readable': readable_prop,
				'required': name in base_request_obj.required_args
			})
		arg_properties = sorted(arg_properties, key=lambda arg_prop: arg_prop['name'])
		return arg_properties

	@classmethod
	def _get_allowed_app_ids(cls):
		return [
			'di-trending-us-nonprod-2',
		]

	@classmethod
	def is_valid_io_user(cls):
		user = users.get_current_user()
		if user:
			valid_users = [

			]
			return user.email().lower() in valid_users
		return False

	def is_valid_appengine_project(self):
		incoming_app_id = self.request.headers.get('X-Appengine-Inbound-Appid', None)
		if incoming_app_id:
			return incoming_app_id in self._get_allowed_app_ids() or incoming_app_id == app_identity.get_application_id()

	def _validate_request(self):
		if self.is_valid_io_user():
			return True

		incoming_app_id = self.request.headers.get('X-Appengine-Inbound-Appid', None)
		if incoming_app_id:
			self.info("Incoming app ID {appid}", appid=incoming_app_id)
			return incoming_app_id in self._get_allowed_app_ids() or incoming_app_id == app_identity.get_application_id()

		if self.request.headers.get('X-Appengine-Cron', None):
			return True

		if self.request.headers.get('X-Appengine-Queuename'):
			return True

		if 'Authorization' in self.request.headers:
			if app_identity.get_application_id() == "None":  # running locally
				return True

		self.info("Unauthorized!  headers:{}", self.request.headers)
		return False

	@classmethod
	def make_http_request(cls, complete_url, headers=None, params=None, method=urlfetch.GET):
		if not params:
			params = {}
		if hasattr(params, "items"):
			# mapping objects
			urlencoded_params = urllib.urlencode(params, doseq=True)
		else:
			urlencoded_params = params

		if method == urlfetch.GET and urlencoded_params:
			complete_url += "?" + urlencoded_params

		if not headers:
			headers = {}
		try:
			response = urlfetch.fetch(
				complete_url,
				payload=urlencoded_params,
				method=method,
				validate_certificate=True,
				headers=headers
			)
		except (urlfetch.DeadlineExceededError, urlfetch.SSLCertificateError), err:
			return err.message, 500

		return response.content, response.status_code, response.headers

	@classmethod
	def enqueue_task(cls, queue_name="default", params=None, url=None):
		pollqueue = taskqueue.Queue(name=queue_name)
		task = taskqueue.Task(
			params=params,
			url=url
		)
		pollqueue.add(task)


def api_registry():
	api_methods = {}

	def api_registrar(req_type=GET_METHOD, base_request=None, response_type=JSON_RESPONSE):
		def wrapper(func):
			def wrapped_api(self, *args, **kwargs):
				new_request_obj = None
				apiRef = ApiReference(self, func, base_request)
				if base_request:
					new_request_obj = base_request.__class__()
					missing_arguments = base_request.parse_arguments(
						return_object=new_request_obj,
						arg_get_func=lambda name, default=None: self.request.get(name, default),
						arg_getall_func=lambda name: self.request.get_all(name)
					)
					new_request_obj.required_args = base_request.required_args
					missing_required_args = list(set(missing_arguments).intersection(new_request_obj.required_args))
					apiRef.parameters = {
						'name': base_request.__class__.__name__,
						"object": new_request_obj
					}
					if missing_required_args:
						self.response.set_status(400)
						missing_arg_response = {"missing_arguments": missing_required_args}
						return missing_arg_response, ApiResponse(missing_arg_response, apiRef, 400)
				if hasattr(self, "request_type"):
					if not self.request_type == req_type:
						return None, apiRef
				setattr(self, "parsed_arguments", new_request_obj)
				try:
					result = func(self, *args, **kwargs)
				except [Exception, ValueError]:
					e_type, e_value, e_tb = sys.exc_info()
					result = {'exception': {
						"type": "{}".format(e_type),
						"value": "{}".format(e_value),
						"traceback": traceback.format_tb(e_tb)
					}}
					self.response.set_status(500, e_value.message)
					result_string = json.dumps(result, indent=2, sort_keys=True)
					self.critical(result_string)
					logging.critical(result_string)
				status = int(self.response._status.split(' ')[0])
				return result, ApiResponse(result, apiRef, status)
			wrapped_api.response_type = response_type
			wrapped_api.request_type = req_type
			wrapped_api.description = func.__doc__
			wrapped_api.base_request = base_request
			api_methods[func.__name__] = wrapped_api
			return wrapped_api
		return wrapper

	api_registrar.all = api_methods
	return api_registrar
