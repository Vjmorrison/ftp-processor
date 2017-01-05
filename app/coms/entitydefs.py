import sys

from google.appengine.ext import ndb
from google.net.proto.ProtocolBuffer import ProtocolBufferDecodeError
from requests import BaseRequestObject
import types
import logging
import datetime
import os

from di_ndb import BaseModel


EMAIL = "EMAIL"
SLACK = "SLACK"
SUBSCRIPTION_OPTIONS = [
	EMAIL,
	SLACK
]

WAITING = "WAITING"
IN_PROGRESS = "IN PROGRESS"
DISABLED = "DISABLED"
ERROR = "ERROR"
STATUS = [
	WAITING,
	IN_PROGRESS,
	DISABLED,
	ERROR
]

FILE = "FILE",
DIR = "DIR"
TYPES = [
	FILE,
	DIR,
]

_status_to_log = {
	WAITING: logging.INFO,
	IN_PROGRESS: logging.INFO,
	ERROR: logging.ERROR,
	DISABLED: logging.WARNING,
}

AND = ndb.AND


def status_to_log(status):
	try:
		return _status_to_log[status]
	except KeyError:
		return logging.NOTSET


class EntityRequest(BaseRequestObject):
	kind = ""
	urlsafe_key = ""
	arguments = ""

	def init_runtime_arg(self, arg_name):
		if arg_name is not "arguments":
			return
		try:
			arg_class = getattr(sys.modules[__name__], self.kind)
		except AttributeError:
			arg_class = BaseModel

		self.arguments = arg_class

	def is_runtime_arg(self, arg_name):
		if arg_name is not "arguments":
			return False
		return True

	def get_arg_names(self, entity=None):
		return ['required_args', 'kind', "urlsafe_key", "arguments"]

	def process_entity_request(self):
		raw_entity = self.get_entity(self.kind, self.urlsafe_key)
		if not raw_entity:
			return None
		return self._update_entity(entity=raw_entity)

	@classmethod
	def get_entity(cls, kind, urlsafe_key=None):
		if urlsafe_key:
			try:
				object_key = ndb.Key(urlsafe=urlsafe_key)
				entity_obj = object_key.get()
				if entity_obj is None:
					return None
				if entity_obj.__class__.__name__ is not kind:
					raise TypeError("The passed Key's class {} does not match the Kind value {}".format(entity_obj.__class__.__name__, kind))
				return entity_obj
			except ProtocolBufferDecodeError:
				return None

		try:
			current_module = sys.modules[__name__]
			class_obj = getattr(current_module, kind)
			entity_obj = class_obj()
		except (AttributeError, KeyError):
			return None

		return entity_obj

	def _update_entity(self, entity):
		for key in entity.get_arg_names():
			setattr(entity, key, getattr(self.arguments, key))
		return entity


def validate_filepath(property, value):
	if not value:
		raise ValueError("filepath cannot be blank")
	return None


class FtpServerInfo(BaseModel):
	server_keyname = ndb.StringProperty(required=True)
	root_folder = None

	@classmethod
	def add_or_get_server(cls, server_keyname):
		new_instance = FtpServerInfo()
		new_instance.server_keyname = server_keyname
		try:
			new_instance.add()
		except ValueError, e:  # already exists
			return e.args[1].get()
		# add Root Folder
		new_instance.root_folder = FtpFileInfo(parent=new_instance.key())
		new_instance.root_folder.filepath='/'
		new_instance.root_folder.file_size = 0
		new_instance.root_folder.type = DIR
		new_instance.modified_date = datetime.datetime.utcnow()
		try:
			new_instance.root_folder.add()
		except ValueError, e:  # already exists
			new_instance.root_folder = e.args[1].get()

		return new_instance

	def get_hashable_arg_values(self):
		return [
			self.server_keyname
		]

	def get_root_folder(self):
		if not self.root_folder:
			children = self.get_children()
			if children:
				self.root_folder = children[0]
		return self.root_folder


class FtpFileInfo(BaseModel):
	full_path = ndb.StringProperty()
	filepath = ndb.StringProperty(validator=validate_filepath, required=True)
	filename = ndb.ComputedProperty(lambda self: self.ftp_path.split('/')[-1])
	extension = ndb.ComputedProperty(lambda self: self.ftp_path.split('.')[-1])
	file_size = ndb.IntegerProperty(required=True)
	modified_date = ndb.DateTimeProperty()
	last_scanned = ndb.DateTimeProperty(auto_now=True)
	object_type = ndb.StringProperty(choices=TYPES)

	def get_hashable_arg_values(self):
		return [
			self.filepath,
			self.file_size,
			self.modified_date.strftime("%Y-%m-%d %H:%M:%S")
		]

	def get_path(self):
		if self.full_path:
			return self.full_path

		parent = self.key().parent().get()
		if parent is FtpServerInfo:
			self.full_path = self.filepath
			return self.filepath

		self.full_path = os.path.join(parent.get_path(), self.filepath)
		return self.full_path

	@classmethod
	def parse_and_add(cls, parent_key, line):
		new_object = FtpFileInfo(parent=parent_key)
		splitline = line.split(';')
		for prop in splitline:
			propsplit = prop.split('=')
			if len(propsplit) == 1:
				new_object.filename = propsplit[0]
				continue
			else:
				propname = prop.split('=')[0]
				propvalue = prop.split('=')[1]
			if propname == 'modify':
				new_object.modified_date = datetime.datetime.strptime(propvalue, "%Y%m%d%H%M%S")
			elif propname == 'size':
				new_object.size = int(propvalue)
			elif propname == 'type':
				new_object.type = propvalue.upper()
		try:
			new_object.add()
		except ValueError:  # already added
			pass

	def refresh(self, ftp_service):
		self.full_path = None
		if self.object_type == FILE:
			file_info = ftp_service.get_file_info(self.get_path())



		pass


class Download(BaseModel):
	ftp_info = ndb.KeyProperty(kind=FtpFileInfo, required=True)
	target_filepath = ndb.StringProperty(validator=validate_filepath, required=True)
	status = ndb.StringProperty(choices=STATUS)
	start_time = ndb.DateTimeProperty()
	end_time = ndb.DateTimeProperty()

	def get_hashable_arg_values(self):
		values = [
			self.target_filepath,
			self.status,
			self.ftp_info.urlsafe()
		]

		return values


def get_all_entities():
	return {name: getattr(sys.modules[__name__], name) for name in dir(sys.modules[__name__]) if isinstance(getattr(sys.modules[__name__], name), (type, types.ClassType)) and issubclass(getattr(sys.modules[__name__], name), BaseModel) and name is not "BaseModel"}

