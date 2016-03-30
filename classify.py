# -*- coding: utf-8 -*-
# classify.py - usage: python classify.py info.txt root
# classify audio into different dir according to its type and date
# author: xiao yang <xiaoyang0117@gmail.com>
# date: 2016.Mar.30

import os
import json


FILENAME_KEY = u'文件名'
CARD_CARVE_TYPE = u'卡号类型'
CARD_DATE_TYPE = u'日期'
INVALID_CARD_DATE = u'无'

DIRS_STRUCT = { 
			u"浮凸": {
				u"有日期": "", 
				u"无日期": ""}, 
			u"平面": {
				u"有日期": "",
				u"无日期": ""}
			}
DIRS_KEYS_SEQ = (CARD_CARVE_TYPE, CARD_DATE_TYPE)

VALUE_DIRNAME_MAP = {
	u"无": u"有日期",
	u"有效日期": u"无日期",
	u"浮凸": u"浮凸",
	u"平面": u"平面"
}

def classify(info_dict, root):
	filelist = os.listdir(root)

	for filename in filelist:
		info = info_dict[filename]
		try:
			filepath = root
			for dir_key in DIRS_KEYS_SEQ:
				filepath = os.path.join(filepath, VALUE_DIRNAME_MAP[info[dir_key]])
		except KeyError, e:
			print u"unable to recognize info for file: " + filename
			continue

		if os.path.exists(filepath):
			filepath = os.path.join(filepath, filename)
			os.move(os.path.join(root, filename), filepath)
		else:
			print u"path " + filepath + u" is not exist"
			continue


def construct_dirs(root, dirs_struct):
	for sub_dir in traverse_dict(dirs_struct):
		dirs = os.path.join(root, sub_dir)	
		os.makedirs(dirs)

def traverse_dict(dirs_struct):
	assert(type(dirs_struct) == dict)
	sub_dirs = []
	for parent, child in dirs_struct.items():
		if not child:
			yield parent
		else:
			for descendant in traverse_dict(child):
				yield os.path.join(parent, descendant)


def hashing(info_txt):
	info_dict = {}
	with open(info_txt,'r') as f:
		for line in f:
			info = json.loads(line)
			info_dict[info[FILENAME_KEY]] = info
	return info_dict

def main(info_txt, root):
	info_dict = hashing(info_txt)
	construct_dirs(root, DIRS_STRUCT)

	classify(info_dict, root)

if __name__ == '__main__':
	if len(sys.argv) != 3:
		print "python " + sys.argv[0] + "info.txt dirname"
		sys.exit(1)
	info_txt = sys.argv[1]
	root = sys.argv[2]
	main(info_txt, root)