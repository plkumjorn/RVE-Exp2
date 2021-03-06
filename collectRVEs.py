#!/usr/bin/python
# -*- coding: utf-8 -*-

from xmlOWL import *
from SPARQLEndpoint import *
import random, time

def getPropertyRVEStats():
	propertyToCheck = list()
	for uri, op in objectPropertyDict.items():
		if op.range is not None and op.range in classDict:
			propertyToCheck.append((uri, op.range))

	with open('PropertyRVEStatsNoRedirects.csv', 'wb') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		writer.writerow(['Property', 'Range', 'numAllStatements', 'numRVEStatements'])
		for prop in propertyToCheck:
			query = """
			SELECT (COUNT(?s) AS ?cnt)
			WHERE {
				?s <%s> ?o.
			} 
			""" % (prop[0])
			nrows, columnHeader = SPARQLQuery(query)
			numAllStatements = float(nrows[0]['cnt']['value'])

			query = """
			SELECT (COUNT(?s) AS ?cnt)
			WHERE {
				?s <%s> ?o.
				FILTER NOT EXISTS { ?o a <%s>.}
				FILTER NOT EXISTS { ?o <http://dbpedia.org/ontology/wikiPageRedirects> ?r}
			} 
			""" % (prop[0], prop[1])
			nrows, columnHeader = SPARQLQuery(query)
			numRVEStatements = float(nrows[0]['cnt']['value'])
			
			writer.writerow([prop[0], prop[1], numAllStatements, numRVEStatements])

def randomRVEIDs(filename, numRVEs):
	selectedRVEs = list()
	allRVEs = list()
	input_file = csv.DictReader(open(filename))
	for row in input_file:
		for i in range(int(float(row['numRVEStatements']))):
			allRVEs.append((row['Property'], i))
	# print(len(allRVEs))
	selectedRVEs = random.sample(allRVEs, numRVEs)
	return selectedRVEs

def getRVEbyID(property, offset):
	query = """
	SELECT ?s ?o
	WHERE {
		?s <%s> ?o.
		FILTER NOT EXISTS { ?o a <%s>.}
		FILTER NOT EXISTS { ?o <http://dbpedia.org/ontology/wikiPageRedirects> ?r}
	} LIMIT 1 OFFSET %d
	""" % (property, objectPropertyDict[property].range, offset)
	nrows, columnHeader = SPARQLQuery(query)
	return {'s': nrows[0]['s']['value'], 'p': property, 'o': nrows[0]['o']['value'], 'r': objectPropertyDict[property].range, 'id': (property, offset)}

def getRVEDataset(numRVEs):
	selected = randomRVEIDs('PropertyRVEStatsNoRedirects.csv', numRVEs)
	RVEs = list()
	with open('RVEsSampledServer'+ str(numRVEs) + '-' + time.strftime("%Y%m%d%H%M%S") +'.csv', 'wb') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		writer.writerow(['s', 'p', 'o', 'r', 'id'])
		for i in selected:
			rve = dict(getRVEbyID(i[0], i[1]))
			writer.writerow([rve['s'].encode('utf8'), rve['p'].encode('utf8'), rve['o'].encode('utf8'), rve['r'].encode('utf8'), rve['id']])
			RVEs.append(rve)
	return RVEs

# getPropertyRVEStats()
getRVEDataset(300)
