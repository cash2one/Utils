#!/bin/sh#run the following cmd before the sh#sed -i -e 's/\r\n/\n/g' count_subdir.shROOT_DIR='/cygdrive/g/20160226'dirlist=(`find $ROOT_DIR -type d -regex '.*/[A-Z][a-z]*/[a-z]*$'`)for dir in ${dirlist[@]};do	num=`find $dir -type f -regex '.*\.txt' | wc -l`	echo ${dir}': '$num >> info.txtdonesed -i -e "s:$ROOT_DIR:\.:g" info.txt