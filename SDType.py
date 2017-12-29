# -*- coding: utf-8 -*-
from xmlOWL import *
from SPARQLEndpoint import *
import csv, sys, random, io
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

def loadProperties(filename):
	f = io.open(filename, 'r', encoding="utf-8")
	propertyList = list()
	for row in f.readlines():
		propertyList.append(row.strip())
	f.close()
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
		SELECT ?type COUNT(DISTINCT ?s) AS ?cnt WHERE{
		?s <%s> [].
		?s a ?type.
		?type a owl:Class.
		} GROUP BY ?type
		""" % (p)
	else:
		query = """
		SELECT ?type COUNT(DISTINCT ?s) AS ?cnt WHERE{
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

def precalculateConditionalProb(filename, propertyList):
	# f = open(filename, 'w') 
	# conditionalProb = dict()
	# for prop in propertyList:
	# 	condProb = findConditionalProbOfProperty(prop, entitySubject = True)
	# 	conditionalProb[prop] = condProb
	# 	f.write('"' + prop.encode('utf8') + '",' + ','.join(map(str, condProb)) +'\n')
	# for prop in propertyList:
	# 	condProb = findConditionalProbOfProperty(prop, entitySubject = False)
	# 	conditionalProb[prop+'-1'] = condProb
	# 	f.write('"' + prop.encode('utf8')+'-1"' + ',' + ','.join(map(str, condProb)) +'\n')
	# f.close()
	# return conditionalProb

	with io.open(filename, 'wb') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		conditionalProb = dict()
		for prop in propertyList:
			condProb = findConditionalProbOfProperty(prop, entitySubject = True)
			conditionalProb[prop] = condProb
			writer.writerow(list(condProb))
		for prop in propertyList:
			condProb = findConditionalProbOfProperty(prop, entitySubject = False)
			conditionalProb[prop+'-1'] = condProb
			writer.writerow(list(condProb))
	return conditionalProb

def transformConditionalProbFile(filename = 'ConditionalProbability-MalformedCSV.txt'):
	conditionalProb = dict()
	with io.open(filename, 'r', encoding="utf8") as csvfile:
		reader = csv.reader(csvfile, delimiter=',')
		i = 0
		for row in reader:
			i += 1
			if len(row) != 761:
				conditionalProb[','.join(row[0:(len(row)-760)])] = row[(len(row)-760):]
			else:
				conditionalProb[row[0]] = row[1:]	
	with open('ConditionalProbability2.txt', 'w', newline='') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		for prop in conditionalProb.keys():
			writer.writerow(conditionalProb[prop])
	f = open('PropertyList.txt', 'w', encoding = 'utf8')
	for prop in conditionalProb.keys():
		f.write(prop + '\n')
	f.close()	

def loadConditionalProb(propertyList, filename):
	conditionalProb = dict()
	with io.open(filename, 'r', encoding="utf8") as csvfile:
		reader = csv.reader(csvfile, delimiter=',')
		i = 0
		for row in reader:
			conditionalProb[propertyList[i]] = np.array([float(x) for x in row])
			i += 1 
	print('Finish loading conditional probabilities of', len(conditionalProb), 'properties')
	return conditionalProb
# ============================================
# Weight-related
def precalculateWeight(filename, priorProb, conditionalProb):
	f = open(filename, 'w')
	weight = dict()
	prior = np.array(list(priorProb.values()))
	for prop in conditionalProb.keys():
		# print(prior)
		# print(conditionalProb[prop])
		weight[prop] = np.sum((prior - conditionalProb[prop])**2)
		f.write(str(weight[prop])+'\n')
	f.close()
	return weight

def loadWeight(propertyList, filename = 'Weight-Server.txt'):
	f = open(filename, 'r')
	weight = dict()
	i = 0
	for line in f.readlines():
		w = float(line.strip())
		weight[propertyList[i]] = w
		i += 1
	print('Finish loading weights of', len(weight), 'properties')
	return weight
# ============================================
# Predict type of an entity
def probOfType(type, entity):
	return probabilityOfType(type, entity, propertyList, priorProb, conditionalProb, weight)


def probabilityOfType(type, entity, propertyList, priorProb, conditionalProb, weight):
	classVector = calculateClassVector(entity, propertyList, conditionalProb, weight)
	classList = list(priorProb.keys())
	if type not in classList:
		return None
	return classVector[classList.index(type)]

def topKTypes(entity, k):
	return returnTopKTypes(entity, k, propertyList, priorProb, conditionalProb, weight)

def returnTopKTypes(entity, k, propertyList, priorProb, conditionalProb, weight):
	classVector = calculateClassVector(entity, propertyList, conditionalProb, weight)
	classIndexSorted = np.argsort(classVector)[::-1]
	classList = list(priorProb.keys())
	classListSorted = [classList[i] for i in classIndexSorted]
	return [(classListSorted[i], classVector[classIndexSorted[i]]) for i in range(k)]
	# classList = list(priorProb.keys())

def calculateClassVector(entity, propertyList, conditionalProb, weight):
	allRelatedProp = getAllRelatedPropOf(entity, propertyList)
	weightVector = np.array(list(weight.values()))
	conditionalProbMatrix = np.array([conditionalProb[key] for key in conditionalProb.keys()])
	propExistenceVector = np.zeros(len(propertyList))
	for prop in allRelatedProp:
		propExistenceVector[propertyList.index(prop)] = 1.0
	denominator = np.sum(propExistenceVector*weightVector)
	nominator = np.dot(conditionalProbMatrix.T , propExistenceVector*weightVector)
	classVector = nominator / denominator
	print(np.sum(conditionalProbMatrix > 1))
	return classVector

def getAllRelatedPropOf(entity, propertyList):
	allRelatedProp = list()
	query = """
	SELECT DISTINCT ?p WHERE{
	<%s> ?p [].
	}
	""" % (entity)
	nrows, ncolumnHeader = SPARQLQuery(query)
	for row in nrows:
		if row['p']['value'] in propertyList:
			allRelatedProp.append(row['p']['value'])
	query = """
	SELECT DISTINCT ?p WHERE{
	[] ?p <%s>.
	}
	""" % (entity)
	nrows, ncolumnHeader = SPARQLQuery(query)
	for row in nrows:
		if row['p']['value'] in propertyList:
			allRelatedProp.append(row['p']['value']+'-1')
	# print(allRelatedProp)
	return allRelatedProp


# ============================================
# One-time run 
# propertyList = getAllProperties()
propertyList = loadProperties('PropertyList-Server.txt')
# priorProb = precalculatePriorProb('PriorProbability.txt')
conditionalProb = precalculateConditionalProb('ConditionalProbability-ServerBugFix.txt', propertyList)
# weight = precalculateWeight('Weight-Server.txt', priorProb, conditionalProb)
# ============================================
# Load pre-calculated data to run
# propertyList = loadProperties('PropertyList-Server.txt')
# priorProb = loadPriorProb('PriorProbability-Server.txt')
# conditionalProb = loadConditionalProb(propertyList, 'ConditionalProbability-Server.txt')
# weight = loadWeight(propertyList, 'Weight-Server.txt')
# returnTopKTypes('http://dbpedia.org/resource/Safi_Airways', 10, propertyList, priorProb, conditionalProb, weight)
# print(probOfType('http://dbpedia.org/ontology/BasketballLeague', 'http://dbpedia.org/resource/England_B_national_football_team'))
# print(topKTypes('http://dbpedia.org/resource/Variety_show',10))
# priorProb = loadPriorProb()


