from xmlOWL import *
from SPARQLEndpoint import *
import csv, sys, random

# ============================================
# Basic statistics from http://wiki.dbpedia.org/dbpedia-2016-04-statistics
numAllEntities = 4678230.00
# ============================================
def countNumEntitiesOfType(aClass):
	query = """
	SELECT (COUNT(?s) AS ?count) 
	WHERE {
		?s a <%s>.
	}
	""" % (aClass)
	nrows, ncolumnHeader = SPARQLQuery(query)
	return float(nrows[0]['count']['value'])

def precalculatePriorProb(filename):
	f = open(filename, 'w') 
	for c in classDict.keys():
		f.write(c + '\t' + str(countNumEntitiesOfType(c)/numAllEntities) + '\n')
	f.close()
# ============================================
# One-time run 
# precalculatePriorProb('PriorProbability.txt')
# ============================================