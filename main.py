#!/usr/bin/python
# -*- coding: utf-8 -*-

# ---------------------------------------------------------------------------------------------------
# Basic libraries
import sys, json, csv, re, string, nltk, math, urllib, io, unicodecsv, time
import numpy as np
from nltk.tokenize import RegexpTokenizer
from nltk.stem.porter import *
from nltk.stem.snowball import *
from collections import Counter
tokenizer = RegexpTokenizer(r"[a-zA-Z0-9À-ʯ']+")
stemmer = SnowballStemmer("english", ignore_stopwords = True)
# ---------------------------------------------------------------------------------------------------
# Our methods and helpers
from xmlOWL import *
from SPARQLEndpoint import *
import SDType
# ---------------------------------------------------------------------------------------------------
# Global Variables for this run
linkInCountsMemo = dict()
redirectLinkOf = dict()
rangeLabel = None
correctTypeObjectsDict = None # map entity --> abstract
indexing = None
relatedProperty = None
correlatedProperty = None
weightKeyword = 0
tau = 0.9
# ---------------------------------------------------------------------------------------------------
def loadTestCases(filename):
	testcases = list()
	input_file = unicodecsv.DictReader(open(filename), encoding="utf-8")
	for row in input_file:
		testcases.append({'s': row['s'], 'p': row['p'], 'o': row['o'], 'r':row['r']})
	return testcases

def processATestCase(rve, typeThreshold, method):
	prob = SDType.probOfType(rve['r'], rve['o'])
	if prob > typeThreshold:
		print('Retain the old object', rve['o'], rve['r'], prob)
		return None
	else:
		print('Change the object', rve['o'], rve['r'], prob)
		return getAnswerSortedList(rve['s'], rve['p'], rve['o'], method)

# ---------------------------------------------------------------------------------------------------
# Data Structure
class CandidateObject:
	def __init__(self, uri, assoType, prop, relprop, prob):
		self.uri = uri
		self.associationType = assoType
		self.forProperty = prop
		self.relatedProperty = relprop
		self.conditionalProb = prob
		
		self.score = 0.0
		self.rankFrom = dict()
		self.linkInCount = findLinkInCount(prop, uri)
		self.doc = createDocFromEntity(uri)

		self.matchProfile = dict()
		self.bestLabelMatch = None

class ClueText:
	def __init__(self, lab, prop, relprop, prob):
		self.label = lab
		self.forProperty = prop
		self.relatedProperty = relprop
		self.conditionalProb = prob
		self.relatedness = None
		self.indicatorScore = None
		self.isCapitalKeyword = dict()

		listOfWords = list(set(tokenizer.tokenize(lab)))
		listOfWords = [word for word in listOfWords if word.lower() not in stopwords.words('english') and not word.lower().isdigit()]
		capital = [word[0].isupper() for word in listOfWords]
		listOfWords = [w.lower() for w in listOfWords]
		stemmedWords = [stemmer.stem(word) for word in listOfWords]
		for idx, w in enumerate(stemmedWords):
			self.isCapitalKeyword[w] = capital[idx]

		for idx, w in enumerate(listOfWords):
			if not any(sw in w for sw in stemmedWords):
				stemmedWords.append(w)
				self.isCapitalKeyword[w] = capital[idx]

		self.keywords = stemmedWords
		self.keywordsWeight = dict()
		self.maxLengthMatch = None
		self.matchedURI = dict()
		self.matchedURITotalLinkIn = dict()
		self.matchedURIMaxLinkIn = dict()

	def calculateRelatedness(self, oDoc, useCondProb = True):
		kwInDoc = [kw for kw in self.keywords if kw in oDoc]
		if useCondProb:
			self.relatedness = self.conditionalProb * float(len(kwInDoc)+1)/(len(self.keywords)+1)
		else:
			self.relatedness = float(len(kwInDoc)+1)/(len(self.keywords)+1)

	def calculateKeywordsWeight(self, oDoc):
		for kw in self.keywords:
			if kw in oDoc and self.isCapitalKeyword[kw]:
				self.keywordsWeight[kw] = 1.0
			else:
				self.keywordsWeight[kw] = weightKeyword

