# -*- coding: utf-8 -*-
# qualify_textgrid.py - usage: python qualify_textgrid src_file[src_root] [timeit]
# to validate the format of a textgrid
# or to calculate the sum time of text in respectively categories
# author: Xiao Yang <xiaoyang0117@gmail.com>
# date: 2016.02.02
import os
import sys
import re
import codecs
from itertools import cycle
from traverse import traverse


RULES_PATTERNS = (
	(re.compile('^([0-2])?(?(1)(?P<text>.+)|$)', re.UNICODE), lambda x: x.group('text') , u'错误：第{lineno}行不是以特定数字开始或只包含数字，文本内容为“{text}”'),
	(re.compile('^(\D+)$'), lambda x: re.sub('\[[SNTPsntp]\]', '', x.group(0)), u'错误：第{lineno}行除文本开始处外另包含数字，文本内容为“{text}”'),
	(re.compile('((?!\[\w\]).)*$', re.UNICODE), lambda x: x.group(0), u'错误：第{lineno}行噪音符号标识错误，包含非SNTP字符，文本内容为"{text}"'),
	(re.compile('(.{3,})$', re.UNICODE), lambda x: True, u'错误：第{lineno}行文本长度小于3，文本内容为"{text}"'),
)
	
TEXT_KEY = 'text'

class CycleIterator(object):
	""" a wrapper for the itertools.cycle """
	def __init__(self, iterable):
		super(CycleIterator, self).__init__()
		self.iterable = iterable
		self.iterator = cycle(iterable)
		self.value = None
	
	def head(self):
		return self.iterable[0]

	def tail(self):
		return self.iterable[-1]

	def next(self):
		self.value = self.iterator.next()
		return self.value

	def end(self):
		return self.value == self.tail()

	# to loop from the begining
	def reset(self):
		self.iterator = cycle(self.iterable)

	def index(self, i):
		return self.iterable[i]


class TextgridParser(object):
	"""translate the textgrid into a dict"""
	CODINGS = (
		('utf-8-sig', (codecs.BOM_UTF8,)),
		('utf-16', (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)),
		('utf-32', (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)),
		)

	BLOCK_PATTERNS = (
		(re.compile('^\s*intervals \[(?P<slice>\d+)\]:'), 'slice', int),
		(re.compile('^\s*xmin = (?P<xmin>[\d\.]+)'), 'xmin', float),
		(re.compile('^\s*xmax = (?P<xmax>[\d\.]+)'), 'xmax', float),
		(re.compile('^\s*text = "(?P<text>.*)"'), 'text', str),
		)
	# for a special case that a text has multiple lines
	MULTILINES_PATTERN = (
		(re.compile('^\s*text = "(?P<text>.*)'), 'text', str),
		(re.compile('^(?P<text>.*)$'), 'text', str),	# to adapt the new line
		(re.compile('^(?P<text>.*)"\s*$'), 'text', str),
	)

	PATTERN_KEYS = ('pattern', 'key', 'type')

	def __init__(self, coding='utf-8'):
		super(TextgridParser, self).__init__()
		self.default_coding = coding
		self.intervals = []

	def read(self, filename):
		self.filename = filename
		with open(filename, 'r') as f:
			content = f.read()
			self.coding = self.code_det(content[0:10])
			try:
				self.lines = content.decode(self.coding).encode(self.default_coding).splitlines()
			except UnicodeError, e:
				print(u"对文件“%s”进行解码时发生错误，请选择合适的文本编辑器，并以utf-8编码格式保存后，再运行此程序" % filename)
				sys.exit(1)

	def code_det(self, headline, default='utf-8'):
		for enc,boms in TextgridParser.CODINGS:
			if any(headline.startswith(bom) for bom in boms): 
				return enc
		return default

	def pack(self, keys, tuples):
		package = []
		for vals in tuples:
			package.append({ keys[i]:vals[i] for i in range(len(keys)) })
		return package

	def update(self, interval, item_pattern, line, append_mode=False):
		ip = item_pattern
		if append_mode:
			# only for text
			interval[ip['key']] += ip['type'](ip['pattern'].match(line).group(ip['key']))
		else:
			interval.update({ ip['key']: ip['type'](ip['pattern'].match(line).group(ip['key'])) }) 
		return interval

	def match(self, item_pattern, line):
		return item_pattern['pattern'].match(line)

	def append(self, interval):
		pass

	def parse(self):
		print(u'正在解析%s...' % self.filename)
		lineno = 0
		interval = {}
		APPEND_MODE = False
		bp_iter = CycleIterator(self.pack(TextgridParser.PATTERN_KEYS, TextgridParser.BLOCK_PATTERNS))
		mp_iter = CycleIterator(self.pack(TextgridParser.PATTERN_KEYS, TextgridParser.MULTILINES_PATTERN))

		block_begining = bp_iter.head()
		item_pattern = bp_iter.next()
		for line in self.lines:
			lineno += 1

			# reset the block parsing once the line matched the begining pattern
			if self.match(block_begining, line):
				# self.update(interval, block_begining, line)
				# not the start actually, exception occured in parsing last block
				if item_pattern != block_begining:
					print(u'错误：无法解析第%d行，不是textgrid标准格式，已跳过' % (lineno-1))	# last line instead of the current
					interval = {}
					APPEND_MODE = False
					bp_iter.reset()
					item_pattern = bp_iter.next()
					
			# when a text existed in multiple lines
			elif APPEND_MODE:
				# import pdb;pdb.set_trace()
				if self.match(mp_iter.tail(), line): # match the pattern of end line
					self.update(interval, mp_iter.tail(), line, APPEND_MODE)
					interval['lineno'] = lineno
					self.intervals.append(interval)	# block ends
					interval = {}
					item_pattern = bp_iter.next()	# loop to the begining
					APPEND_MODE = False
					# 2. block ending
				else:
					# append the middle part of the text
					self.update(interval, mp_iter.index(1), line, APPEND_MODE) 
			
			# match the item in sequence
			if self.match(item_pattern, line):
				self.update(interval, item_pattern, line)

				# if the end of the block was matched
				if bp_iter.end():
					interval['lineno'] = lineno
					self.intervals.append(interval)
					interval = {}

				# loop to the begining
				item_pattern = bp_iter.next()
				# 1. block ending

			#　match the begining of multi-lines text instead of a single line
			elif self.match(mp_iter.head(), line):
				self.update(interval, mp_iter.head(), line)
				APPEND_MODE = True


