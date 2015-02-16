from django.shortcuts import render,get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.views import generic
from django.contrib.gis.geos import Point
from djgeojson.serializers import Serializer as GeoJSONSerializer
from django.contrib.gis.geos import *
from django.contrib.gis.measure import Distance, D
from django.views.decorators.csrf import csrf_exempt
#apparently simplejson is depreciated...
#Django deprecates simplejson in favor of Python's built-in json module.
from django.core import serializers
import json
import time
import datetime
import pdb
import requests
import yaml
import urllib

from entries.models import *

import difflib

import django
django.setup()

# Create your views here.
class IndexView(generic.ListView):
	template_name = 'entries/index.html'
	context_object_name = 'latest_EffortInstance_list'
	
	def get_queryset(self):
		"""Return the last five published EffortInstances."""
		return EffortInstance.objects.order_by('-date_start')[:15]
    
#not sure what this does anymore    
def results(request, entries_id):
    entry = get_object_or_404(EffortInstance, effort_instance_id=entries_id)
    return render(request, 'entries/results.html', {'entry': entry})

#disables csrf token validation on this view
@csrf_exempt
def data_import(organization,lat,lon,input_point,service_list):
		
	print('time to create a new org')
	#before I used AJAX...
	#return HttpResponseRedirect('/entries/test_form/')

	#if it is a new organization name and in a new location then create new entry in DB

	the_55s = EffortInstance.objects.filter(effort_instance_id__startswith=55)
	print('55: ')
	print(the_55s)
	if the_55s:
		print('incrementing...')
		list_of_55s = []
		for i in the_55s:
			list_of_55s.append(i.effort_instance_id)
		highest_55 = max(list_of_55s)
		print('highest_55')
		print(highest_55)
		left_two = str(highest_55)[:2]
		to_the_right = str(highest_55)[2:]
		
		increment_one = int(to_the_right) + 1
		new_id = left_two + str(increment_one)
	else:
		new_id = 551
		
	print('new_id: ')
	print(new_id)
	
	#http://stackoverflow.com/questions/13890935/timestamp-python
	ts = time.time()
	utc_datetime = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

	EffortInstanceObj = EffortInstance()
	EffortInstanceObj.effort_instance_id = new_id
	
	EffortInstanceObj.updated_on = utc_datetime
	EffortInstanceObj.updated_by = 'HOS registration'
	
	#make a default effort instance
	EffortInstanceObj.default = True

	#Create ServiceProvider
	ServiceProviderObj, created = ServiceProvider.objects.get_or_create(provider_name=organization)
	EffortInstanceObj.service_provider = ServiceProvider.objects.get(provider_name=organization)

	#insert default date for effortInstance
	
	EffortInstanceObj.save()
	
	#Create Location
	loc = Location()
	loc.latitude = str(lat)
	loc.longitude = str(lon)
	loc.save(EffortInstanceObj.effort_instance_id)
	EffortInstanceObj.location = Location.objects.get(id=loc.id)
	EffortInstanceObj.save()

	if loc.geom:
		qs = haiti_adm3_minustah.objects.filter(geom__contains=loc.geom)
		#return HttpResponse(qs[0])
	
		if len(qs):
		
			#return HttpResponse(qs[0].adm3)
			EffortInstanceObj.adm_3 = haiti_adm3_minustah.objects.get(id=qs[0].id)
			
		EffortInstanceObj.save()


	#Create Services
	for x in service_list:
			EffortInstanceServiceObj = EffortInstanceService()
			EffortInstanceServiceObj.effort_instance = EffortInstance.objects.get(effort_instance_id=new_id)

			EffortInstanceServiceObj.effort_service_description = x
			
			#might need to re-factor for different languages
			#EffortInstanceServiceObj.effort_service_type = ServiceType.objects.get(service_name=x)
			EffortInstanceServiceObj.effort_service_type = ServiceType.objects.get(service_name_en=x)

			EffortInstanceServiceObj.save()

	print('saved new org')
	return HttpResponse('saved new org')

	#just consider a simple password for drupal to pass with each post for authentication
	#next step would be https