# ---------------------------------------------------------------------------------------------------
# Calculation Methods
def getAnswerSortedList(s, p, o, method):
	# Check method name
	possibleMethods = ['keyword', 'graph', 'combined', 'combinedScore']
	if method not in possibleMethods:
		print("Error: Incorrect method command " + method)
		print("Possible choices of method are " + str(possibleMethods))
		sys.exit(0)

	# Preparation
	global op, rangeLabel, correctTypeObjectsDict, indexing, relatedProperty, correlatedProperty
	op = objectPropertyDict[p]
	rangeLabel = getEnglishLabel(op.range)
	correctTypeObjectsDict = getCorrectTypeObjectsDict(op)
	indexing = doIndexing(correctTypeObjectsDict)
	relatedProperty, correlatedProperty = findRelatedProperty(p, op, threshold = tau)
	
	# Create Search Space
	candidateObjects, clueList = getSearchSpace(s, p, o, op, relatedProperty, correlatedProperty, rangeLabel)
	if len(candidateObjects) == 0:
		return []	

	# Calculate Score
	if method.startswith('keyword'):
		sortedCandidateObjects = calculateScoreKeyword(candidateObjects, s, p, o, clueList)
	elif method.startswith('graph'):
		sortedCandidateObjects = calculateScoreGraph(candidateObjects, s, p, o)
	elif method == 'combined':
		sortedCandidateObjects = calculateScoreCombineMethod(candidateObjects, s, p, o, clueList)
	elif method == 'combinedScore':
		sortedCandidateObjects = calculateScoreCombineScoreMethod(candidateObjects, s, p, o, clueList)
	return sortedCandidateObjects

def calculateScoreGraph(candidateObjects, s, p, o): # Use graph structure
	ref = o 
	query = """
	SELECT ?o (COUNT (DISTINCT ?o1) as ?cnt) WHERE {
	{ ?o ?p1 ?o1 } UNION  { ?o1 ?p1 ?o } .
	{ <%s> ?p2 ?o1 } UNION  { ?o1 ?p2 <%s> } .
	?o a <%s>.
	?o1 a owl:Thing.
	FILTER (?p1 != rdf:type && ?p2 != rdf:type).
	} GROUP BY ?o  ORDER BY DESC(?cnt)
	""" % (ref,ref,op.range)
	nrows, ncolumnHeader = SPARQLQuery(query)
	for row in nrows:
		if row['o']['value'] in candidateObjects:
			candidateObjects[row['o']['value']].score = float(row['cnt']['value'])
	for obj in candidateObjects.values():
		if '3' in obj.associationType:
			obj.score += 1 # for 1 hob path

	sortedCandidateObjects = candidateObjects.values()
	sortedCandidateObjects.sort(key = lambda x: (x.score,len(x.associationType), x.linkInCount), reverse = True)
	return sortedCandidateObjects

def calculateScoreKeyword(candidateObjects, s, p, o, clueList): # Use Keyword Search 
	incorrectObjectLabel = o.replace('http://dbpedia.org/resource/', '').lower() 
	incorrectObjectAllDoc = createDocFromEntity(o, use = "allDoc")
	for key in clueList.keys():
		clue = clueList[key]
		clue.calculateRelatedness(incorrectObjectAllDoc, useCondProb = False)
		clue.calculateKeywordsWeight(incorrectObjectAllDoc)
		print(clue.label, clue.relatedness)
		print(clue.keywordsWeight)

	for candidate in candidateObjects.values():
		docWords = tokenize(candidate.doc)
		sumScore = 0.0
		for key, clue in clueList.iteritems(): 
			if sum(clue.keywordsWeight.values()) == 0:
				continue
			score = 0.0
			for kw in clue.keywords:
				if kw in docWords or kw in tokenize(candidate.uri.replace('http://dbpedia.org/resource/', '')):
					score += clue.keywordsWeight[kw]
			sumScore += float((score + 1)) / (len(clue.keywords)+1)

		if '1' in candidate.associationType and candidate.conditionalProb > tau:
			if '3' in candidate.associationType or removeNamespace(candidate.uri).strip().lower().replace('_',' ') in incorrectObjectAllDoc:
				sumScore += 1

		candidate.score = sumScore

	sortedCandidateObjects = candidateObjects.values()
	sortedCandidateObjects.sort(key = lambda x: (x.score,len(x.associationType), x.linkInCount), reverse = True)
	return sortedCandidateObjects

