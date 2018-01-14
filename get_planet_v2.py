################################################################################################################
#
#    Planet clip downloader 
#
#    Talfan Barnie  30/11/2017
#
#    Any questions contact talfanbarnie@gmail.com or https://github.com/TalfanBarnie
#
#    This script is not guaranteed to not accidentally consume your entire quota by ordering nonsense.
#
#    Use at your own risk!
#
#
#    Notes:
#	(i) This script can't handle requests that retrun > 250 products. Unlikely to be a problem though
#
################################################################################################################





import os, glob, requests, json, subprocess, datetime, time, zipfile, re, os, sys, argparse, importlib, xmltodict
from requests.auth import HTTPBasicAuth
import pandas as pd
import numpy as np
from area import area


# set up parser that takes arguments from the commandline

parser = argparse.ArgumentParser()

parser.add_argument('--path', help='path to folder containing Planet files')

parser.add_argument('--filter', help='file containing filter arguments')

parser.add_argument('--key', help='API key')

args = parser.parse_args()

path = args.path

key = args.key


# get geojson filter

with open(args.filter) as json_data:

    d = json.load(json_data)

    json_data.close()




# catch missing '/' in the path submitted by the user
#if path[-1] != '/':
#	path=path +'/'

###################################################
# find local files
###################################################

# we get metadata from the .xml because we are grown ups

files = glob.glob( os.path.join(path,'*_metadata_clip.xml') )

def get_xml_vars(f):
    with open(f) as ff:
        doc = xmltodict.parse(ff.read())
        try:

            ID = doc['ps:EarthObservation']['gml:metaDataProperty']['ps:EarthObservationMetaData']['eop:identifier']
            date = doc['ps:EarthObservation']['gml:using']['eop:EarthObservationEquipment']['eop:acquisitionParameters']['ps:Acquisition']['ps:acquisitionDateTime']
            filename = doc['ps:EarthObservation']['gml:resultOf']['ps:EarthObservationResult']['eop:product']['ps:ProductInformation']['eop:fileName']
            num_bands = doc['ps:EarthObservation']['gml:resultOf']['ps:EarthObservationResult']['eop:product']['ps:ProductInformation']['ps:numBands']
        except:
            ID = doc['re:EarthObservation']['gml:metaDataProperty']['re:EarthObservationMetaData']['eop:identifier']
            date = doc['re:EarthObservation']['gml:using']['eop:EarthObservationEquipment']['eop:acquisitionParameters']['re:Acquisition']['re:acquisitionDateTime']
            filename = doc['re:EarthObservation']['gml:resultOf']['re:EarthObservationResult']['eop:product']['re:ProductInformation']['eop:fileName']
            num_bands = doc['re:EarthObservation']['gml:resultOf']['re:EarthObservationResult']['eop:product']['re:ProductInformation']['re:numBands']
        return(
            {
                'id':ID,
                'date':date,
                'file':filename,
                'num bands':num_bands
            }
        )


df_local = pd.DataFrame( [get_xml_vars(f) for f in files] )

if not df_local.empty:

	df_local.sort_values('date').reset_index(drop=True)

	# add field to join on - we have to do this because the ids in the xml and in the json returned from the archive don't match

	def get_join_on(r):

		# we tell the difference between products based on the number of bands
		# this will break if a new 3, 4 or 5 band product is added

		if r['num bands']=='5':
			date_string = pd.to_datetime(r['date']).strftime('%Y%m%d')
			sat_num =  re.findall(".*RE(.)_.*",r['file'])[0]
			id0 = date_string  + 'RapidEye-' + sat_num
			return(id0)
		if r['num bands']=='3':
			id0 = os.path.split(r['file'])[1].split('.')[0][:-12] # this is probably broken, may need to change amount of filename that is trimmed from endd
			return(id0)

		if r['num bands']=='4':
			id0 = os.path.split(r['file'])[1].split('.')[0][:-19]
			return(id0)

		return('err')

	df_local['join on'] = df_local.apply(get_join_on,axis=1)

	print(len(df_local[ df_local['num bands']=='5']),' local RapidEye band files found.')
	print(len(df_local[ df_local['num bands']=='3']),' local PlanetScope 3 band files found.')
	print(len(df_local[ df_local['num bands']=='4']),' local PlanetScope 4 band files found.')

else:
	print('No local files found')
#####################################################
# Search API request object
#####################################################

# NOTE! If more than 250 results are found, they will be spread across multiple 'pages'
# currently this script does not handle this

# build the request
search_endpoint_request = {
				  "item_types": ["REOrthoTile","PSScene4Band", "PSScene3Band"],
				  "filter": d
				}

# send it to planet.com and get the json results
result =  requests.post(
			    'https://api.planet.com/data/v1/quick-search',
			    auth=HTTPBasicAuth(key, ''), 
			    json=search_endpoint_request
			)

