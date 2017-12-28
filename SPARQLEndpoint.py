#!/usr/bin/python
# -*- coding: utf-8 -*-

from SPARQLWrapper import *
from SPARQLWrapper.Wrapper import QueryResult, QueryBadFormed, EndPointNotFound, EndPointInternalError
# from time import *
from urllib2 import HTTPError
import time as t
import sys, json
import csv
import imp
# imp.reload(sys)
# sys.setdefaultencoding('utf-8')

def SPARQLQuery(queryString, url = "http://dbpedia.org/sparql", returnFullJSON = False, hasRequested = 0):
	hasRequested += 1 
	try:
		sparql = SPARQLWrapper(url)
		prefix = """
		PREFIX owl: <http://www.w3.org/2002/07/owl#>
		PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
		PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
		PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
		PREFIX foaf: <http://xmlns.com/foaf/0.1/>
		PREFIX dc: <http://purl.org/dc/elements/1.1/>
		PREFIX : <http://dbpedia.org/resource/>
		PREFIX dbp: <http://dbpedia.org/property/>
		PREFIX dbo: <http://dbpedia.org/ontology/>
		PREFIX dbpedia: <http://dbpedia.org/>
		PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
	    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
		"""
		sparql.setQuery(prefix+queryString)
		sparql.setReturnFormat(JSON)
		results = sparql.query()
		dict = results.convert()
		# print json.dumps(dict, indent = 4)
		if not returnFullJSON:
			columnHeader = dict['head']['vars']
			rows = dict['results']['bindings']
			return rows, columnHeader
		else:
			return dict 
	except (EndPointInternalError, EndPointNotFound, HTTPError) as e:
		if hasRequested > 20:
			# print 'SPARQL Query Error more than 20 times.'
			# print e
			raise
		t.sleep(5)
		return SPARQLQuery(queryString, url, returnFullJSON, hasRequested)

def printResults(rows, columnHeader):
	print(('\t'.join(columnHeader)))
	for row in rows:
		line = []
		for col in columnHeader:
			if col in row:
				if 'datatype' in row[col]:
					line.append(row[col]['value']+"^^("+row[col]['datatype']+")")
				else:
					line.append(row[col]['value'])
			else:
				line.append('-')
		# line = [row[col]['value'] if col in row else '-' for col in columnHeader]
		print(('\t'.join(line)))

def writeCSV(filename, rows):
	fn = filename + t.strftime("-%Y%m%d-%H%M%S", t.localtime()) + '.csv'
	with open(fn, 'wb') as f:
		writer = csv.writer(f)
		writer.writerows(rows)