def calculateScoreCombineMethod(candidateObjects, s, p, o, clueList): # Combine Graph Structure and Keyword Search
	# Score from graph method
	calculateScoreGraph(candidateObjects, s, p, o)
	tempSort = candidateObjects.values()
	tempSort.sort(key = lambda x:(x.score,len(x.associationType), x.linkInCount), reverse = True)
	for rank, item in enumerate(tempSort):
		item.rankFrom['graph'] = rank+1
		item.score = 0.0

	# Score from keyword method
	calculateScoreKeyword(candidateObjects, s, p, o, clueList)
	tempSort = candidateObjects.values()
	tempSort.sort(key = lambda x:(x.score,len(x.associationType), x.linkInCount), reverse = True)
	for rank, item in enumerate(tempSort):
		item.rankFrom['keyword'] = rank+1
		# Combine Score
		item.score = -((item.rankFrom['keyword'] + item.rankFrom['graph']) / 2.0)

	sortedCandidateObjects = candidateObjects.values()
	sortedCandidateObjects.sort(key = lambda x: (x.score,len(x.associationType), x.linkInCount), reverse = True)
	return sortedCandidateObjects

def calculateScoreCombineScoreMethod(candidateObjects, s, p, o, clueList): # Combine Graph Structure and Keyword Search
	# Score from graph method
	calculateScoreGraph(candidateObjects, s, p, o)
	maxGraphScore = max([x.score for x in candidateObjects.values()])
	for item in candidateObjects.values():
		if maxGraphScore != 0:
			item.rankFrom['graph'] = 1.0*item.score/maxGraphScore
		else:
			item.rankFrom['graph'] = 0.0
		item.score = 0.0

	# Score from keyword method
	calculateScoreKeyword(candidateObjects, s, p, o, clueList)
	maxKeywordScore = max([x.score for x in candidateObjects.values()])
	for item in candidateObjects.values():
		if maxKeywordScore != 0:
			item.rankFrom['keyword'] = 1.0*item.score/maxKeywordScore
		else:
			item.rankFrom['keyword'] = 0.0
		# Combine Score
		item.score = ((item.rankFrom['keyword'] + item.rankFrom['graph']) / 2.0)

	sortedCandidateObjects = candidateObjects.values()
	sortedCandidateObjects.sort(key = lambda x: (x.score,len(x.associationType), x.linkInCount), reverse = True)
	return sortedCandidateObjects