# if no images are present for the filter, quit
if not json.loads(result.text)['features']:
	print('No images found on server for dates / coords specified in filter')
	quit()
			
# put the results in a dataframe for easy manipulation. For each result, we only need the id and a few of the properties from the json.

df_properties = pd.DataFrame( [r['properties'] for r in json.loads(result.text)['features']]   )[['acquired','item_type','satellite_id']]

df_id = pd.DataFrame( {'id': [r['id'] for r in json.loads(result.text)['features'] ]} )

df_search = pd.concat([df_properties,df_id],axis=1)

print(len(df_search),' number of items returned from the Planet API')

# a number of 4 band PlanetScope images appear to have a 3 band counterpart listed seperately.
# these are unnecessary and will waste our quota, so we filter them out

df_search = df_search.groupby('id').apply(lambda x: x.sort_values('item_type').tail(1)).reset_index(drop=True)

print(len(df_search),' number of items returned from the Planet API after dropping 3 band duplicates')

if df_search.empty:
	print('No images found on Planet server that meet search criteria')
	quit()

# define a column containing strings to join on when joining to the dataframe of local files

def get_join_on(r):
    if 'RapidEye' in r['satellite_id']:
        date_string = pd.to_datetime(r['acquired']).strftime('%Y%m%d')
        return(date_string + r['satellite_id'])
    return(r['id'])#+'_3B')

df_search['join on'] = df_search.apply(get_join_on,axis=1)



print(len(df_search),' images found on Planet Labs servers')


#####################################################
# Get list of files to order
#####################################################


# join dataframe of search results with that of local files
# this gives a df of search results with local file details appended
# if a local file is present

if not df_local.empty:
	df_combined = df_search.join(df_local.set_index('join on'),'join on',lsuffix='_left',rsuffix='_right')



	# select images with no local file - these will be ordered

	df_selected = df_combined[ df_combined['file'].isnull() ]
	
	# make sure 'id' is present to prevent key errors later
	df_selected['id'] = df_selected['id_left']
else:
	df_selected = df_search


print(len(df_selected),' new images to be ordered')

if len(df_selected) ==0:
	quit()

# estimate the total area of the order
print('Estimated total order size is: ',   len(df_selected)  * area(d['config'][0]['config'])/(1000.**2), ' km2. Proceed?')
text = input()
if text not in ['y','Y','yes','Yes','YES']:
	quit()

#####################################################
# Order files
#####################################################
def get_file(r, path, key):
    headers = {
        'Content-Type': 'application/json',
    }


    json = {    
        "aoi": d['config'][0]['config'],
        "targets": [      
             {       
                 "item_id":r['id'],        
                 "item_type":r['item_type'],#"PSScene4Band",        
                 "asset_type": "Analytic"      
             }    ]
    }
    
    # send the 'ship and clip' order
    print('ordering ', r['id'])
    r = requests.post(
        'https://api.planet.com/compute/ops/clips/v1', 
        headers=headers, 
        json=json, 
        auth=(key, '')
    )
    
    print(r.json())
    # check if asset_type exists:
    if 'message' in r.json():
        message = r.json()['message']
        if 'No access to targets' in message:
            print(message)
            return()

    # check image falls within AOI (sometimes it doesn't !?)
    if 'general' in r.json():
        if len(r.json()['general']) >0:
            if 'message' in r.json()['general'][0]:
                if 'AOI does not intersect targets' in r.json()['general'][0]['message']:
                    print('AOI does not intersect targets')
                    return()

    
    # check up on the order, get its states and print it.
    # it will likely still be running
    r3 = requests.get(
        r.json()['_links']['_self'], 
        auth=(key, ''))

    state = r3.json()['state']
    print('Order status: ', state)
    
    # sleeping 60s between checks to avoid annoying the Planet people
    while state == 'running':
        print('Sleeping ...')
        time.sleep(60)
        r3 = requests.get(
            r.json()['_links']['_self'], 
            auth=(key, '')
        )
        state = r3.json()['state']

        print('Order status: ',state)

    # ... when the order has finished, get the download link ...
    url_download = r3.json()['_links']['results'][0]


    # .. get the response for that link ...
    response = requests.get(url_download)

    #and save to a file name built using the order id
    with open( os.path.join(path, r3.json()['id']+'-clips.zip'), 'wb') as f:
        print('Downloading order')
        f.write(response.content) 


for i, r in df_selected.iterrows():
	get_file(r, path, key)



#####################################################
# Unzip files
#####################################################

# extract zip files
print('unzipping files ... ')
files_zip = glob.glob(os.path.join(path,'*.zip'))
for f in files_zip:
    print('unzipping: ',f)
    zip_ref = zipfile.ZipFile(f, 'r')
    zip_ref.extractall(path)
    zip_ref.close()


