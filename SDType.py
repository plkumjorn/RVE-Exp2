from xmlOWL import *
from SPARQLEndpoint import *
import csv, sys, random
import numpy as np
# ============================================
# Basic statistics from http://wiki.dbpedia.org/dbpedia-2016-04-statistics
numAllEntities = 4678230.00
# ============================================
# PriorProb-related
def indexOfClass(aClass):
	allClasses = list(classDict.keys())
	if aClass in allClasses:
		return allClasses.index(aClass)
	else:
		return None

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
	priorProb = dict()
	for c in classDict.keys():
		f.write(c + '\t' + str(countNumEntitiesOfType(c)/numAllEntities) + '\n')
		priorProb[c] = float(countNumEntitiesOfType(c)/numAllEntities)
	f.close()
	return priorProb

def loadPriorProb(filename = 'PriorProbability.txt'):
	f = open(filename, 'r')
	priorProb = dict()
	for line in f.readlines():
		aTuple = line.strip().split('\t')
		priorProb[aTuple[0]] = float(aTuple[1])
	return priorProb
# ============================================
# ConditionalProb-related
def getAllProperties():
	propertyList = list()
	query = """
	SELECT DISTINCT ?property WHERE {
		{?property a rdf:Property.} UNION {?property a owl:ObjectProperty.} UNION {?property a owl:DatatypeProperty.}
	}
	""" 
	# Select all properties
	nrows, ncolumnHeader = SPARQLQuery(query)
	for row in nrows:
		prop = row['property']['value']
		if prop.startswith('http://dbpedia.org/'):
			propertyList.append(prop)
	return propertyList

def findConditionalProbOfProperty(p, entitySubject = True):
	ansVector = np.zeros(len(classDict.keys()))

	if entitySubject:
		query = """
		SELECT (COUNT(DISTINCT ?s) AS ?count) 
		WHERE {
			?s <%s> [].
		}
		""" % (p)
	else:
		query = """
		SELECT (COUNT(DISTINCT ?s) AS ?count) 
		WHERE {
			[] <%s> ?s.
		}
		""" % (p)
	nrows, ncolumnHeader = SPARQLQuery(query)
	totalNumEntities = float(nrows[0]['count']['value'])
	if totalNumEntities == 0:
		return ansVector

	if entitySubject:
		query = """
		SELECT ?type COUNT(?s) AS ?cnt WHERE{
		?s <%s> [].
		?s a ?type.
		?type a owl:Class.
		} GROUP BY ?type
		""" % (p)
	else:
		query = """
		SELECT ?type COUNT(?s) AS ?cnt WHERE{
		[] <%s> ?s.
		?s a ?type.
		?type a owl:Class.
		} GROUP BY ?type
		""" % (p)
	nrows, ncolumnHeader = SPARQLQuery(query)
	
	for row in nrows:
		idx = indexOfClass(row['type']['value'])
		if idx is not None:
			ansVector[idx] = float(row['cnt']['value']) / totalNumEntities

	return ansVector

def precalculateConditionalProb(filename = 'ConditionalProbability.txt', propertyList):
	f = open(filename, 'w') 
	conditionalProb = dict()
	for prop in propertyList:
		condProb = findConditionalProbOfProperty(prop, entitySubject = True)
		conditionalProb[prop] = condProb
		f.write(prop + ',' + ','.join(map(str, condProb)) +'\n')
	for prop in propertyList:
		condProb = findConditionalProbOfProperty(prop, entitySubject = False)
		conditionalProb[prop+'-1'] = condProb
		f.write(prop+'-1' + ',' + ','.join(map(str, condProb)) +'\n')
	f.close()
	return conditionalProb
# ============================================
# Weight-related
def precalculateWeight(filename = 'Weight.txt', priorProb, conditionalProb):
	f = open(filename, 'w')
	weight = dict()
	prior = np.array(priorProb.values())
	for prop in conditionalProb.keys():
		weight[prop] = np.sum((prior - conditionalProb[prop])**2)
		f.write(prop+'\t'+str(weight[prop]+'\n'))
	f.close()
	return weight

def loadWeight(filename = 'Weight.txt'):
	f = open(filename, 'r')
	weight = dict()
	for line in f.readlines():
		aTuple = line.strip().split('\t')
		weight[aTuple[0]] = float(aTuple[1])
	return weight
# ============================================
# One-time run 
propertyList = getAllProperties()
priorProb = precalculatePriorProb('PriorProbability.txt')
conditionalProb = precalculateConditionalProb('ConditionalProbability.txt', propertyList)
weight = precalculateWeight('Weight.txt', priorProb, conditionalProb)
# ============================================

# priorProb = loadPriorProb()