def getSearchSpace(s, p, o, op, relatedProperty, correlatedProperty, rangeLabel):
	candidateObjects = dict()
	# print "Related Property:"
	# for r in relatedProperty.iterkeys():
	# 	print r
	# print "Correlated Property"
	# for r in correlatedProperty.iterkeys():
	# 	print r
	# --------------------- // Type 1 // ---------------------
	query = """
	SELECT ?a, ?p
	WHERE {
		<%s> ?p ?a.
		?a a <%s>.
	}
	""" % (s, op.range)
	nrows, ncolumnHeader = SPARQLQuery(query)
	for objectRow in nrows:
		if objectRow['p']['value'] in relatedProperty:
			if objectRow['a']['value'] not in candidateObjects:
				newCandidate = CandidateObject(uri = objectRow['a']['value'], assoType = '1', prop = p, relprop = objectRow['p']['value'], prob = relatedProperty[objectRow['p']['value']][5])
				candidateObjects[objectRow['a']['value']] = newCandidate
			else:
				if candidateObjects[objectRow['a']['value']].conditionalProb < relatedProperty[objectRow['p']['value']][5]:
					candidateObjects[objectRow['a']['value']].relatedProperty = objectRow['p']['value']
					candidateObjects[objectRow['a']['value']].conditionalProb = relatedProperty[objectRow['p']['value']][5]

	# print 'Type1'
	# for key, val in candidateObjects.iteritems():
	# 	print key, val.associationType, val.relatedProperty
	# --------------------- // Type 2 // ---------------------
	# 2.1 Find clues from correlatedProperty
	incorrectObjectLabel = getEnglishLabel(o)
	clueList = dict()
	clueList[incorrectObjectLabel] = ClueText(lab = incorrectObjectLabel, prop = p, relprop = p, prob = 1)

	if len(correlatedProperty) > 0:
		query = """
		SELECT ?a ?p
		WHERE { 
			<%s> ?p ?a.
			FILTER NOT EXISTS {?a a <%s>.}
			FILTER (
		""" % (s, op.range)

		filterProperty = ["""(?p = <%s>)""" % (key) for key in correlatedProperty.keys()]
		query += """ || """.join(filterProperty)
		query += """) }"""
		nrows, ncolumnHeader = SPARQLQuery(query)
		
		for objectRow in nrows:
			if objectRow['a']['type'] == 'literal':
				if len(tokenizer.tokenize(objectRow['a']['value'])) > 0: # If the label has keywords
					clueList[objectRow['a']['value']] = ClueText(lab = objectRow['a']['value'], prop = p, relprop = objectRow['p']['value'], prob = correlatedProperty[objectRow['p']['value']][-1])
			elif objectRow['a']['type'] == 'uri':
				lab = removeNamespace(objectRow['a']['value']) 
				if len(tokenizer.tokenize(lab)) > 0: # If the label of uri has keywords
					clueList[lab] = ClueText(lab = lab, prop = p, relprop = objectRow['p']['value'], prob = correlatedProperty[objectRow['p']['value']][-1])

	# print '--> Clue Strings'
	# for key, value in clueList.iteritems():
	# 	print value.label, value.relatedProperty, value.conditionalProb, value.keywords

	# 2.2 Find keywords from clues
	# print "Clue Texts"
	allKeywords = []
	for key in clueList.keys():
		val = clueList[key]
		allKeywords.extend(val.keywords)
		# print key
	allKeywords = list(set(allKeywords))

	ignoreWords = list(set(tokenizer.tokenize(rangeLabel)))
	ignoreWords.extend([stemmer.stem(word) for word in ignoreWords])
	ignoreWords = list(set(ignoreWords))

	allKeywords = [kw for kw in allKeywords if kw not in ignoreWords and kw not in rangeLabel and len(kw) >= 4]
	# print allKeywords

	# 2.3 Find objects from keywords
	if len(allKeywords) > 0:
		# Search from inverted index
		cList = [] # Candidate List
		for kw in allKeywords:
			if kw not in indexing:
				continue
			else:
				cList.extend([profile[0] for profile in indexing[kw]])
		cList = list(set(cList))
		for uri in cList:
			if uri not in candidateObjects:
				newCandidate = CandidateObject(uri = uri, assoType = '2', prop = p, relprop = None, prob = None)
				candidateObjects[uri] = newCandidate
			else:
				candidateObjects[uri].associationType += '2'

	# print 'Type2'
	# for key, val in candidateObjects.iteritems():
	# 	print key, val.associationType, val.relatedProperty

	# --------------------- // Type 3 // ---------------------
	query = """
	SELECT ?p ?a
	WHERE {
	  { <%s> ?p ?a }
	  UNION
	  { ?a ?p <%s> }
	  ?a a <%s>.
	}
	""" % (o, o, op.range)
	nrows, ncolumnHeader = SPARQLQuery(query)

	for objectRow in nrows:
		if objectRow['a']['value'] not in candidateObjects:
			newCandidate = CandidateObject(uri = objectRow['a']['value'], assoType = '3', prop = p, relprop = objectRow['p']['value'], prob = None)
			candidateObjects[objectRow['a']['value']] = newCandidate
		else:
			if '3' not in candidateObjects[objectRow['a']['value']].associationType:
				candidateObjects[objectRow['a']['value']].associationType += '3'

	# print 'Type3'
	# for key, val in candidateObjects.iteritems():
	# 	print key, val.associationType, val.relatedProperty
	# return candidateObjects, clueList
	# --------------------- // Filter Out // ---------------------
	# for uri in candidateObjects.keys():
	# 	if len(candidateObjects[uri].associationType) == 1 and candidateObjects[uri].linkInCount == 0:
	# 		candidateObjects.pop(uri, None)
	return candidateObjects, clueList

def findRelatedProperty(uri, op, threshold):
	# Find related properties
	query = """
	SELECT ?p (COUNT(?s) AS ?count) 
	WHERE {
		?s ?p ?o.
		?s <%s> ?o.
		?o a <%s>.
	} GROUP BY ?p
	""" % (uri, op.range)
	cooccurrences, cooccurrencesColumnHeader = SPARQLQuery(query)
	cooccurrencesProperty = [(prop['p']['value'], float(prop['count']['value'])) for prop in cooccurrences]
	if cooccurrencesProperty == []:
		return [], []	
	maxCount = float(max(cooccurrencesProperty, key=lambda x: x[1])[1])
	cooccurrencesProperty = [(prop[0], prop[1], prop[1]/maxCount) for prop in cooccurrencesProperty]

	# Find confidence rate of related property
	relatedProperty = dict()
	correlatedProperty = dict()
	for prop in cooccurrencesProperty:
		if prop[0] != uri:
			query = """
			SELECT (COUNT(?s) AS ?count) 
			WHERE {
				?s <%s> ?o.
				?o a <%s>.
			}
			""" % (prop[0], op.range)
			countThisProp, colhead = SPARQLQuery(query)
			countThisProp = float(countThisProp[0]['count']['value'])
			relatedProperty[prop[0]] = (prop[0], prop[1], maxCount, countThisProp, prop[2], prop[1]/countThisProp)
			if prop[1]/countThisProp >= threshold:
				correlatedProperty[prop[0]] = relatedProperty[prop[0]]
			# Assume that set A is a set of triples with uri as a property, set B is a set of triples with a related property as a property
			# Each tuple in relatedProperty is in form of (relatedPropertyURI, n(A and B), n(A), n(B), P(B|A), P(A|B)) 
			# Our confident weight for this property is P(A|B)

	print('Related Property: '+('\n').join(relatedProperty.keys()))
	print('Correlated Property: '+('\n').join(correlatedProperty.keys()))
	return relatedProperty, correlatedProperty