def validate(intervals, quiet=False):
	validated = []
	if not quiet:
		print(u'正在验证...')
	for interval in intervals:
		legal = True 	# to append legal textgrid in the validated list
		text = interval[TEXT_KEY].decode('utf-8')
		if text:
			for rp,fn,msg in RULES_PATTERNS:
				result = rp.match(text)
				if result:
					text = fn(result)
				else:
					if not quiet:
						print(msg.format(lineno=interval['lineno'], text=interval['text'].decode('utf-8')))
					legal = False
					break
		else:
			legal = False
		if legal:
			validated.append(interval)
	return validated

TEXT_CATEGORY_PARSER = re.compile('^(?P<category>[0-2])\D.*', flags=re.UNICODE)

def timesum(intervals):
	assoeted_intervals = {}
	for interval in intervals:
		try:
			# assume it was validated before
			category = TEXT_CATEGORY_PARSER.match(interval[TEXT_KEY].decode('utf-8')).group('category')
			time_len = interval['xmax'] - interval['xmin']
			if time_len < 0:
				print('error: value of xmax detected under corresponding xmin')
				sys.exit(0)
			assoeted_intervals[category] += time_len
		except KeyError, e:
			assoeted_intervals[category] = time_len
		except AttributeError, e:
			print('error: did not validate the textgrid before calculating the time')
			sys.exit(0)

	for key, val in assoeted_intervals.items():
		print('Total time for category %s is %fs' % (key, val))


def qualify(src_file, _):
	tp.read(src_file)
	tp.parse()
	validate(tp.intervals)

def timeit(src_file, _):
	tp.read(src_file)
	tp.parse()
	validated_intervals = validate(tp.intervals, quiet=True)
	timesum(validated_intervals)
	
def main():
	file_or_dir = sys.argv[1]
	
	if len(sys.argv)>2 and sys.argv[2] == 'timeit':
		fn = timeit
	else:
		fn = qualify

	if os.path.isdir(file_or_dir): 
		traverse(file_or_dir, '', fn, target='.textgrid')
	elif os.path.isfile(file_or_dir):
		fn(file_or_dir, '')
	else:
		print(u"指定的文件或目录不存在")
	
if __name__ == '__main__':
	tp = TextgridParser()
	main()