#disables csrf token validation on this view
@csrf_exempt
def validate(item):

	print('let us begin validation')
	
	organization = item['name']
	if type(organization) is list:
		organization = organization[0]
	
	#print(organization)
	
	print('timestamp before')
	if 'timestamp' in item:
	
		timestamp = item['timestamp']
		if type(timestamp) is list:
			timestamp = timestamp[0]
		
	print('timestamp after')
	
	print('updated_on before')
	if 'updated_on' in item:
	
		updated_on = item['updated_on']
		if type(updated_on) is list:
			updated_on = updated_on[0]
		
	print('updated_on after')
	
	print('updated_by before')
	if 'updated_by' in item:
	
		updated_by = item['updated_by']
		if type(updated_by) is list:
			updated_by = updated_by[0]
		
	print('updated_by after')
	
	print('drupal id before')
	if 'drupal_id' in item:
	
		drupal_id = item['drupal_id']
		if type(drupal_id) is list:
			drupal_id = drupal_id[0]
		
	print('drupal id after')
	
	lat = item['latitude']
	lon = item['longitude']
	
	if type(lat) is list:
		lat = lat[0]
		
	if type(lon) is list:
		lon = lon[0]

	#make them only 15 characters
	#lat_str = lat_str[:15]
	#lon_str = lon_str[:15]

	lat = float(lat)
	lon = float(lon)

	input_point = Point(lon,lat)
	
	print(input_point)
	
	service_list = item['services[]']
	
	if service_list:
		pass
	else:
		service_list = item['services']

	health_facilities_within_100_meters = Location_w_efforts.objects.filter(geom__distance_lt=(input_point, D(m=1000)))
	#print('health_facilities_within_100_meters len')
	#print(len(health_facilities_within_100_meters))
	
	#tests to see if there is an existing organization name that is exactly the same
	try:
		#I needed to do a filter with starts_with for some reason, the good thing anyways is that 
		#it will catch multiple organizations if they all start with the same name
		selected_choice = Location_w_efforts.objects.filter(provider_name__startswith=organization)
		#print(selected_choice)
		#print(len(selected_choice))
		#if there was no matching organization, test if the similarity ration exceeds a certain ratio
		if len(selected_choice)<1:
			#print("testing for a similar result")
			similar_name_list = []
			for i in Location_w_efforts.objects.all():
				#print(difflib.SequenceMatcher(None, organization, i.provider_name).ratio())
				if difflib.SequenceMatcher(None, organization, i.provider_name).ratio() > .95:
					similar_name_list.append(i.provider_name)

	except:
		print("exception")
	else:
		#print("continue...")
		matching_facilities = GeoJSONSerializer().serialize(selected_choice, use_natural_keys=True)
		print('matching facilities')
		print(matching_facilities)
		matching_facilities_list = json.loads(matching_facilities)
		#print("continue..1..2..3...")
	
	#tests to see if there are existing organizations close by
	if len(health_facilities_within_100_meters) > 0:
		nearby_facilities = GeoJSONSerializer().serialize(health_facilities_within_100_meters, use_natural_keys=True) 
		#print("ok...")
		#print(nearby_facilities)
		#print("ok...")
		#nearby_facilities_list = simplejson.loads( nearby_facilities )
		nearby_facilities_list = json.loads(nearby_facilities)
	else:
		nearby_facilities_list= ""
		
	json_data_input_list= {}
	
	#adds matching_facilities_list to json_data_input_list
	if not selected_choice:
		print('selected choice is empty ')
		pass
	if selected_choice:
		json_data_input_list['matching_facilities'] = matching_facilities_list
	
	#adds nearby_facilities_list to json_data_input_list
	if not nearby_facilities_list:
		#print('nearby_facilities_list is empty ')
		pass
	if nearby_facilities_list:
		json_data_input_list['nearby_facilities'] = nearby_facilities_list
		
	try:
		if len(similar_name_list) > 0:
			#print('no matching name, but similar name or names')
			similar_name_list = json.loads(similar_name_list)
			json_data_input_list['similar_names'] = similar_name_list
	except NameError:
  		print("NameError exception")
	else:
	  	#print("next step...")
	  	pass

	json_data = json.dumps(json_data_input_list)
	
	print(json_data)
	
	#helpful link: http://kiaran.net/post/54943617485/serialize-multiple-lists-of-django-models-to-json
	if selected_choice or nearby_facilities_list:
		print('not added to database, check if already exists1')
		#return HttpResponse(json_data,content_type='application/json')
		return json_data
	# if no nearby entry or entry with matching or similar name, then create a new entry
	else:
		data_import(organization,lat,lon,input_point,service_list)
		