def getEnglishLabel(o):
	query = """
	SELECT ?lab
	WHERE {
		<%s> rdfs:label ?lab.
		FILTER (langmatches(lang(?lab), "EN"))
	} LIMIT 1
	""" % (o)
	nrows, ncolumnHeader = SPARQLQuery(query)
	if len(nrows) > 0:
		return nrows[0]['lab']['value']
	else:
		return removeNamespace(o).strip().replace('_',' ')

def findLinkInCount(prop, objURI):
	if objURI not in linkInCountsMemo:
		query = """
		SELECT (COUNT(?s) AS ?count) 
		WHERE {
			?s <%s> <%s>.
		}
		""" % (prop, objURI)
		nrows, ncolumnHeader = SPARQLQuery(query)
		linkInCountsMemo[objURI] = float(nrows[0]['count']['value'])
	return linkInCountsMemo[objURI]

def createDocFromEntity(uri, use = "abstract"):
	if use == "abstract":
		if uri in correctTypeObjectsDict:
			return correctTypeObjectsDict[uri]
		else:
			query = """
			SELECT ?abs
			WHERE{
				<%s> dbo:abstract ?abs.
				FILTER (langmatches(lang(?abs), "EN"))
			}
			""" % (uri)
			nrows, ncolumnHeader = SPARQLQuery(query)
			if len(nrows) > 0:
				return nrows[0]['abs']['value'].lower()
			else: # return label
				return uri.replace('http://dbpedia.org/resource/', '').lower() 
	elif use == "allDoc":
		doc = uri
		query = """
		SELECT ?property ?hasValue ?isValueOf
		WHERE {
		  { <%s> ?property ?hasValue }
		  UNION
		  { ?isValueOf ?property <%s> }
		}
		""" % (uri, uri)
		nrows, ncolumnHeader = SPARQLQuery(query)
		for row in nrows:
			if 'hasValue' in row:
				if 'xml:lang' not in row['hasValue'] or row['hasValue']['xml:lang'] == 'en':
					doc += '\n' + removeNamespace(row['property']['value'])
					doc += ' : ' + removeNamespace(row['hasValue']['value'])
			if 'isValueOf' in row:
				if 'xml:lang' not in row['isValueOf'] or row['isValueOf']['xml:lang'] == 'en':
					doc += '\n' + removeNamespace(row['property']['value'])
					doc += ' ; ' + removeNamespace(row['isValueOf']['value'])			
		return doc.lower()

def getCorrectTypeObjectsDict(op):
	correctTypeObjectsDict = {}	
	i = 0
	while True:
		query = """
		SELECT ?a, ?abs
		WHERE {
		?a a <%s>.
		OPTIONAL {?a dbo:abstract ?abs.
		FILTER (langmatches(lang(?abs), "EN")) }
		} LIMIT 10000 OFFSET %d
		""" % (op.range, i*10000)
		nrows, ncolumnHeader = SPARQLQuery(query)
		if len(ncolumnHeader) == 0:
			i += 1
			continue
		if len(nrows) == 0:
			break
		for row in nrows:
			if 'abs' in row:
				correctTypeObjectsDict[row['a']['value']] = row['abs']['value'].lower()
			else:
				correctTypeObjectsDict[row['a']['value']] = row['a']['value'].lower()
			linkInCountsMemo[row['a']['value']] = 0
		print('1', i)
		i += 1

	i = 0
	while True:
		query = """
		SELECT ?a, COUNT(?s) as ?cnt
		WHERE {
		?a a <%s>.
		?s <%s> ?a.
		} GROUP BY ?a LIMIT 10000 OFFSET %d
		""" % (op.range, op.uri, i*10000)
		nrows, ncolumnHeader = SPARQLQuery(query)
		if len(nrows) == 0:
			break
		for row in nrows:
			linkInCountsMemo[row['a']['value']] = float(row['cnt']['value'])
		print('2', i)
		i += 1

	i = 0
	while True:
		query = """
		SELECT ?a, ?r
		WHERE {
		?a a <%s>.
		?r <http://dbpedia.org/ontology/wikiPageRedirects> ?a.
		} LIMIT 10000 OFFSET %d
		""" % (op.range, i*10000)
		nrows, ncolumnHeader = SPARQLQuery(query)
		if len(nrows) == 0:
			break
		for row in nrows:
			redirectLinkOf[row['r']['value']] = row['a']['value']
		print('3', i)
		i += 1
	return correctTypeObjectsDict

