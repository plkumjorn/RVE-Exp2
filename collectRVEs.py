#!/usr/bin/python
# -*- coding: utf-8 -*-

from xmlOWL import *
from SPARQLEndpoint import *

def getPropertyRVEStats():
	propertyToCheck = list()
	for uri, op in objectPropertyDict.items():
		if op.range is not None and op.range in classDict:
			propertyToCheck.append((uri, op.range))

	with open('PropertyRVEStats.csv', 'wb') as csvfile:
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
			} 
			""" % (prop[0], prop[1])
			nrows, columnHeader = SPARQLQuery(query)
			numRVEStatements = float(nrows[0]['cnt']['value'])
			
			writer.writerow([prop[0], prop[1], numAllStatements, numRVEStatements])

getPropertyRVEStats()