def get_hos_data():
	
	#print a list of results: the ones that were added to the Databases, and the ones that 
	#were not because flagged as potential duplicates

	# added (effort instance id, name
	# not added, flagged for duplicates (effort instance id, name, similiar name or close by or both)
	# what about temp table with locations?
	results_dict = {}
	
	#ex. of how to run, $ python -c 'import views; print views.get_hos_data()'
	
	r = requests.get('http://hopeonesource.org/api/org/view-orgs')
	
	r_list = json.loads(r.text)
	#print(r_list[1])
	
	#It is having trouble converting all of the json into a dictionary
	#It works if I break it up into parts
		
	for index, item in enumerate(r_list):

		validate(item)
		
		
		
#disables csrf token validation on this view
@csrf_exempt
def post_request(request):

	item = request.POST
	
	#print(item)
	
	#http://stackoverflow.com/questions/13349573/how-to-change-a-django-querydict-to-python-dict
	#myDict = item.dict()
	myDict = dict(item._iterlists())
	
	print(myDict)

	validate(myDict)
	
	#Since this function is called, you need the HttpResponse inside this function, or else you might get a 500 server error
	return HttpResponse(validate(myDict),content_type='application/json')
		     
def find_facilities(request):

	"""
	Give a lat/lon pair, return the unit(s) surround it.
	"""
	#example of a get request: http://127.0.0.1:8000/find/?lat=18.57&lon=-72.293&buffer=1000
	
	#if request.is_ajax():
	lat = request.GET.get('lat', None)
	lon = request.GET.get('lon', None)
	
	#need a buffer distance...
  	buffer = request.GET.get('buffer', None)
  	
  	#make default buffer value 1000 if it is not specified
  	if not buffer:
  		buffer = 1000
        
    #else: 
    	#msg = "Bad request: no AJAX present"
    	#return HttpResponseBadRequest(msg)
        
	#point = Point(float(lon), float(lat))
	lon = float(lon)
	lat = float(lat)
	point2 = Point(lon,lat)
	
	#test_pnt = Point(-104.93, 39.73)
	

	"""
	Why distance_lt instead of dwithin?
	http://stackoverflow.com/questions/2235043/geodjango-difference-between-dwithin-and-distance-lt
	"""
	facilities = Location_w_efforts.objects.filter(geom__distance_lt=(point2, D(m=buffer)))
	
	#testing query not using Location_w_efforts table
	locations_only = Location.objects.filter(geom__distance_lt=(point2, D(m=buffer)))
	print('printing locations_only')
	print(locations_only)
	
	#https://docs.djangoproject.com/en/1.7/topics/db/examples/one_to_one/
	#need to find all effort instances that have the locations in facilities
	
	efforts_matching_locations_only = EffortInstance.objects.filter(location=locations_only)
	
	print('printing efforts_matching_locations_only')
	print(efforts_matching_locations_only)
	
	'''
	originally I tried .get() , but that returned a MultipleObjectsReturned error
	so I changed it to .filter()
	If there will be more than one result, you need .filter()
	'''

	geojson_data = GeoJSONSerializer().serialize(facilities, use_natural_keys=True) 
	
	return HttpResponse(geojson_data,content_type='application/json')

