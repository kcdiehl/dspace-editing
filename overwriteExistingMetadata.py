import json
import requests
import secrets
import time
import csv
from datetime import datetime
import urllib3
import argparse

secretsVersion = raw_input('To edit production server, enter the name of the secrets file: ')
if secretsVersion != '':
    try:
        secrets = __import__(secretsVersion)
        print 'Editing Production'
    except ImportError:
        print 'Editing Stage'
else:
    print 'Editing Stage'

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--fileName', help='the name of the CSV with handles and file identifiers. optional - if not provided, the script will ask for input')
args = parser.parse_args()
if args.fileName:
    fileName = args.fileName
else:
    fileName = raw_input('Enter file name: ')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

baseURL = secrets.baseURL
email = secrets.email
password = secrets.password
filePath = secrets.filePath
verify = secrets.verify
skippedCollections = secrets.skippedCollections

handleIdDict = {}
with open(fileName) as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        fileIdentifier = row['fileId']
        handle = row['handle']
        handleIdDict[fileIdentifier] = handle
print handleIdDict
id = raw_input('test')

startTime = time.time()
data = {'email':email,'password':password}
header = {'content-type':'application/json','accept':'application/json'}
session = requests.post(baseURL+'/rest/login', headers=header, verify=verify, params=data).cookies['JSESSIONID']
cookies = {'JSESSIONID': session}
headerFileUpload = {'accept':'application/json'}
cookiesFileUpload = cookies
status = requests.get(baseURL+'/rest/status', headers=header, cookies=cookies, verify=verify).json()
print 'authenticated'

collectionMetadata = json.load(open('metadataOverwrite.json'))

f=csv.writer(open(filePath+'metadataOverwrite'+datetime.now().strftime('%Y-%m-%d %H.%M.%S')+'.csv', 'wb'))
f.writerow(['itemID']+['delete']+['post'])

for k,v in handleIdDict.items():
    for itemMetadata in collectionMetadata:
        updatedItemMetadata = {}
        updatedItemMetadataList = []
        for element in itemMetadata['metadata']:
            if element['key'] == 'fileIdentifier':
                fileIdentifier = element['value']
            else:
                updatedItemMetadataList.append(element)
        uriElement = {}
        uriElement['key'] = 'dc.identifier.uri'
        uriElement['value'] = 'http://jhir.library.jhu.edu/handle/' + v
        updatedItemMetadataList.append(uriElement)
        provNote = 'Item metadata updated through a batch process on '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'.'
        provNoteElement = {}
        provNoteElement['key'] = 'dc.description.provenance'
        provNoteElement['value'] = unicode(provNote)
        provNoteElement['language'] = 'en_US'
        updatedItemMetadataList.append(provNoteElement)

        if fileIdentifier == k:
            print fileIdentifier
            endpoint = baseURL+'/rest/handle/'+v
            item = requests.get(endpoint, headers=header, cookies=cookies, verify=verify).json()
            itemID = item['uuid']
            metadata = requests.get(baseURL+'/rest/items/'+str(itemID)+'/metadata', headers=header, cookies=cookies, verify=verify).json()
            for l in range (0, len (metadata)):
                metadata[l].pop('schema', None)
                metadata[l].pop('element', None)
                metadata[l].pop('qualifier', None)
                if metadata[l]['key'] == 'dc.description.provenance':
                    updatedItemMetadataList.append(metadata[l])
                if metadata[l]['key'] == 'dc.date.available':
                    updatedItemMetadataList.append(metadata[l])
                if metadata[l]['key'] == 'dc.date.accessioned':
                    updatedItemMetadataList.append(metadata[l])
            updatedItemMetadata = json.dumps(updatedItemMetadataList)
            delete = requests.delete(baseURL+'/rest/items/'+str(itemID)+'/metadata', headers=header, cookies=cookies, verify=verify)
            print delete
            post = requests.put(baseURL+'/rest/items/'+str(itemID)+'/metadata', headers=header, cookies=cookies, verify=verify, data=updatedItemMetadata)
            print post
            f.writerow([itemID]+[delete]+[post])

logout = requests.post(baseURL+'/rest/logout', headers=header, cookies=cookies, verify=verify)

elapsedTime = time.time() - startTime
m, s = divmod(elapsedTime, 60)
h, m = divmod(m, 60)
print 'Total script run time: ', '%d:%02d:%02d' % (h, m, s)
