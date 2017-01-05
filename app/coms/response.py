
import datetime
import time
from google.appengine.ext import ndb
from autoparse import AutoParseObject


class BaseResponseObject(AutoParseObject):
	pass


class ApiReference(BaseResponseObject):
	api_name = None
	parameters = {}
	module = None

	def __init__(self, func_self, function_ref, arguments):
		if func_self:
			self.module = func_self.__class__.__name__
		else:
			# unbound method
			self.module = function_ref.im_class.__name__

		self.parameters = arguments
		self.api_name = function_ref.__name__


class ApiResponse(BaseResponseObject):
	api_reference = None
	result = None

	def __init__(self, result, api_reference, status_code):
		self.result = result
		self.status_code = status_code
		if not isinstance(api_reference, ApiReference):
			raise TypeError("api_reference must be of type ApiReference (given type {})".format(type(api_reference).__name__))
		self.api_reference = api_reference


def json_encode(obj):
	if isinstance(obj, ndb.Key):
		convertedObject = {
			"urlsafe": obj.urlsafe(),
			"parent": obj.parent(),
			"kind": obj.kind(),
			"app": obj.app(),
			"pairs": obj.pairs()
		}

	elif isinstance(obj, datetime.datetime):
		convertedObject = time.mktime(obj.timetuple())

	elif isinstance(obj, ndb.Property):
		convertedObject = {
			"type": obj.__class__.__name__,
			"choices": obj._choices,
			"default": obj._default,
			"repeated": obj._repeated,
			"required": obj._required,
			"indexed": obj._indexed,
			"verbose_name": obj._verbose_name
		}
		if isinstance(obj, ndb.StructuredProperty):
			convertedObject['structured_type'] = obj._modelclass.__name__

	elif hasattr(obj, "__module__") and not hasattr(obj, "func_dict"):
		object_attr_names = [attr for attr in dir(obj) if not callable(getattr(obj, attr)) and not attr.startswith("_")]
		convertedObject = {}
		for attr_name in object_attr_names:
			convertedObject[attr_name] = getattr(obj, attr_name)

	else:
		convertedObject = obj

	if hasattr(convertedObject, '__iter__'):
		if hasattr(convertedObject, 'keys'):
			for key in convertedObject.keys():
				convertedObject[key] = json_encode(convertedObject[key])
		elif hasattr(convertedObject, 'insert'):
			for index in range(0, len(convertedObject)):
				convertedObject[index] = json_encode(convertedObject[index])
		else:
			convertedObject = [json_encode(item) for item in convertedObject]

	return convertedObject
