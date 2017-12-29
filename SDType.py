# -*- coding: utf-8 -*-
from xmlOWL import *
from SPARQLEndpoint import *
import csv, sys, random, io
import numpy as np
from metadata import *
# ============================================
# Basic statistics from http://wiki.dbpedia.org/dbpedia-2016-04-statistics
numAllEntities = 4678230.00
numClasses = len(classList)
numProperties = len(propertyList)
# ============================================
# Helper Functions
def getIndexOfClass(c):
	if c not in classList:
		return None
	return classList.index(c)

def getIndexOfProperty(p, asSubject):
	if p not in propertyList:
		return None
	if asSubject:
		return propertyList.index(p)
	else:
		return numProperties + propertyList.index(p)

def getPropertyOfIndex(idx):
	if idx < 0 or idx >= 2 * numProperties:
		return None
	if idx < numProperties:
		return propertyList[idx]
	else:
		return propertyList[idx - numProperties] + '-1'

def getClassOfIndex(idx):
	if idx < 0 or idx >= numClasses:
		return None
	else: 
		return classList[idx]

# ============================================
# Prior Probability
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
	priorVector = np.zeros(numClasses)
	for c in classList:
		priorVector[getIndexOfClass(c)] = float(countNumEntitiesOfType(c)/numAllEntities)
	with io.open(filename, 'wb') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		writer.writerow(priorVector)
	return priorVector

def loadPriorVector(filename):
	f = open(filename, 'r')
	priorVector = [float(x) for x in f.readline().strip().split(',')]
	print('Finish loading prior vector of ' + str(len(priorVector)) + ' classes.')
	return np.array(priorVector)

# ============================================
# Conditional Probability
def findConditionalProbOfProperty(p, entitySubject = True):
	ansVector = np.zeros(numClasses)

	if entitySubject:
		query = """
		SELECT (COUNT(?s) AS ?count) 
		WHERE {
			?s <%s> [].
		}
		""" % (p)
	else:
		query = """
		SELECT (COUNT(?s) AS ?count) 
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
		SELECT ?type (COUNT(?s) AS ?cnt) WHERE{
		?s <%s> [].
		?s a ?type.
		?type a owl:Class.
		} GROUP BY ?type
		""" % (p)
	else:
		query = """
		SELECT ?type (COUNT(?s) AS ?cnt) WHERE{
		[] <%s> ?s.
		?s a ?type.
		?type a owl:Class.
		} GROUP BY ?type
		""" % (p)
	nrows, ncolumnHeader = SPARQLQuery(query)
	
	for row in nrows:
		idx = getIndexOfClass(row['type']['value'])
		if idx is not None:
			ansVector[idx] = float(row['cnt']['value']) / totalNumEntities





	return ansVector

def precalculateConditionalProb(filename):
	with io.open(filename, 'wb') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		conditionalProbMatrix = []
		for prop in propertyList:
			condProb = findConditionalProbOfProperty(prop, entitySubject = True)
			conditionalProbMatrix.append(condProb)
			writer.writerow(list(condProb))
		for prop in propertyList:
			condProb = findConditionalProbOfProperty(prop, entitySubject = False)
			conditionalProbMatrix.append(condProb)
			writer.writerow(list(condProb))
	return np.array(conditionalProbMatrix)

def loadConditionalProbMatrix(filename):
	conditionalProbMatrix = np.loadtxt(filename, delimiter=',')
	print('Finish loading conditional probabilities of ' + str(len(conditionalProbMatrix)) + ' properties / ' + str(len(conditionalProbMatrix[0])) + ' classes.')
	return conditionalProbMatrix

# ============================================
# Weight-related
def precalculateWeight(filename):
	weightVector = []
	for i in conditionalProbMatrix:
		weightVector.append(np.sum((priorVector - i)**2))
	with io.open(filename, 'wb') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		writer.writerow(weightVector)
	return np.array(weightVector)

def loadWeight(filename):
	f = open(filename, 'r')
	weightVector = [float(x) for x in f.readline().strip().split(',')]
	print('Finish loading weight vector of ' + str(len(weightVector)) + ' properties.')
	return np.array(weightVector)

# ============================================
# Predict type of an entity
def getExistenceVectorOf(entity):
	existenceVector = np.zeros(2 * numProperties)
	query = """
	SELECT ?p (COUNT(?o) AS ?cnt) WHERE{
	<%s> ?p ?o.
	} GROUP BY ?p
	""" % (entity)
	nrows, ncolumnHeader = SPARQLQuery(query)
	for row in nrows:
		idx = getIndexOfProperty(row['p']['value'], asSubject = True)
		if idx is not None:
			existenceVector[idx] = float(row['cnt']['value'])
	query = """
	SELECT ?p (COUNT(?o) AS ?cnt) WHERE{
	?o ?p <%s>.
	} GROUP BY ?p
	""" % (entity)
	nrows, ncolumnHeader = SPARQLQuery(query)
	for row in nrows:
		idx = getIndexOfProperty(row['p']['value'], asSubject = False)
		if idx is not None:
			existenceVector[idx] = float(row['cnt']['value'])
	return existenceVector

def calculateClassVector(entity, ofType = None):
	propExistenceVector = getExistenceVectorOf(entity)
	denominator = np.sum(propExistenceVector*weightVector)
	if ofType is None:
		nominator = np.dot(conditionalProbMatrix.T , propExistenceVector*weightVector)
	else:
		nominator = np.dot(conditionalProbMatrix.T[ofType] , propExistenceVector*weightVector)
	classVector = nominator / denominator
	return classVector

def probOfType(c, entity):
	classIdx = getIndexOfClass(c)
	if classIdx == None:
		return None
	prob = calculateClassVector(entity, ofType = classIdx)
	return prob

def topKTypes(entity, k):
	classVector = calculateClassVector(entity)
	classIndexSorted = np.argsort(classVector)[::-1]
	return [(getClassOfIndex(i), classVector[i]) for i in classIndexSorted[0:k]]

# ============================================
# One-time run 
# priorVector = precalculatePriorProb('PriorVector-Server.csv')
# conditionalProbMatrix = precalculateConditionalProb('ConditionalProbMatrix-Server.csv')
# weightVector = precalculateWeight('WeightVector-Server.csv')
priorVector = loadPriorVector('PriorVector-Server.csv')
conditionalProbMatrix = loadConditionalProbMatrix('ConditionalProbMatrix-Server.csv')
weightVector = loadWeight('WeightVector-Server.csv')
# print(probOfType('http://dbpedia.org/ontology/Country', 'http://dbpedia.org/resource/Australia'))
# print(topKTypes('http://dbpedia.org/resource/Australia',10))
# print(probOfType('http://dbpedia.org/ontology/Genre', 'http://dbpedia.org/resource/Variety_Show'))
# print(topKTypes('http://dbpedia.org/resource/Variety_Show',10))

