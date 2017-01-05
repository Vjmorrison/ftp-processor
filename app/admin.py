
import basemodule
import webapp2
import healthcheck
import coms.entitydefs as entitydefs
from google.appengine.ext import ndb
from coms.requests import BaseRequestObject
from coms.di_ndb import BaseModel


class PollHistoryRequest(BaseRequestObject):
	alert_key = ""


class AdminHandler(basemodule.BaseApiHandler):

	test_method = healthcheck.test_registry()
	api_method = basemodule.api_registry()

	@api_method(req_type=basemodule.GET_METHOD)
	def delete_all_entities(self):
		exceptions = []
		num_deleted = 0
		for item in BaseModel.query().__iter__(keys_only=True):
			try:
				item.delete()
				num_deleted += 1
			except Exception, e:
				exceptions.append(e)
				continue
		return {'num_deleted': num_deleted, 'exceptions': exceptions}

	@api_method(
		req_type=basemodule.GET_METHOD,
		base_request=entitydefs.EntityRequest(required_args=['kind', 'arguments'])
	)
	def add_entity(self):
		entity = self.parsed_arguments.process_entity_request()
		entity.put()
		return entity

	@api_method(
		req_type=basemodule.GET_METHOD,
		base_request=entitydefs.EntityRequest(required_args=['kind', 'urlsafe_key'])
	)
	def remove_entity(self):
		entity = self.parsed_arguments.process_entity_request()
		entity.delete()
		return True

	@api_method(
		req_type=basemodule.GET_METHOD,
		base_request=entitydefs.EntityRequest(required_args=['kind', 'arguments', 'urlsafe_key'])
	)
	def update_entity(self):
		entity = self.parsed_arguments.process_entity_request()
		entity.put()
		return entity

	@api_method(req_type=basemodule.GET_METHOD)
	def get_entity_defs(self):
		return entitydefs.get_all_entities()

	@api_method(req_type=basemodule.GET_METHOD, base_request=entitydefs.EntityRequest(required_args=["kind"]))
	def get_entity(self):
		if self.parsed_arguments.urlsafe_key:
			result = self.parsed_arguments.process_entity_request()
			if not result:
				return []
			if not isinstance(result, list):
				result = [result]
			return result
		else:
			raw_entity = self.parsed_arguments.process_entity_request()
			if not self.request.get('arguments'):
				query = raw_entity.query()
			else:
				sorted_keys = sorted(self.parsed_arguments.arguments.get_arg_names())
				query = None
				for key in sorted_keys:
					if key in self.request.get('arguments'):
						if query:
							query.filter(ndb.AND(ndb.GenericProperty(key) == getattr(self.parsed_arguments.arguments, key)))
						else:
							query = raw_entity.query(ndb.GenericProperty(key) == getattr(self.parsed_arguments.arguments, key))
			all_results = query.fetch()
			return all_results


class AdminHeathCheckHandler(healthcheck.HeathCheckMixIn, AdminHandler):
	pass


app = webapp2.WSGIApplication([
	('/api/.*', AdminHandler),
	('/task/.*', AdminHandler),
	('/healthcheck', AdminHeathCheckHandler),
], debug=True)