def removeNamespace(stri):
	namespace = ['http://www.w3.org/2002/07/owl#',
		'http://www.w3.org/2001/XMLSchema#',
		'http://www.w3.org/2000/01/rdf-schema#',
		'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
		'http://xmlns.com/foaf/0.1/',
		'http://purl.org/dc/elements/1.1/',
		'http://dbpedia.org/resource/',
		'http://dbpedia.org/property/',
		'http://dbpedia.org/ontology/',
		'http://www.w3.org/2004/02/skos/core#',
		'http://dbpedia.org/class/yago/',
		'http://',
		'www.',
		'wikipedia',
		'wiki'
	]
	for ns in namespace:
		stri = stri.replace(ns, ' ') 
	return stri

def doIndexing(docDict):
	invertedIndex = dict()
	for key in docDict.keys():
		val = docDict[key]
		doc = val.lower()
		doc = tokenizer.tokenize(doc)
		doc = [stemmer.stem(word) for word in doc]
		docIndex = dict(Counter(doc))
		docKeys = docIndex.keys()
		for kw in docKeys:
			if kw in invertedIndex:
				invertedIndex[kw].append((key, kw, docIndex[kw], float(docIndex[kw])/len(doc)))
			else:
				invertedIndex[kw] = [(key, kw, docIndex[kw], float(docIndex[kw])/len(doc))]
	return invertedIndex

def stem_tokens(tokens, stemmer):
	stemmed = []
	for item in tokens:
		stemmed.append(stemmer.stem(item))
	return stemmed

def tokenize(text):
	# tokens = nltk.word_tokenize(text)
	tokens = tokenizer.tokenize(text)
	stems = stem_tokens(tokens, stemmer)
	return stems

def translate_non_alphanumerics(to_translate, translate_to=u'_'):
	not_letters_or_digits = u'!"#%\'()*+,-./:;<=>?@[\]^_`{|}~'
	translate_table = dict((ord(char), translate_to) for char in not_letters_or_digits)
	return to_translate.translate(translate_table)

with open("wordsEn.txt") as word_file:
	english_words = set(word.strip().lower() for word in word_file)

def is_english_word(word):
	return word.lower() in english_words

testFilename = 'RVEsSampledServer300-20171229033026.csv'
method = 'combinedScore'

testcases = loadTestCases(testFilename)
testRange = range(len(testcases))[254:]

f = open('output-'+testFilename[:-4]+'-'+method+ time.strftime("%Y%m%d%H%M%S") +'.csv', 'a')
w = unicodecsv.writer(f, encoding='utf-8')
# w.writerow(['s','p','o','r'])
for k in testRange:
	rve = testcases[k]
	print('Testcase', k, rve['s'], rve['p'], rve['o'], rve['r'])
	sortedCandidates = processATestCase(rve, typeThreshold = 0.4, method = method)
	if sortedCandidates == []:
		w.writerow([k, rve['s'], rve['p'], rve['o'], rve['r'], '-'])
	elif sortedCandidates is not None:
		for i in range(min(25, len(sortedCandidates))):
			print(i+1, sortedCandidates[i].uri, sortedCandidates[i].score) 
		w.writerow([k, rve['s'], rve['p'], rve['o'], rve['r']] + [candidate.uri for candidate in sortedCandidates[0:min(25, len(sortedCandidates))]])
	else:
		w.writerow([k, rve['s'], rve['p'], rve['o'], rve['r'], 'None'])
f.close()



		
