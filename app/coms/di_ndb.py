from google.appengine.ext.ndb import polymodel
from google.appengine.ext import ndb
from google.appengine.api import users
import types
import hashlib

SERVICE_USER_ID = "App Engine Service Account"

# (Yes, the datastore uses int32!)
MAX_FETCH_LIMIT = 2 ** 31 - 1


class BaseModel(polymodel.PolyModel):
	last_modified = ndb.DateTimeProperty(auto_now=True)
	last_modified_dis_user_id = ndb.StringProperty()
	unique_hash = ndb.ComputedProperty(lambda self: self.get_unique_hash())

	def set_user(self, user=None, user_id=None):
		if user_id:
			self.last_modified_dis_user_id = user_id
		elif user:
			self.last_modified_dis_user_id = user.user_id()

	def put(self):
		currentUser = users.get_current_user()
		if currentUser:
			self.last_modified_dis_user_id = currentUser.email()
		else:
			self.last_modified_dis_user_id = SERVICE_USER_ID

		return super(BaseModel, self).put()

	@classmethod
	def get(cls, key):
		if isinstance(key, ndb.Key):
			entity = key.get()
		elif isinstance(key, basestring):
			entity = ndb.Key(urlsafe=key).get()
		else:
			return None
		return entity

	@classmethod
	def get_all(cls):
		all_records = cls.query().fetch()
		if not isinstance(all_records, types.ListType):
			all_records = [all_records]
		return all_records

	def get_children(self):
		child_records = self.query().ancestor(self.key())
		if not isinstance(child_records, types.ListType):
			if child_records is None:
				child_records = []
			else:
				child_records = [child_records]
		return child_records

	def get_arg_names(self):
		args_to_remove = set([attr for attr in dir(BaseModel())])
		return [attr for attr in dir(self) if attr not in args_to_remove and not callable(getattr(self, attr)) and not attr.startswith("_")]

	def get_hashable_arg_values(self):
		raise NotImplementedError(
			"get_hashable_args is not implemented for class <{}>".format(self.__class__.__name__))

	def get_unique_hash(self):
		newHash = hashlib.md5()
		for value in self.get_hashable_arg_values():
			newHash.update(str(value))
		return newHash.hexdigest()

	def query_for_uniqueness(self, keys_only=True):
		"""returns a formatted query based on internal values"""
		return self.format_uniqueness_query().fetch(MAX_FETCH_LIMIT, keys_only=keys_only)

	def format_uniqueness_query(self):
		return self.query(self.__class__.unique_hash == self.get_unique_hash())

	def add(self):
		results = self.query_for_uniqueness(keys_only=True)
		if results:
			raise ValueError("Duplicate {classname} found with identical values, "
							"please use that object instead. (urlsafe_key: {key})"
							.format(classname=self.__class__.__name__, key=results[0].urlsafe()), results[0])
		return self.put()

	def add_or_update(self):
		results = self.query_for_uniqueness(keys_only=True)
		if not results:
			added = True
		else:
			results = results[0]
			for arg_name in self.get_arg_names():
				if isinstance(getattr(self.__class__, arg_name), ndb.ComputedProperty):
					continue  # you cannot set computed properties
				current_value = getattr(self, arg_name)
				new_value = getattr(results, arg_name, current_value)
				setattr(self, arg_name, new_value)
			added = False
		self.put()
		return added
