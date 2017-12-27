#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, json, csv, re, string, nltk, random

def ttltsv(path, percentage = 100):
	f = open(path[0:-4]+'_'+str(percentage)+'.tsv', 'w')
	for line in open(path, 'r'):
		if line.startswith('#'):
			continue
		if percentage == 100 or random.randrange(0, 100) < percentage:
			newLine = ('\t').join(line.rstrip('\n').split()[0:-1])+'\n'
			f.write(newLine)
	f.close()		

def learnErrorData(path):
	countDict = {}
	for line in open(path, 'r'):
		if line.startswith('#'):
			continue
		triple = line.rstrip('\n').split()[0:-1]
		if triple[1] not in countDict:
			countDict[triple[1]] = 1
		else:
			countDict[triple[1]] += 1
	countTuple = [(key, val) for key, val in countDict.items()]
	countTuple.sort(key = lambda x: x[1])
	for keyval in countTuple:
		print(keyval)

def getErrorData(path, property):
	for line in open(path, 'r'):
		if line.startswith('#'):
			continue
		triple = line.rstrip('\n').split()[0:-1]
		triple = [t[1:-1] for t in triple]
		if triple[1] == 'http://dbpedia.org/ontology/'+property:
			print(('\t').join(triple))

def getPredictedAnswer(paths):
	# print paths
	ansAll = []
	for path in paths:
		matchTerm = 'Predicted Answer = '
		if path.startswith('f_m0'):
			matchTerm = 'predicted = '
		if path.startswith('f_TransE'):
			matchTerm = 'Predicted Answer (Filter) = '
		ansLine = []
		for line in open(path, 'r'):
			if line.startswith(matchTerm):
				# print line
				ans = line.replace(matchTerm,'').strip().split()[0]
				if ans.startswith('<'):
					ans = ans[1:-1]
				ansLine.append(ans)
				# print 'ans = ', ans
		print(len(ansLine))
		ansAll.append(ansLine)
	ansAllTranspose = list(map(list, list(zip(*ansAll))))
	for row in ansAllTranspose:
		print(('\t').join(row))
# print sys.argv[0], sys.argv[1], sys.argv[2]
# ttltsv('C:\Users\Piyawat (Peter)\Downloads\DBpediaDataForRules\instance_types_en.ttl')
# learnErrorData('C:\Users\Piyawat (Peter)\Downloads\DBpediaDataForRules\mappingbased_objects_disjoint_range_en.ttl')
# getErrorData('C:\Users\Piyawat (Peter)\Downloads\DBpediaDataForRules\mappingbased_objects_disjoint_range_en.ttl', 'team')
getPredictedAnswer([
	'f_m0_employerNew.txt',
	'f_m1_employerNew.txt', 
	'f_m2_employerNew.txt', 
	'f_m3_employerNew.txt',
	'f_m4_employerNew.txt', 
	'f_m5_employerNew.txt', 
	'f_m6_employerNew.txt',
	'f_m7_employerNew.txt',
	'f_m7plus_employerNew.txt',
	'f_m8p1Baseline_employerNew.txt',
	'f_m9GraphBaseline_employerNew.txt',
	'f_m9GraphP1Baseline_employerNew.txt',
	'f_m10_employerNew.txt',
	'f_m11_employerNew.txt',
	'f_m12_employerNew.txt',
	'f_BiJac_employerNew.txt',
	'f_DL_employerNew.txt',
	'f_Dice_employerNew.txt',
	'f_STFIDF_employerNew.txt',
	'f_WikiDis_employerNew.txt'
])
# getPredictedAnswer(['f_TransE_collegeNew.txt'])
# getPredictedAnswer(['f_m12_routeEndNew.txt'])
# getPredictedAnswer(['f_AMIE40Server_languageNew.txt'])
# getPredictedAnswer(['f_AMIE_languageNew.txt', 'f_AMIE40Server_languageNew.txt'])
# getPredictedAnswer('f_m1_employerNew.txt')
# getPredictedAnswer('f_m2_targetAirportNew.txt')
# getPredictedAnswer('f_m3_targetAirportNew.txt')
# getPredictedAnswer('f_m4_targetAirportNew.txt')
# getPredictedAnswer('f_m5_targetAirportNew.txt')
# getPredictedAnswer('f_m6_targetAirportNew.txt')
# getPredictedAnswer('f_m7_targetAirportNew.txt')
# getPredictedAnswer('f_m7plus_targetAirportNew.txt')
# getPredictedAnswer('f_m8p1Baseline_targetAirportNew.txt')
# getPredictedAnswer('f_m9GraphBaseline_targetAirportNew.txt')
# getPredictedAnswer('f_m9GraphP1Baseline_targetAirportNew.txt')
# getPredictedAnswer('f_m10_targetAirportNew.txt')
# getPredictedAnswer('f_m11_targetAirportNew.txt')
# getPredictedAnswer('f_BiJac_targetAirportNew.txt')
# getPredictedAnswer('f_DL_targetAirportNew.txt')
# getPredictedAnswer('f_Dice_targetAirportNew.txt')
# getPredictedAnswer('f_STFIDF_targetAirportNew.txt')
# getPredictedAnswer('f_WikiDis_targetAirportNew.txt')
