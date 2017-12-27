#!/usr/bin/python
# -*- coding: utf-8 -*-

from SPARQLWrapper import SPARQLWrapper, JSON, RDF
import sys, json, importlib
import xml.etree.ElementTree as ET

# importlib.reload(sys)
# sys.setdefaultencoding('utf-8')

class OWLClass:
	def __init__(self, classRoot):
		self.uri = classRoot.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']
		
		self.label = dict()
		for lab in classRoot.iter('{http://www.w3.org/2000/01/rdf-schema#}label'):
			self.label[lab.attrib['{http://www.w3.org/XML/1998/namespace}lang']] = lab.text

		self.comment = dict()
		for ment in classRoot.findall('{http://www.w3.org/2000/01/rdf-schema#}comment'):
			self.comment[ment.attrib['{http://www.w3.org/XML/1998/namespace}lang']] = ment.text
		
		# Version one superclass 
		# self.subClassOf = None
		# superClass = classRoot.find('{http://www.w3.org/2000/01/rdf-schema#}subClassOf')
		# if superClass is not None:
		# 	self.subClassOf = superClass.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']

		# Version many superclasses 
		self.subClassOf = []
		for superClass in classRoot.findall('{http://www.w3.org/2000/01/rdf-schema#}subClassOf'):
			self.subClassOf.append(superClass.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'])

		# Version one disjoint class
		# self.disjointWith = None
		# disjointClass = classRoot.find('{http://www.w3.org/2002/07/owl#}disjointWith')
		# if disjointClass is not None:
		# 	self.disjointWith = disjointClass.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']

		# Version many disjoint classes
		self.disjointWith = []
		for disjointClass in classRoot.findall('{http://www.w3.org/2002/07/owl#}disjointWith'):
			self.disjointWith.append(disjointClass.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'])

		# Version one equivalent class
		# self.equivalentClass = None
		# equiClass = classRoot.find('{http://www.w3.org/2002/07/owl#}equivalentClass')
		# if equiClass is not None:
		# 	self.equivalentClass = equiClass.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']

		# Version many equivalent classes
		self.equivalentClass = []
		for equiClass in classRoot.findall('{http://www.w3.org/2002/07/owl#}equivalentClass'):
			self.equivalentClass.append(equiClass.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'])

		self.wasDerivedFrom = classRoot.find('{http://www.w3.org/ns/prov#}wasDerivedFrom').attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']

class OWLProperty:
	def __init__(self, propertyRoot):
		self.uri = propertyRoot.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']
		
		if propertyRoot.find('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}type') is not None:
			self.type = propertyRoot.find('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}type').attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']
		else:
			self.type = None
		
		self.label = dict()
		for lab in propertyRoot.iter('{http://www.w3.org/2000/01/rdf-schema#}label'):
			self.label[lab.attrib['{http://www.w3.org/XML/1998/namespace}lang']] = lab.text

		self.comment = dict()
		for ment in propertyRoot.findall('{http://www.w3.org/2000/01/rdf-schema#}comment'):
			self.comment[ment.attrib['{http://www.w3.org/XML/1998/namespace}lang']] = ment.text

		dom = propertyRoot.find('{http://www.w3.org/2000/01/rdf-schema#}domain')
		if dom is not None:
			self.domain = dom.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']
		else:
			self.domain = None

		rge = propertyRoot.find('{http://www.w3.org/2000/01/rdf-schema#}range')
		if rge is not None:
			self.range = rge.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']
		else:
			self.range = None

		self.subPropertyOf = []
		for superProperty in propertyRoot.findall('{http://www.w3.org/2000/01/rdf-schema#}subPropertyOf'):
			self.subPropertyOf.append(superProperty.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'])

		self.equivalentProperty = []
		for equiProperty in propertyRoot.findall('{http://www.w3.org/2002/07/owl#}equivalentProperty'):
			self.equivalentProperty.append(equiProperty.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource'])

		if propertyRoot.find('{http://www.w3.org/ns/prov#}wasDerivedFrom') is not None:
			self.wasDerivedFrom = propertyRoot.find('{http://www.w3.org/ns/prov#}wasDerivedFrom').attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource']
		else:
			self.wasDerivedFrom = None

class OWLDatatype:
	def __init__(self, datatypeRoot):
		self.uri = datatypeRoot.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']
		
		self.label = dict()
		for lab in datatypeRoot.iter('{http://www.w3.org/2000/01/rdf-schema#}label'):
			self.label[lab.attrib['{http://www.w3.org/XML/1998/namespace}lang']] = lab.text

		

tree = ET.parse('dbpedia_2016-10.owl')
root = tree.getroot()
print('Initialized dbpedia ontology 2016-04') 

def getClassNameList():
	allClassNames = [cl.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about'] for cl in root.iter('{http://www.w3.org/2002/07/owl#}Class')]
	return allClassNames

def getClassDict():
	classDict = dict()
	for cl in root.iter('{http://www.w3.org/2002/07/owl#}Class'):
		classDict[cl.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']] = OWLClass(cl)
	for uri, owlClass in classDict.items():
		owlClass.allSuperClasses = findAllSuperClasses(classDict, owlClass)
	return classDict

def getDatatypePropertyDict():
	datatypePropertyDict = dict()
	for dtp in root.iter('{http://www.w3.org/2002/07/owl#}DatatypeProperty'):
		datatypePropertyDict[dtp.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']] = OWLProperty(dtp)
	return datatypePropertyDict

def getObjectPropertyDict():
	objectPropertyDict = dict()
	for op in root.iter('{http://www.w3.org/2002/07/owl#}ObjectProperty'):
		objectPropertyDict[op.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']] = OWLProperty(op)
	return objectPropertyDict

def getDatatypeDict():
	datatypeDict = dict()
	for dt in root.iter('{http://www.w3.org/2000/01/rdf-schema#}Datatype'):
		datatypeDict[dt.attrib['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about']] = OWLProperty(dt)
	return datatypeDict

def findTopSuperClass(classDict, owlclass):
	if owlclass.subClassOf[0] == "http://www.w3.org/2002/07/owl#Thing":
		return owlclass.uri
	else:
		return findTopSuperClass(classDict, classDict[owlclass.subClassOf[0]])

def findAllSuperClasses(classDict, owlclass):
	if owlclass.subClassOf[0] == "http://www.w3.org/2002/07/owl#Thing":
		return [owlclass.uri]
	else:
		return findAllSuperClasses(classDict, classDict[owlclass.subClassOf[0]]) + [owlclass.uri]

classDict = getClassDict()
print('No. of classes =', len(classDict))
# print classDict['http://dbpedia.org/ontology/Animal'].subClassOf

datatypePropertyDict = getDatatypePropertyDict()
print('No. of datatypeProperty =', len(datatypePropertyDict))

objectPropertyDict = getObjectPropertyDict()
print('No. of objectProperty =', len(objectPropertyDict))

datatypeDict = getDatatypeDict()
print('No. of datatype =', len(datatypeDict))


# print findTopSuperClass(classDict, classDict["http://dbpedia.org/ontology/Agent"])
# print findTopSuperClass(classDict, classDict["http://dbpedia.org/ontology/Architect"])
# print findTopSuperClass(classDict, classDict["http://dbpedia.org/ontology/Person"])
# print findTopSuperClass(classDict, classDict["http://dbpedia.org/ontology/City"])
# print findTopSuperClass(classDict, classDict["http://dbpedia.org/ontology/Organ"])