def shared_servicetype(request):

	#example of a get request: http://127.0.0.1:8000/entries/shared_servicetype/?id=11779
	#11779 should have 7 services
	
	#grabs other health facilities that offer the same type of services
	
	effort_instance_id = request.GET.get('id', None)
	
	print("ok")
	
	if effort_instance_id:
		
		try:
			selected_effort_instance = EffortInstance.objects.get(effort_instance_id=effort_instance_id)
			#related_effort_instances = EffortInstance.objects.filter(__in=selected_effort_instance.EffortInstanceService_set.all)
			
			#http://thebuild.com/blog/2010/12/22/getting-the-id-of-related-objects-in-django/
			#https://docs.djangoproject.com/en/1.6/topics/db/aggregation/
			#The .values is grabbing the unique service names for the selected effort instance
			print("step 1")
			print(selected_effort_instance)
			#all_services_qs = selected_effort_instance.EffortInstanceService_set.all().values('effort_service_type__service_name')
			#for some reason I had to lowercase the table name
			#all_services_qs = selected_effort_instance.effortinstanceservice_set.all().values('effort_service_type__service_name')
			all_services_qs = selected_effort_instance.effortinstanceservice_set.all().values('effort_service_type__service_name_en')
			print("step 2")
			#Python also includes a data type for sets. A set is an unordered collection with no duplicate elements.
			all_services = set([entry['effort_service_type__service_name_en'] for entry in all_services_qs])
			
			print('printing all services:')
			print(all_services)
			
			#The query chain below didn't work because you can't chain a _set.all() after a filter. You can I think after a get
			#ServiceType.objects.filter(service_name__in=['Pharmacy','Malaria']).EffortInstanceService_set.all().values('effort_instance_id')
			
			'''
			Tests that worked:
			print("all Service type objects with 2 picked:")
			print(ServiceType.objects.filter(service_name__in=['Pharmacy','Malaria']))
			
			print("all Service type objects with list picked:")
			print(ServiceType.objects.filter(service_name__in=all_services))
			'''
			
			#http://stackoverflow.com/questions/853184/django-orm-selecting-related-set
			sel_service_types = ServiceType.objects.filter(service_name_en__in=all_services)
			
			print('printing sel_service_types:')
			print(sel_service_types)
			
			
			#You want distinct because many EffortInstanceService objects will link to the same EffortInstance object, so you
			#don't want duplicates of EffortInstance objects selected
			sel_ids = EffortInstanceService.objects.filter(effort_service_type__in=sel_service_types).values('effort_instance_id').distinct()
			
			print("Effort Instances that share at least one service type:")
			print(sel_ids)
		
		except:
			print("exception")
		else:
			print("else")
			return HttpResponse(sel_ids,content_type='application/json')

#http://stackoverflow.com/questions/8230315/python-sets-are-not-json-serializable
class SetEncoder(json.JSONEncoder):
    def default(self, obj):
       if isinstance(obj, set):
          return list(obj)
       return json.JSONEncoder.default(self, obj)


def service_results(self,pk):

	#example of request: http://127.0.0.1:8000/entries/11887/results/
	
	print(pk)
	
	selected_effort_instance = EffortInstance.objects.get(effort_instance_id=pk)
		
	all_services_qs = selected_effort_instance.effortinstanceservice_set.all().values('effort_service_type__service_name_en')
	
	all_services = set([entry['effort_service_type__service_name_en'] for entry in all_services_qs])
	
	print(all_services)
	
	json_data = json.dumps(all_services, cls=SetEncoder)
	
	print(json_data)
	
	return HttpResponse(json_data)
		
    

def all_facilities(request):

	"""
	returns all facilities from temp table
	"""
	
	"""
	Why am I using Location_w_efforts? 
	The serializer failed with Location, there might be a bug with the django-geojson plugin
	It is not handling backwards relations
	http://stackoverflow.com/questions/22898547/error-with-geodjango-serializer-and-foreignkey-field
	"""
	
	facilities = Location_w_efforts.objects.all()
	
	print ('hello')
		
	
	geojson_data = GeoJSONSerializer().serialize(facilities, use_natural_keys=True) 
	
	return HttpResponse(geojson_data,content_type='application/json')
	
	