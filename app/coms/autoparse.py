import json
import urlparse


class AutoParseObject(object):

	@classmethod
	def get_arg_names(cls, entity=None):
		if not entity:
			entity = cls
		return [attr for attr in dir(entity) if not callable(getattr(entity, attr)) and not attr.startswith("_")]

	@classmethod
	def parse_arguments(cls, return_object=None, arg_get_func=None, arg_getall_func=None):
		"""Arguments are passed as class members within a return object.  The values given are used to determine response
		type as well as provide default values if missing
		Returns: The found values are inserted into the returnObject.  Missing arguments are returned as a list of arg names"""

		missing_args = []
		if hasattr(return_object, "get_arg_names"):
			arg_names = return_object.get_arg_names()
		else:
			arg_names = cls.get_arg_names(entity=return_object)
		for key in arg_names:
			try:
				if hasattr(return_object, "is_runtime_arg") and return_object.is_runtime_arg(key):
					return_object.init_runtime_arg(key)

				defaultValue = getattr(return_object, key)
				value = cls._get_argument(
					name=key,
					default=defaultValue,
					required=True,
					get_func=arg_get_func,
					getall_func=arg_getall_func
				)
				setattr(return_object, key, value)
			except TypeError, e:
				missing_args.append(key)

		return missing_args

	@classmethod
	def _get_argument(cls, name, get_func=None, getall_func=None, default=None, required=False):
		if cls._argument_is_sequence(default) and not hasattr(default, "keys"):
			foundValue = getall_func(name)
		else:
			foundValue = get_func(name, None)
			if cls._argument_is_sequence(foundValue):
				foundValue = foundValue[0]

		if isinstance(default, bool):
			try:
				if foundValue.lower() == "false":
					foundValue = False
				else:
					foundValue = True
			except AttributeError:
				if foundValue:
					foundValue = True
				else:
					foundValue = False

		if isinstance(default, dict) or hasattr(default, "__dict__"):
			if isinstance(foundValue, basestring):
				try:
					foundValue = json.loads(foundValue)
				except ValueError:
					foundValue = urlparse.parse_qs(foundValue)
					foundValue = {pair[0]: pair[1][0] for pair in foundValue.iteritems()}
			elif foundValue is None:
				foundValue = {}
			else:
				raise TypeError("Value supplied must be a string since the target value is an object")
			if hasattr(default, "__dict__"):
				raw_data = foundValue

				def get_property(prop_name, prop_default=None):
					return raw_data.get(prop_name, prop_default)
				if callable(default):
					foundValue = default()
					cls.parse_arguments(foundValue, arg_get_func=get_property, arg_getall_func=get_property)
				else:
					foundValue = default.__class__()
					foundValue = cls.parse_arguments(foundValue, arg_get_func=get_property, arg_getall_func=get_property)
		if not foundValue:
			foundValue = default

		if required and not foundValue:
			raise TypeError("'{parameter}' was not given and is a required argument".format(parameter=name))
		return foundValue

	@classmethod
	def _argument_is_sequence(cls, arg):
		return not hasattr(arg, "strip") and hasattr(arg, "__getitem__") or hasattr(arg, "__iter__")

	def init_runtime_arg(self, arg_name):
		pass

	def is_runtime_arg(self, arg_name):
		return False
